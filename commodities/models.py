from __future__ import annotations

from typing import Set

from django.db import models
from django.db import transaction
from django.db.models import Q
from polymorphic.managers import PolymorphicManager
from treebeard.mp_tree import MP_Node

from commodities import business_rules
from commodities import validators
from commodities.querysets import GoodsNomenclatureIndentQuerySet
from common.models import NumericSID
from common.models import TrackedModel
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.validity import ValidityMixin
from common.models.mixins.validity import ValidityStartMixin
from common.util import TaricDateRange
from footnotes.validators import ApplicationCode
from measures import business_rules as measures_business_rules


class GoodsNomenclature(TrackedModel, ValidityMixin):
    record_code = "400"
    subrecord_code = "00"

    sid = NumericSID()

    # These are character fields as they often has leading 0s
    item_id = models.CharField(
        max_length=10,
        validators=[validators.item_id_validator],
        db_index=True,
    )
    suffix = models.CharField(
        max_length=2,
        validators=[validators.suffix_validator],
        db_index=True,
    )

    statistical = models.BooleanField()

    origins = models.ManyToManyField(
        "self",
        through="GoodsNomenclatureOrigin",
        through_fields=("new_goods_nomenclature", "derived_from_goods_nomenclature"),
    )

    successors = models.ManyToManyField(
        "self",
        through="GoodsNomenclatureSuccessor",
        through_fields=(
            "replaced_goods_nomenclature",
            "absorbed_into_goods_nomenclature",
        ),
    )

    @property
    def is_taric_code(self) -> bool:
        return self.item_id[8:] != "00"

    @property
    def footnote_application_codes(self) -> Set[ApplicationCode]:
        codes = {ApplicationCode.TARIC_NOMENCLATURE, ApplicationCode.DYNAMIC_FOOTNOTE}
        if not self.is_taric_code:
            codes.add(ApplicationCode.CN_NOMENCLATURE)
        return codes

    indirect_business_rules = (
        business_rules.NIG10,
        business_rules.NIG18,
        business_rules.NIG2,
        business_rules.NIG22,
        business_rules.NIG7,
        measures_business_rules.ME1,
        measures_business_rules.ME7,
        measures_business_rules.ME71,
        measures_business_rules.ME88,
    )
    business_rules = (
        business_rules.NIG1,
        business_rules.NIG5,
        business_rules.NIG30,
        business_rules.NIG31,
        business_rules.NIG34,
        business_rules.NIG35,
    )

    class Meta:
        verbose_name = "commodity code"

    def __str__(self):
        return self.item_id

    def in_use(self):
        return (
            self.measures.model.objects.filter(
                goods_nomenclature__sid=self.sid,
            )
            .approved_up_to_transaction(self.transaction)
            .exists()
        )


class GoodsNomenclatureIndent(TrackedModel, ValidityStartMixin):
    record_code = "400"
    subrecord_code = "05"

    objects: GoodsNomenclatureIndentQuerySet = PolymorphicManager.from_queryset(
        GoodsNomenclatureIndentQuerySet,
    )()

    sid = NumericSID()

    indent = models.PositiveIntegerField(db_index=True)

    indented_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
        related_name="indents",
    )

    indirect_business_rules = (business_rules.NIG11,)
    business_rules = (business_rules.NIG2,)

    validity_over = "indented_goods_nomenclature"

    def get_parent_indents(self):
        parent_path_query = Q()
        for path in self.nodes.values_list("path", flat=True):
            parent_path_query = parent_path_query | Q(
                nodes__path=path[: -GoodsNomenclatureIndentNode.steplen],
            )

        return GoodsNomenclatureIndent.objects.filter(parent_path_query)

    def save(self, *args, **kwargs):
        return_value = super().save(*args, **kwargs)

        if not hasattr(self, "version_group"):
            self.version_group = self._get_version_group()

        return return_value

    def __str__(self):
        return f"Goods Nomenclature Indent: {self.indent} - {self.indented_goods_nomenclature}"


