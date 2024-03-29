import logging
from datetime import date
from datetime import timedelta

from django.db import transaction

from commodities import import_parsers as parsers
from commodities import models
from commodities import serializers
from commodities.models.orm import GoodsNomenclatureDescription
from common.validators import UpdateType
from footnotes.models import Footnote
from importer.handlers import BaseHandler

logger = logging.getLogger(__name__)


class GoodsNomenclatureHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSerializer
    tag = parsers.GoodsNomenclatureParser.tag.name


class GoodsNomenclatureOriginHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureOriginSerializer
    tag = parsers.GoodsNomenclatureOriginParser.tag.name

    identifying_fields = (
        "new_goods_nomenclature__sid",
        "derived_from_goods_nomenclature__item_id",
        "derived_from_goods_nomenclature__suffix",
    )

    links = (
        {
            "model": models.GoodsNomenclature,
            "name": "new_goods_nomenclature",
            "optional": False,
        },
        {
            "model": models.GoodsNomenclature,
            "name": "derived_from_goods_nomenclature",
            "optional": False,
            "identifying_fields": ("item_id", "suffix"),
        },
    )

    def get_derived_from_goods_nomenclature_link(self, model, kwargs):
        if "new_goods_nomenclature_id" in self.resolved_links:
            good = models.GoodsNomenclature.objects.get(
                pk=self.resolved_links["new_goods_nomenclature_id"],
            )
        else:
            good = self.resolved_links["new_goods_nomenclature"]

        must_be_active_on_date = good.valid_between.lower - timedelta(days=1)

        return (
            model.objects.filter(
                valid_between__contains=must_be_active_on_date,
                **kwargs,
            )
            .latest_approved()
            .get()
        )


class GoodsNomenclatureSuccessorHandler(BaseHandler):
    serializer_class = serializers.GoodsNomenclatureSuccessorSerializer
    tag = parsers.GoodsNomenclatureSuccessorParser.tag.name

    identifying_fields = (
        "replaced_goods_nomenclature__sid",
        "absorbed_into_goods_nomenclature__item_id",
        "absorbed_into_goods_nomenclature__suffix",
    )

    links = (
        {
            "model": models.GoodsNomenclature,
            "name": "replaced_goods_nomenclature",
            "optional": False,
        },
        {
            "model": models.GoodsNomenclature,
            "name": "absorbed_into_goods_nomenclature",
            "optional": False,
            "identifying_fields": ("item_id", "suffix"),
        },
    )

    def get_absorbed_into_goods_nomenclature_link(self, model, kwargs):
        if "replaced_goods_nomenclature_id" in self.resolved_links:
            good = models.GoodsNomenclature.objects.get(
                pk=self.resolved_links["replaced_goods_nomenclature_id"],
            )
        else:
            good = self.resolved_links["replaced_goods_nomenclature"]

        # If this successor is being deleted, the replaced goods nomenclature
        # will no longer have an end date, so we can't use that to look up the
        # correct absorbing goods nomenclature. Instead, we retrieve that
        # link from the previous version of the successor.
        if (
            good.valid_between.upper is None
            and self.data["update_type"] == UpdateType.DELETE
        ):
            previous = (
                models.GoodsNomenclatureSuccessor.objects.filter(
                    **{key: self.data[key] for key in self.identifying_fields},
                )
                .latest_approved()
                .get()
            )
            return previous.absorbed_into_goods_nomenclature
        else:
            must_be_active_on_date = good.valid_between.upper + timedelta(days=1)
            return (
                model.objects.filter(
                    valid_between__contains=must_be_active_on_date,
                    **kwargs,
                )
                .latest_approved()
                .get()
            )


class BaseGoodsNomenclatureDescriptionHandler(BaseHandler):
    links = (
        {
            "model": models.GoodsNomenclature,
            "name": "described_goods_nomenclature",
        },
    )
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = "BaseGoodsNomenclatureDescriptionHandler"


class GoodsNomenclatureDescriptionHandler(BaseGoodsNomenclatureDescriptionHandler):
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionParser.tag.name

    def create_missing_goods_nomenclature_description_period(
        self,
        goods_nomenclature_description_handler,
    ):
        """
        In some circumstances, we will receive an EU update that will reference
        a historic description period, and since TAP does not track SIDs
        currently for this data we cant resolve the reference.

        This allows the
        import to proceed by providing an invented dispatch object that can be
        processed alongside the update.
        returns a data object that replaces the missing dependency with the validity_start date set to today.
        TODO : implement correct period handling to correctly resolve this crude workaround
        """
        data = dict()

        # The code below looks for an existing goods nomenclature description in our db (using the description sid)
        # and if it finds one it will use the validity start date from that record to use in the new description.
        # If there is no existing description found then it will use todays date as the validity start date.
        # Setting to today's date is not perfect, and could cause issues in circumstances where the end date of the
        # goods nomenclature is before today, however if that's the case it does not really matter.
        # an additional possibility is that there already exists a description with this date, which will cause a rule
        # violation, also unlikely but possible.

        # Ultimately this is a crude temporary measure that will be superseded by a correct implementation splitting
        # out description periods into a new table

        # goods_nomenclature_description = None if no description exists
        goods_nomenclature_description = (
            GoodsNomenclatureDescription.objects.filter(sid=self.data["sid"])
            .latest_approved()
            .first()
        )

        if (
            goods_nomenclature_description
            and goods_nomenclature_description.described_goods_nomenclature.valid_between.lower
        ):
            data["validity_start"] = (
                goods_nomenclature_description.described_goods_nomenclature.valid_between.lower
            )
        else:
            data["validity_start"] = date.today()

        # Update the goods nomenclature description with the start date
        goods_nomenclature_description_handler.data.update(data)

        # goods nomenclature descriptions only have 1 dependency, and that's on period, so we are safe to make this an
        # empty set since we are populating the validity_start date
        goods_nomenclature_description_handler.dependency_keys = set()

        return


@GoodsNomenclatureDescriptionHandler.register_dependant
class GoodsNomenclatureDescriptionPeriodHandler(
    BaseGoodsNomenclatureDescriptionHandler,
):
    dependencies = [GoodsNomenclatureDescriptionHandler]
    serializer_class = serializers.GoodsNomenclatureDescriptionSerializer
    tag = parsers.GoodsNomenclatureDescriptionPeriodParser.tag.name


class GoodsNomenclatureIndentHandler(BaseHandler):
    links = (
        {"model": models.GoodsNomenclature, "name": "indented_goods_nomenclature"},
    )
    serializer_class = serializers.GoodsNomenclatureIndentSerializer
    tag = parsers.GoodsNomenclatureIndentParser.tag.name

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
        data.update(**self.extra_data)

        if "indented_goods_nomenclature_id" in data:
            pk = data.pop("indented_goods_nomenclature_id")
            data["indented_goods_nomenclature"] = models.GoodsNomenclature.objects.get(
                pk=pk,
            )

        indent = super().save(data)

        return indent


class FootnoteAssociationGoodsNomenclatureHandler(BaseHandler):
    identifying_fields = (
        "goods_nomenclature__sid",
        "associated_footnote__footnote_id",
        "associated_footnote__footnote_type__footnote_type_id",
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
            "identifying_fields": ("footnote_id", "footnote_type__footnote_type_id"),
        },
    )
    serializer_class = serializers.FootnoteAssociationGoodsNomenclatureSerializer
    tag = parsers.FootnoteAssociationGoodsNomenclatureParser.tag.name
