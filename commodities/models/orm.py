from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from typing import Set

from django.db import models
from django.db.models.query import QuerySet
from polymorphic.managers import PolymorphicManager

from commodities import business_rules
from commodities import validators
from commodities.querysets import GoodsNomenclatureIndentQuerySet
from common.business_rules import UpdateValidity
from common.fields import LongDescription
from common.models import NumericSID
from common.models import TrackedModel
from common.models.managers import TrackedModelManager
from common.models.mixins.description import DescribedMixin
from common.models.mixins.description import DescriptionMixin
from common.models.mixins.description import DescriptionQueryset
from common.models.mixins.validity import ValidityMixin
from common.models.mixins.validity import ValidityStartMixin
from common.models.transactions import Transaction
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


class GoodsNomenclature(TrackedModel, ValidityMixin, DescribedMixin):
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
        business_rules.NIG12,
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

    @property
    def indent_shift(self) -> int:
        """
        Returns the depth offset for the good.

        Indent shifts come into play when we need to construct a goods
        nomenclature hierarchy tree. In some cases, where there are phantom
        headers at the 4 digit level in a chapter, the indent is shifted by + 1.
        A phantom header is any good with a suffix != "80". In the real world
        this represents a good that does not appear in any legislature and is
        non-declarable. i.e. it does not exist outside of the database and is
        purely for "convenience". This algorithm doesn't apply to chapter 99.
        """
        chapter = self.code.chapter
        indent_shift = 0

        extra_headings = (
            GoodsNomenclature.objects.filter(
                item_id__startswith=chapter,
                item_id__endswith="000000",
            )
            .exclude(suffix="80")
            .exists()
        ) and chapter != "99"

        if extra_headings and (self.item_id[-6:] != "000000" or self.suffix == "80"):
            indent_shift += 1

        return indent_shift


class GoodsNomenclatureIndent(TrackedModel, ValidityStartMixin):
    record_code = "400"
    subrecord_code = "05"

    objects: GoodsNomenclatureIndentQuerySet = TrackedModelManager.from_queryset(
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

    def get_good_indents(
        self,
        as_of_transaction: Optional[Transaction] = None,
    ) -> QuerySet:
        """Return the related goods indents based on approval status."""
        good = self.indented_goods_nomenclature
        return good.indents.approved_up_to_transaction(
            as_of_transaction or self.transaction,
        )

    def get_preceding_indent(
        self,
        as_of_transaction: Optional[Transaction] = None,
    ) -> Optional[GoodsNomenclatureIndent]:
        """Returns the node indent's predecessor in time, if any."""
        return (
            self.get_good_indents(as_of_transaction)
            .filter(
                validity_start__lt=self.validity_start,
            )
            .order_by("validity_start")
            .last()
        )

    def get_succeeding_indent(
        self,
        as_of_transaction: Optional[Transaction] = None,
    ) -> Optional[GoodsNomenclatureIndent]:
        """Returns the node indent's successor in time, if any."""
        return (
            self.get_good_indents(as_of_transaction)
            .filter(
                validity_start__gt=self.validity_start,
            )
            .order_by("validity_start")
            .first()
        )

    def save(self, *args, **kwargs):
        return_value = super().save(*args, **kwargs)

        if not hasattr(self, "version_group"):
            self.version_group = self._get_version_group()

        return return_value

    def __str__(self):
        return f"Goods Nomenclature Indent: {self.indent} - {self.indented_goods_nomenclature}"


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
    business_rules = (UpdateValidity,)

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
