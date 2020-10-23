import logging
from typing import Any
from typing import Optional

from django.db import transaction

from commodities import import_parsers as parsers
from commodities import models
from commodities import serializers
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from importer.handlers import BaseHandler

logger = logging.getLogger(__name__)


class InvalidIndentError(Exception):
    pass


def maybe_min(*objs: Optional[Any]) -> Optional[Any]:
    present = [d for d in objs if d is not None]
    if any(present):
        return min(present)
    else:
        return None


class GoodsNomenclatureHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureParser.tag.name


class GoodsNomenclatureOriginHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureOriginParser.tag.name


class BaseGoodsNomenclatureDescriptionHandler(BaseHandler):
    links = (
        {
            "identifying_fields": ("sid", "item_id"),
            "model": models.GoodsNomenclature,
            "name": "described_goods_nomenclature",
        },
    )
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = "BaseGoodsNomenclatureDescriptionHandler"


class GoodsNomenclatureDescriptionHandler(BaseGoodsNomenclatureDescriptionHandler):
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionParser.tag.name


@GoodsNomenclatureDescriptionHandler.register_dependant
class GoodsNomenclatureDescriptionPeriodHandler(
    BaseGoodsNomenclatureDescriptionHandler
):
    dependencies = [GoodsNomenclatureDescriptionHandler]
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionPeriodParser.tag.name


class GoodsNomenclatureIndentHandler(BaseHandler):
    links = (
        {"model": models.GoodsNomenclature, "name": "indented_goods_nomenclature"},
    )
    serializer_class = serializers.GoodsNomenclatureIndentSerializer
    tag = parsers.GoodsNomenclatureIndentsParser.tag.name

    # It is sadly necessary to correct some mistakes in the TARIC data.
    # These codes all do not meet the assumption that the child indent
    # is 1 more than their parent indent. These are assumed to be errors.
    # Here indent sid + start date is mapped to correct parent indent sid.
    overrides = {
        # 2106909921/80
        (35191, 1972, 1, 1): 35189,
        # 2106909929/80
        (35198, 1972, 1, 1): 35189,
        # 1901100035/80
        (33760, 1980, 1, 1): 33746,
        (33760, 1990, 3, 1): 33743,
        (33760, 1992, 1, 1): 33755,
    }

    def __init__(self, *args, **kwargs):
        super(GoodsNomenclatureIndentHandler, self).__init__(*args, **kwargs)
        self.extra_data = {}

    def clean(self, data: dict) -> dict:
        self.extra_data["indent"] = int(data["indent"])
        return super(GoodsNomenclatureIndentHandler, self).clean(data)

    @transaction.atomic
    def save(self, data: dict):
        depth = self.extra_data.pop("indent")
        data.update(**self.extra_data)

        item_id = data["indented_goods_nomenclature"].item_id

        indent = super(GoodsNomenclatureIndentHandler, self).save(data)

        node_data = {
            "indent": indent,
            "valid_between": data["valid_between"],
        }

        if depth == 0 and item_id[2:] == "00000000":
            # This is a root indent (i.e. a chapter heading)
            models.GoodsNomenclatureIndentNode.add_root(**node_data)
            return indent

        chapter_heading = item_id[:2]

        parent_depth = depth + 1

        # In some cases, where there are phantom headers at the 4 digit level
        # in a chapter, the depth is shifted by + 1.
        # A phantom header is any good with a suffix != "80". In the real world
        # this represents a good that does not appear in any legislature and is
        # non-declarable. i.e. it does not exist outside of the database and is
        # purely for "convenience". This algorithm doesn't apply to chapter 99.
        extra_headings = (
            models.GoodsNomenclature.objects.filter(
                item_id__startswith=chapter_heading,
                item_id__endswith="000000",
            )
            .exclude(suffix="80")
            .exists()
        ) and chapter_heading != "99"

        if extra_headings and (
            item_id[-6:] != "000000"
            or data["indented_goods_nomenclature"].suffix == "80"
        ):
            parent_depth += 1

        start_date = data["valid_between"].lower
        end_date = maybe_min(
            data["valid_between"].upper,
            data["indented_goods_nomenclature"].valid_between.upper,
        )

        while start_date and ((start_date < end_date) if end_date else True):
            defn = (indent.sid, start_date.year, start_date.month, start_date.day)
            if defn in self.overrides:
                next_indent = models.GoodsNomenclatureIndent.objects.get(
                    sid=self.overrides[defn]
                )
                next_parent = next_indent.nodes.filter(
                    valid_between__contains=start_date
                ).get()
                logger.info("Using manual override for indent %s", defn)
            else:
                next_parent = (
                    models.GoodsNomenclatureIndentNode.objects.filter(
                        indent__indented_goods_nomenclature__item_id__lte=item_id,
                        indent__indented_goods_nomenclature__item_id__startswith=chapter_heading,
                        indent__indented_goods_nomenclature__valid_between__contains=start_date,
                        indent__valid_between__contains=start_date,
                        valid_between__contains=start_date,
                        depth=parent_depth,
                    )
                    .order_by("-indent__indented_goods_nomenclature__item_id")
                    .first()
                )

            if not next_parent:
                raise InvalidIndentError(
                    f"Parent indent not found for {item_id} for date {start_date}"
                )

            indent_start = start_date
            indent_end = maybe_min(
                next_parent.valid_between.upper,
                next_parent.indent.valid_between.upper,
                next_parent.indent.indented_goods_nomenclature.valid_between.upper,
                end_date,
            )

            node_data["valid_between"] = (indent_start, indent_end)

            next_parent.add_child(**node_data)

            start_date = indent_end

        return indent

    def post_save(self, obj):
        """
        There is a possible (albeit unlikely) scenario when introducing an indent that the
        new indent is put between an existing indent and it's children (i.e. it becomes the
        new parent for those children).

        As the old system had no real materialized tree behind the system it is not
        unreasonable to suggest this as a possibility.

        This method handles this by checking for any children which need to be moved
        in case this happens.
        """

        # TODO: Implement this scenario (requires updating to be implemented first).

        return super(GoodsNomenclatureIndentHandler, self).post_save(obj)


class FootnoteAssociationGoodsNomenclatureHandler(BaseHandler):
    identifying_fields = (
        "goods_nomenclature__sid",
        "associated_footnote__footnote_id",
        "associated_footnote__footnote_type_id",
    )

    links = (
        {
            "model": models.GoodsNomenclature,
            "name": "goods_nomenclature",
            "optional": False,
        },
        {
            "model": Footnote,
            "name": "associated_footnote",
            "optional": False,
            "identifying_fields": ("footnote_id", "footnote_type_id"),
        },
    )
    serializer_class = serializers.FootnoteAssociationGoodsNomenclatureSerializer
    tag = parsers.FootnoteAssociationGoodsNomenclatureParser.tag.name

    def get_associated_footnote_link(self, model, kwargs):
        kwargs["footnote_type"] = FootnoteType.objects.get_latest_version(
            footnote_type_id=kwargs.pop("footnote_type_id")
        )
        return model.objects.get_latest_version(**kwargs)