class GoodsNomenclatureIndentNode(MP_Node, ValidityMixin):
    """
    Goods Nomenclature naturally falls into the structure of a hierarchical
    tree. As there is a root good e.g. "Live Animals; Animal Products" which
    then has branch nodes such as "Live animals" and "Meat and edible meat
    offal". And so on and so forth until leaf nodes are found.

    To represent this efficiently in a database a Materialized Path is used. There is some
    documentation on this here: https://django-treebeard.readthedocs.io/en/latest/mp_tree.html

    The Crux of the system is every node is given a "path" attribute. A path is constructed of
    "steps". Steps by default are 4 character blocks. The number of steps given to a node
    determine its depth. Root nodes are given a single step as a path. A child of a root node
    will have a path starting with the parents path, then with an extra step added on.

    This way queries for all child nodes are as simple as:

    .. code:: SQL

        SELECT *
          FROM table
         WHERE path LIKE "{parent_path}%";

    and a parent node query would be:

    .. code:: SQL

        SELECT *
          FROM table
         WHERE path = parent_path[:-4]

    Sadly for legacy reasons the visible codes given to goods do not well conform to this
    structure. These given ids are generally limited to 10 characters with numeric only steps
    of 2 characters each. This would naturally mean a tree can only be 5 layers deep, however
    there are instances where the tariff goes to 14 levels. As a result the step based system
    has been ignored historically. There are also cases where the same ID is given to multiple
    objects with other identifying values included (e.g. suffixes) and an entire indent table
    to represent the tree depth. This, combined with suffixes and some ordering within the item
    ID gave the actual location.

    The indent table initially looks like a good candidate. However, due to how the legacy
    system was implemented (i.e., without a tree), the legacy indents would move fluidly
    between parents without the need for an update - a feature that would be incompatible with
    an implemented tree system at this table.

    This implementation keeps a separate untracked table for tree nodes, keeping the tree entirely
    separate from the main implementation of the data system. The node holds a Foreign Key to the
    indent table, allowing the tree to be accessed through the indent. The indent then has a Foreign Key
    to the relevant Goods Nomenclature so they can be edited separately. This does away with
    the need to analyse the item id and suffix as well as the indent - as the node gives us
    an entire description of the tree and its related commodities on its own, over time.
    """

    # Coming from the legacy tracked model this model needs a new primary key.
    # Given paths are always unique in MP trees this is the best candidate for the PK.
    path = models.CharField(max_length=255, unique=True, primary_key=True)

    indent = models.ForeignKey(
        GoodsNomenclatureIndent,
        on_delete=models.PROTECT,
        related_name="nodes",
    )

    creating_transaction = models.ForeignKey(
        "common.Transaction",
        on_delete=models.PROTECT,
        related_name="goods_nomenclature_indent_nodes",
    )

    def get_measures(self, **kwargs):
        if self.indent.measures.exists():
            return self.indent.measures.all()
        query = self.get_ancestors().filter(
            indent__indented_goods_nomenclature__measures__isnull=False, **kwargs
        )
        if query.exists():
            return query.first().measures.all()

        return False

    def has_measure_in_tree(self):
        ascendant_measures = self.get_ancestors().filter(
            indent__indented_goods_nomenclature__measures__isnull=False,
        )
        descendant_measures = self.get_descendants().filter(
            indent__indented_goods_nomenclature__measures__isnull=False,
        )
        return (
            self.indent.measures.exists()
            or ascendant_measures.exists()
            or descendant_measures.exists()
        )

    def _get_restricted_valid_between(
        self,
        valid_between: TaricDateRange,
    ) -> TaricDateRange:
        new_valid_between = self.valid_between
        if not new_valid_between.lower or (
            valid_between.lower and new_valid_between.lower < valid_between.lower
        ):
            new_valid_between = TaricDateRange(
                valid_between.lower,
                new_valid_between.upper,
            )
        if not new_valid_between.upper or (
            valid_between.upper and new_valid_between.upper > valid_between.upper
        ):
            new_valid_between = TaricDateRange(
                new_valid_between.lower,
                valid_between.upper,
            )

        return new_valid_between

    @transaction.atomic
    def copy_tree(
        self,
        parent: GoodsNomenclatureIndentNode,
        valid_between: TaricDateRange,
        transaction,
    ):
        new_valid_between = self._get_restricted_valid_between(valid_between)

        new_node = parent.add_child(
            indent=self.indent,
            valid_between=new_valid_between,
            creating_transaction=transaction,
        )
        for child in self.get_children():
            child.copy_tree(new_node, valid_between, transaction)

        return new_node

    @transaction.atomic
    def restrict_valid_between(self, valid_between: TaricDateRange):
        self.valid_between = self._get_restricted_valid_between(valid_between)
        for child in self.get_children():
            child.restrict_valid_between(self.valid_between)
        self.save()

    def __str__(self):
        return f"path={self.path}, indent=({self.indent})"


