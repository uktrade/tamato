import logging
from datetime import date
from datetime import timedelta
from typing import Optional

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.db.models import Q

from commodities import import_parsers as parsers
from commodities import models
from commodities import serializers
from commodities.exceptions import InvalidIndentError
from common.models import Transaction
from common.util import TaricDateRange
from common.util import maybe_min
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
                    **{key: self.data[key] for key in self.identifying_fields}
                )
                .latest_approved()
                .get()
            )
            return previous.absorbed_into_goods_nomenclature
        else:
            if good.valid_between.upper is None:
                return model.objects.filter(**kwargs).latest_approved().get()
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

    def set_preceding_node_end_date(
        self,
        indent: models.GoodsNomenclatureIndent,
    ) -> None:
        """
        End-dates the node of the preceding indent, if there is one.

        Background:
        - In the Taric3 specification, goods_nomenclature_indent records
        have an explicit validity start date, while the end date is implied
        conditional on the existence of a succeeding indent for the same good.

        - When we materialize the goods nomenclature hierarchy tree,
        we use the `GoodsNomenclatureIndentNode` model (not in Taric3 spec),
        which is designed to have explicit validity end dates.

        This means that when a new `goods_nomenclature_indent` record
        is created on an existing `goods_nomenclature` record,
        we have to make sure to explicitly end-date the related
        `GoodsNomenclatureIndentNode` object.

        If we failed to sync the end dates of the indent and the node,
        one of two issues would occur:
        1. The materialized goods nomenclature hierarchy tree
        could end up being incorrect for some time spans
        2. An exception could be thrown in the `save` method of this class:
        when we pick the wrong parent indent, its implied end date
        might be lower than the start date of a new node
        we are trying to attach to the tree.
        """
        preceding_indent = indent.get_preceding_indent()

        if not preceding_indent:
            return

        preceding_node = (
            models.GoodsNomenclatureIndentNode.objects.filter(
                indent=preceding_indent,
            )
            .order_by("creating_transaction_id")
            .last()
        )

        valid_between = TaricDateRange(
            preceding_node.valid_between.lower,
            indent.validity_start - timedelta(days=1),
        )

        if (
            valid_between.upper < valid_between.lower
            and Transaction.objects.get(
                id=preceding_node.creating_transaction_id,
            ).workbasket
            == indent.transaction.workbasket
        ):
            return

        # We need a new preceding node as of this transaction
        # with the correct end date, and we need to create a new one
        node_data = {
            "indent": preceding_indent,
            "valid_between": valid_between,
            "creating_transaction_id": indent.transaction.id,
        }

        if preceding_indent.is_root:
            new_preceding_node = models.GoodsNomenclatureIndentNode.add_root(
                **node_data
            )
        else:
            indent_shift = indent.indented_goods_nomenclature.indent_shift
            parent_depth = preceding_indent.indent + 1 + indent_shift
            parent_node = preceding_indent.get_parent_node(
                parent_depth=parent_depth,
            )
            new_preceding_node = parent_node.add_child(**node_data)

        # The tree needs to be copied over to each new indent node separately,
        # including the new preceding node
        preceding_node.copy_tree(
            parent=new_preceding_node,
            valid_between=valid_between,
            transaction=indent.transaction,
        )

        return preceding_node

    def get_indent_end_date(
        self,
        indent: models.GoodsNomenclatureIndent,
    ) -> Optional[date]:
        """
        Return the implied end date for an indent when there is a succeeding
        indent.

        See the docs to `self.set_preceding_node_end_date` for context.

        If a new indent comes in and it already has a succeeding future indent,
        then we need to use the implied end date for the new indent
        as the explicit end date for the new indent's related
        `GoodsNomenclatureIndentNode` object we are about to create.
        """
        models.GoodsNomenclatureIndent.objects.with_end_date().get(
            pk=indent.pk,
        ).validity_end

    # @transaction.atomic
    def save(self, data: dict):
        depth = self.extra_data.pop("indent")
        data.update(**self.extra_data)
        if "indented_goods_nomenclature_id" in data:
            pk = data.pop("indented_goods_nomenclature_id")
            data["indented_goods_nomenclature"] = models.GoodsNomenclature.objects.get(
                pk=pk,
            )
        item_id = data["indented_goods_nomenclature"].item_id

        indent = super().save(data)
        preceding_node = self.set_preceding_node_end_date(indent)

        indent = models.GoodsNomenclatureIndent.objects.with_end_date().get(
            pk=indent.pk,
        )
        node_data = {
            "indent": indent,
            "valid_between": indent.valid_between,
            "creating_transaction_id": data["transaction_id"],
        }

        if indent.is_root:
            indent_node = models.GoodsNomenclatureIndentNode.add_root(**node_data)

            if preceding_node:
                # The tree needs to be copied over to each new indent node separately,
                # in addition to the new preceding indent, including the new root indent node.
                preceding_node.copy_tree(
                    parent=indent_node,
                    valid_between=indent.valid_between,
                    transaction=indent.transaction,
                )

            return indent

        indent_shift = indent.indented_goods_nomenclature.indent_shift
        parent_depth = depth + 1 + indent_shift

        start_date = data["validity_start"]
        end_date = maybe_min(
            indent.validity_end,
            data["indented_goods_nomenclature"].valid_between.upper,
        )

        while start_date and ((start_date < end_date) if end_date else True):
            defn = (indent.sid, start_date.year, start_date.month, start_date.day)
            if defn in self.overrides:
                next_indent = models.GoodsNomenclatureIndent.objects.get(
                    sid=self.overrides[defn],
                )
                next_parent = next_indent.nodes.filter(
                    valid_between__contains=start_date,
                ).get()
                logger.info("Using manual override for indent %s", defn)
            else:
                next_parent = indent.get_parent_node(
                    parent_depth,
                    as_of_transaction=indent.transaction,
                    start_date=start_date,
                )

            if not next_parent:
                raise InvalidIndentError(
                    f"Parent indent not found for {item_id} for date {start_date}",
                )

            next_parent_indent = (
                models.GoodsNomenclatureIndent.objects.with_end_date().get(
                    pk=next_parent.indent.pk,
                )
            )
            indent_start = start_date
            indent_end = maybe_min(
                next_parent.valid_between.upper,
                next_parent_indent.validity_end,
                next_parent.indent.indented_goods_nomenclature.valid_between.upper,
                end_date,
                self.get_indent_end_date(indent),
            )

            node_data["valid_between"] = TaricDateRange(indent_start, indent_end)
            indent_node = next_parent.add_child(**node_data)

            if preceding_node:
                # The tree needs to be copied over to each new indent node separately,
                # in addition to the new preceding indent, including this node.
                preceding_node.copy_tree(
                    parent=indent_node,
                    valid_between=node_data["valid_between"],
                    transaction=indent.transaction,
                )

            start_date = (
                indent_end + relativedelta(days=+1) if indent_end else indent_end
            )

        return indent

    @transaction.atomic
    def move_child_node_to_new_parent(
        self,
        child_node: models.GoodsNomenclatureIndentNode,
        parent_indent: models.GoodsNomenclatureIndent,
    ):
        """
        Given a child with an inappropriate parent and a replacing parent,
        replace the child's parent.

        In some cases the inappropriate parent may only be inappropriate during certain dates - in which
        case the child and it's descendants need to be split across both parents.
        """
        new_valid_between = child_node.valid_between

        if new_valid_between.upper_is_greater(parent_indent.valid_between):
            # There is overlap on the upper end of the indent.
            # Copy child indent so the old tree is replicated after the
            # new indents validity range.
            child_node.copy_tree(
                parent=child_node.get_parent(),
                valid_between=TaricDateRange(
                    parent_indent.valid_between.upper + relativedelta(days=1),
                    new_valid_between.upper,
                ),
                transaction=parent_indent.transaction,
            )
            new_valid_between = TaricDateRange(
                new_valid_between.lower,
                parent_indent.valid_between.upper,
            )

        if new_valid_between.lower < parent_indent.valid_between.lower:
            # There is overlap on the lower end of the indent.
            # Split the child tree so it is a child of both the old
            # parent and the new parent indent.
            old_child = child_node
            child_node = child_node.copy_tree(
                parent=child_node.get_parent(),
                valid_between=TaricDateRange(
                    parent_indent.valid_between.lower,
                    new_valid_between.upper,
                ),
                transaction=parent_indent.transaction,
            )

            old_child.restrict_valid_between(
                TaricDateRange(
                    new_valid_between.lower,
                    parent_indent.valid_between.lower - relativedelta(days=1),
                ),
            )
            new_valid_between = TaricDateRange(
                parent_indent.valid_between.lower,
                new_valid_between.upper,
            )

        new_parents = parent_indent.nodes.filter(
            valid_between__overlap=new_valid_between,
            depth=child_node.depth - 1,
        )
        if new_parents.count() == 1:
            # No need to split the child node further, it fits completely
            # into the new parent node.
            new_parent = new_parents.get()
            child_node.move(new_parent, "last-child")
        else:
            # The new child node does not fit neatly into a single parent node.
            # Split the child node so it fits under each new parent node.
            start_date = new_valid_between.lower
            end_date = new_valid_between.upper
            for parent in new_parents:
                new_valid_between = TaricDateRange(
                    parent.valid_between.lower
                    if parent.valid_between.lower > start_date
                    else start_date,
                    parent.valid_between.upper
                    if parent.valid_between.upper < end_date
                    else end_date,
                )
                child_node.copy_tree(
                    parent,
                    new_valid_between,
                    parent_indent.transaction,
                )
                child_node.delete()
                start_date = parent.valid_between.upper + relativedelta(
                    days=1,
                )

    @transaction.atomic
    def find_and_replace_inappropriate_parent_nodes(
        self,
        obj: models.GoodsNomenclatureIndent,
    ):
        """
        In some cases an indent is introduced in between an existing indent and
        it's children. In this case those children should move from the existing
        indent to the new indent.

        This method finds all possible children of a new indent and queries to
        see if any should be moved from their current parent to the new indent.
        """
        try:
            # while in the import handler,
            # we may have indents that have no nodes yet,
            # which could lead to exceptions
            nodes = obj.nodes.all()
        except (AttributeError, TypeError):
            return

        if not nodes:
            return

        excluded_nodes = [
            Q(nodes__path__startswith=path)
            for path in nodes.values_list("path", flat=True)
        ]

        # These are the children which could be moved to the new indent.
        # This is because they are one level deeper than the new indent
        # and have item IDs greater than the new indent.
        possible_children = (
            models.GoodsNomenclatureIndent.objects.with_end_date()
            .approved_up_to_transaction(
                obj.transaction,
            )
            .filter(
                nodes__depth=nodes.first().depth + 1,
                valid_between__overlap=obj.valid_between,
                indented_goods_nomenclature__item_id__gte=obj.indented_goods_nomenclature.item_id,
                indented_goods_nomenclature__item_id__startswith=obj.indented_goods_nomenclature.item_id[
                    :2
                ],
            )
            .exclude(*excluded_nodes)
        )

        for child in possible_children:
            # A child can only be moved to the new node if it has parents which can be replaced.
            # A parent can only be replaced if it is the current parent of this possible child, and
            # it's item_id is considered lesser than the new indents item_id.
            replaceable_parents = (
                child.get_parent_indents()
                .with_end_date()
                .filter(
                    indented_goods_nomenclature__item_id__lt=obj.indented_goods_nomenclature.item_id,
                    valid_between__overlap=obj.valid_between,
                )
            )

            if not replaceable_parents.exists():
                # In this case all the parents of the node are appropriate and don't need to be replaced.
                continue

            has_parent_path = Q()
            for path in models.GoodsNomenclatureIndentNode.objects.filter(
                indent__in=replaceable_parents,
            ).values_list("path", flat=True):
                has_parent_path = has_parent_path | Q(path__startswith=path)

            child_nodes = models.GoodsNomenclatureIndentNode.objects.filter(
                has_parent_path,
                valid_between__overlap=obj.valid_between,
                indent=child,
            ).order_by("valid_between")

            for child_node in child_nodes:
                self.move_child_node_to_new_parent(child_node, obj)

        return obj

    @transaction.atomic
    def post_save(self, obj: models.GoodsNomenclatureIndent):
        """
        There is a possible scenario when introducing an indent that the new
        indent is put between an existing indent and its children (i.e. it
        becomes the new parent for those children). This is possible as the old
        system had no real materialized tree behind it.

        Furthermore on updating changes any node which originally has children
        will need to have its children copied across to the new updated node.
        """

        obj = models.GoodsNomenclatureIndent.objects.with_end_date().get(pk=obj.pk)
        self.find_and_replace_inappropriate_parent_nodes(obj)

        if self.data["update_type"] == UpdateType.CREATE:
            return super(GoodsNomenclatureIndentHandler, self).post_save(obj)

        previous_version = (
            obj.version_group.versions.exclude(pk=obj.pk)
            .has_approved_state()
            .order_by("transaction__updated_at")
            .last()
        )

        if not previous_version:
            previous_version = (
                obj.version_group.versions.exclude(pk=obj.pk)
                .filter(transaction__workbasket=obj.transaction.workbasket)
                .order_by("transaction__updated_at")
                .last()
            )

        for node in obj.nodes.all():
            for previous_node in previous_version.nodes.filter(
                valid_between__overlap=node.valid_between,
            ):
                for child in previous_node.get_children().filter(
                    valid_between__overlap=node.valid_between,
                ):
                    child.copy_tree(
                        parent=node,
                        valid_between=node.valid_between,
                        transaction=node.creating_transaction,
                    )

        return super(GoodsNomenclatureIndentHandler, self).post_save(obj)


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
