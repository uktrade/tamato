from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from typing import Optional
from typing import Set

from django.db import models
from django.db import transaction
from django.db.models import Q
from django.db.models.query import QuerySet
from polymorphic.managers import PolymorphicManager
from treebeard.mp_tree import MP_Node

from commodities import business_rules
from commodities import validators
from commodities.querysets import GoodsNomenclatureIndentQuerySet
from common.business_rules import UpdateValidity
from common.fields import LongDescription
from common.models import NumericSID
from common.models import TrackedModel
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.description import DescriptionQueryset
from common.models.mixins.validity import ValidityMixin
from common.models.mixins.validity import ValidityStartMixin
from common.util import TaricDateRange
from footnotes.validators import ApplicationCode
from measures import business_rules as measures_business_rules


@dataclass
class CommodityCode:
    """A dataclass for commodity codes with a range of convenience
    properties."""

    code: str

    @property
    def chapter(self) -> str:
        """Returns the HS chapter for the commodity code."""
        return self.code[:2]

    @property
    def heading(self) -> str:
        """Returns the HS heading for the commodity code."""
        return self.code[:4]

    @property
    def subheading(self) -> str:
        """Returns the HS subheading for the commodity code."""
        return self.code[:6]

    @property
    def cn_subheading(self) -> str:
        """Returns the CN subheading for the commodity code."""
        return self.code[:8]

    @property
    def dot_code(self) -> str:
        """Returns the commodity code in dot format."""
        code = self.code
        return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"

    @property
    def trimmed_dot_code(self) -> str:
        """Returns the commodity code in dot format, without trailing zero
        pairs."""
        parts = self.dot_code.split(".")

        for i, part in enumerate(parts[::-1]):
            if part != "00":
                return ".".join(parts[: len(parts) - i])

    @property
    def trimmed_code(self) -> str:
        """Returns the commodity code without trailing zero pairs."""
        return self.trimmed_dot_code.replace(".", "")

    @property
    def is_chapter(self) -> bool:
        """Returns true if the commodity code represents a HS chapter."""
        return self.trimmed_code.rstrip("0") == self.chapter

    @property
    def is_heading(self) -> bool:
        """Returns true if the commodity code represents a HS heading."""
        return self.trimmed_code == self.heading and not self.is_chapter

    @property
    def is_subheading(self) -> bool:
        """Returns true if the commodity code represents a HS subheading."""
        return self.trimmed_code == self.subheading

    @property
    def is_cn_subheading(self) -> bool:
        """Returns true if the commodity code represents a CN subheading."""
        return self.trimmed_code == self.cn_subheading

    @property
    def is_taric_subheading(self) -> bool:
        """Returns true if the commodity code represents a Taric subheading."""
        return self.trimmed_code == self.code

    @property
    def is_taric_code(self) -> bool:
        return self.code[8:] != "00"

    def __str__(self):
        """Returns a string representation of the dataclass instance."""
        return self.code


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
    def code(self) -> CommodityCode:
        """Returns a CommodityCode instance for the good."""
        return CommodityCode(code=self.item_id)

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
        UpdateValidity,
    )

    class Meta:
        verbose_name = "commodity code"

    def __str__(self):
        return self.item_id

    @property
    def autocomplete_label(self):
        return f"{self} - {self.get_description().description}"

    def get_dependent_measures(self, transaction=None):
        return self.measures.model.objects.filter(
            goods_nomenclature__sid=self.sid,
        ).approved_up_to_transaction(transaction)

    @property
    def is_taric_code(self) -> bool:
        return self.code.is_taric_code


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
    business_rules = (business_rules.NIG2, UpdateValidity)

    validity_over = "indented_goods_nomenclature"

    @property
    def is_root(self) -> bool:
        """Returns True if this is a root indent."""
        item_id = self.indented_goods_nomenclature.item_id
        return self.indent == 0 and item_id[2:] == "00000000"

    def get_parent_indents(self) -> QuerySet:
        """Returns the ancestors to this indent in the goods hierarchy."""
        if self.is_root:
            return GoodsNomenclatureIndent.objects.none()

        parent_path_query = Q()
        for path in self.nodes.values_list("path", flat=True):
            parent_path_query = parent_path_query | Q(
                nodes__path=path[: -GoodsNomenclatureIndentNode.steplen],
            )

        return GoodsNomenclatureIndent.objects.filter(parent_path_query)

    @property
    def good_indents(self) -> QuerySet:
        """Return the related goods indents based on approval status."""
        good = self.indented_goods_nomenclature
        return good.indents.approved_up_to_transaction(
            self.transaction,
        )

    @property
    def preceding_indent(self) -> Optional[GoodsNomenclatureIndent]:
        """Returns the node indent's predecessor in time, if any."""
        return (
            self.good_indents.filter(
                validity_start__lt=self.validity_start,
            )
            .order_by("validity_start")
            .last()
        )

    @property
    def succeeding_indent(self) -> Optional[GoodsNomenclatureIndent]:
        """Returns the node indent's successor in time, if any."""
        return (
            self.good_indents.filter(
                validity_start__gt=self.validity_start,
            )
            .order_by("validity_start")
            .first()
        )

    def get_parent_node(
        self,
        parent_depth: int,
        start_date: Optional[date] = None,
    ) -> Optional[GoodsNomenclatureIndent]:
        """
        Returns the parent of the indent given a parent depth.

        This method is attached here so it can be used on indents
        that do not have an indent node yet
        (for example, new indents while being imported).

        This method does not trust paths by definition.
        """
        if self.is_root:
            return None

        good: GoodsNomenclature = self.indented_goods_nomenclature
        item_id = good.item_id
        chapter = good.code.chapter
        suffix = good.suffix
        validity_start = start_date or self.validity_start

        qs = GoodsNomenclatureIndentNode.objects
        parent: GoodsNomenclatureIndentNode = (
            qs.filter(
                Q(indent__indented_goods_nomenclature__item_id__lt=item_id)
                | Q(
                    indent__indented_goods_nomenclature__item_id=item_id,
                    indent__indented_goods_nomenclature__suffix__lt=suffix,
                ),
                indent__indented_goods_nomenclature__item_id__startswith=chapter,
                indent__indented_goods_nomenclature__valid_between__contains=validity_start,
                indent__validity_start__lte=validity_start,
                valid_between__contains=validity_start,
                depth=parent_depth,
            )
            .order_by(
                "-indent__indented_goods_nomenclature__item_id",
                "-indent__validity_start",
                "-creating_transaction",
            )
            .first()
        )

        # The end dates on some historically created nodes
        # may have not been synced with the implied end date of their indent
        # when a succeeding indent has been introduced at a later point in time.
        # This can cause the above query to yield the wrong parent.
        # The extra logic below catches and remedies such potential cases.
        # TODO: Handle situations with multiple wrong patterns
        effective_end_date = parent.effective_end_date

        if effective_end_date and effective_end_date < self.validity_start:
            parent = parent.succeeding_node

        return parent

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

    @property
    def parent_depth(self) -> int:
        """
        Returns parent depth factoring in the good's indent shift.

        See the docs to `GoodsNomenclature.indent_shift` for context.
        """
        return self.depth + 1 + self.good.indent_shift

    @property
    def good(self) -> GoodsNomenclature:
        """Returns the node indent's indented good."""
        return self.indent.indented_goods_nomenclature

    @property
    def preceding_node(self) -> Optional[GoodsNomenclatureIndentNode]:
        """Returns the precessor to this node, if any."""
        indent = self.indent.preceding_indent

        if not indent:
            return

        return indent.nodes.order_by(
            "valid_between__startswith",
        ).last()

    @property
    def succeeding_node(self) -> Optional[GoodsNomenclatureIndentNode]:
        """Returns the successor to this node, if any."""
        indent = self.indent.succeeding_indent

        if not indent:
            return

        return indent.nodes.order_by(
            "valid_between__startswith",
        ).first()

    @property
    def effective_end_date(self) -> date:
        """
        Returns the effective end date for the node.

        Context:
        Historically, the goods hierarchy tree was broken for some time spans.
        The root cause has been fixed for future imports
        (see `GoodsNomenclatureIndentHandler.set_preceding_node_enddate`).
        However, legacy broken tree areas still exist;
        for nodes whose explicit end date has not been updated in the past
        when the related indent's implicit end date changed
        (e.g. due to the introduction of a succeeding indent),
        we need to be able to tell the effective end dates of such nodes,
        which are constrained by the implicit end date of the related indent.
        """
        indent = self.indent.succeeding_indent

        if not indent:
            return self.valid_between.upper

        return indent.validity_start + timedelta(days=-1)

    @property
    def effective_valid_between(self) -> TaricDateRange:
        """
        Returns the effective validity range for the node.

        Context:
        See the docs for the `effective_end_date` method of this class.
        """
        return TaricDateRange(
            self.valid_between.lower,
            self.effective_end_date,
        )

    @property
    def parent(self) -> GoodsNomenclatureIndentNode:
        """Returns the parent of the node."""
        return self.indent.get_parent_node(self.parent_depth)

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


class GoodsNomenclatureDescription(DescriptionMixin, TrackedModel):
    record_code = "400"
    subrecord_code = "15"
    period_record_code = "400"
    period_subrecord_code = "10"

    objects = PolymorphicManager.from_queryset(DescriptionQueryset)()

    sid = NumericSID()
    described_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
        related_name="descriptions",
    )
    description = LongDescription()

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
    business_rules = (business_rules.NIG7, UpdateValidity)

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

    business_rules = (business_rules.NIG10, UpdateValidity)

    def __str__(self):
        return (
            f"replaced=({self.replaced_goods_nomenclature}), "
            f"absorbed_into=({self.absorbed_into_goods_nomenclature})"
        )


class FootnoteAssociationGoodsNomenclature(TrackedModel, ValidityMixin):
    record_code = "400"
    subrecord_code = "20"

    goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
        related_name="footnote_associations",
    )
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
        UpdateValidity,
    )