class GoodsNomenclatureDescription(TrackedModel, DescriptionMixin):
    record_code = "400"
    subrecord_code = "15"
    period_record_code = "400"
    period_subrecord_code = "10"

    sid = NumericSID()
    described_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
        related_name="descriptions",
    )
    description = models.TextField(blank=True)

    indirect_business_rules = (business_rules.NIG12,)

    class Meta:
        ordering = ("validity_start",)


class GoodsNomenclatureOrigin(TrackedModel):
    """
    Represents a link between a newly-created GoodsNomenclature and the codes
    that previously represented it.

    This will often be the parent nomenclature code. A GoodsNomenclature can
    have multiple origins when the hierarchy has been reorganised and the new
    classification was previously covered by multiple codes.
    """

    record_code = "400"
    subrecord_code = "35"

    new_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        related_name="origin_links",
        on_delete=models.PROTECT,
    )
    derived_from_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
    )

    identifying_fields = (
        "new_goods_nomenclature__sid",
        "derived_from_goods_nomenclature__sid",
    )

    indirect_business_rules = (business_rules.NIG5,)
    business_rules = (business_rules.NIG7,)

    def __str__(self):
        return (
            f"derived_from=({self.derived_from_goods_nomenclature}), "
            f"new=({self.new_goods_nomenclature})"
        )


class GoodsNomenclatureSuccessor(TrackedModel):
    """
    Represents a link between a end-dated GoodsNomenclature and the codes that
    have replaced it (or in TARIC parlance have "absorbed" it).

    The replacing codes cover the goods that this classification code previously
    covered.
    """

    record_code = "400"
    subrecord_code = "40"

    replaced_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        related_name="successor_links",
        on_delete=models.PROTECT,
    )
    absorbed_into_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
    )

    identifying_fields = (
        "replaced_goods_nomenclature__sid",
        "absorbed_into_goods_nomenclature__sid",
    )

    business_rules = (business_rules.NIG10,)

    def __str__(self):
        return (
            f"replaced=({self.replaced_goods_nomenclature}), "
            f"absorbed_into=({self.absorbed_into_goods_nomenclature})"
        )


class FootnoteAssociationGoodsNomenclature(TrackedModel, ValidityMixin):
    record_code = "400"
    subrecord_code = "20"

    goods_nomenclature = models.ForeignKey(GoodsNomenclature, on_delete=models.PROTECT)
    associated_footnote = models.ForeignKey(
        "footnotes.Footnote",
        on_delete=models.PROTECT,
    )

    identifying_fields = (
        "goods_nomenclature__sid",
        "associated_footnote__footnote_id",
        "associated_footnote__footnote_type__footnote_type_id",
    )

    business_rules = (
        business_rules.NIG18,
        business_rules.NIG22,
        business_rules.NIG23,
        business_rules.NIG24,
    )
