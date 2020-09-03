from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from treebeard.mp_tree import MP_Node

from commodities import validators
from common.models import PolymorphicMPTreeManager
from common.models import PolymorphicMPTreeQuerySet
from common.models import TrackedModel
from common.models import ValidityMixin


class GoodsNomenclature(TrackedModel, ValidityMixin):
    record_code = "400"
    subrecord_code = "00"
    origin_record_code = "400"
    origin_subrecord_code = "35"
    successor_record_code = "400"
    successor_subrecord_code = "40"

    sid = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99999999)]
    )

    # These are character fields as they often has leading 0s
    item_id = models.CharField(max_length=10, validators=[validators.item_id_validator])
    suffix = models.CharField(max_length=2, validators=[validators.suffix_validator])

    statistical = models.BooleanField()

    origin = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="succeeding_goods",
        related_query_name="succeeding_goods",
    )

    def validate_workbasket(self):
        validators.validate_at_least_one_description(self)
        validators.validate_at_least_one_indent(self)
        validators.validate_has_origin(self)
        self.full_clean()  # This means it is run twice but due to weirdness with the origin it is required.
        return super().validate_workbasket()

    def clean(self):
        validators.validate_predecessor_ends_before_successor_starts(self)
        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Goods Nomenclature: {self.item_id}"

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_goods",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        )


class GoodsNomenclatureIndent(MP_Node, TrackedModel, ValidityMixin):
    """
    Goods Nomenclature naturally falls into the structure of a hierarchical tree.
    As there is a root good e.g. "Live Animals; Animal Products" which then has branch nodes
    such as "Live animals" and "Meat and edible meat offal". And so on and so forth until
    leaf nodes are found.

    To represent this efficiently in a database a Materialized Path is used. There is some
    documentation on this here: https://django-treebeard.readthedocs.io/en/latest/mp_tree.html

    The Crux of the system is every node is given a "path" attribute. A path is constructed of
    "steps". Steps by default are 4 character blocks. The number of steps given to a node
    determine its depth. Root nodes are given a single step as a path. A child of a root node
    will have a path starting with the parents path, then with an extra step added on.

    This way queries for all child nodes are as simple as:

        SELECT *
          FROM table
         WHERE path LIKE "{parent_path}%";

    and a parent node query would be:

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

    This implementation keeps the separate indent table, but places allows that indent to be
    represented by a real tree using the Materialized Path. The indent then has a Foreign Key
    to the relevant Goods Nomenclature so they can be edited separately. This does away with
    the need to analyse the item id and suffix as well as the indent - as the indent gives us
    an entire description of the tree and its related commodities on its own.
    """

    record_code = "400"
    subrecord_code = "05"

    sid = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99999999)]
    )

    indented_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature, on_delete=models.PROTECT, related_name="indents"
    )

    objects = PolymorphicMPTreeManager.from_queryset(PolymorphicMPTreeQuerySet)()

    def get_active_children(self, **kwargs):
        return self.get_children().active().filter(**kwargs)

    def get_measures(self, **kwargs):
        if self.measures.exists():
            return self.measures.all()
        query = self.get_ancestors().filter(
            indented_goods_nomenclature__measures__isnull=False, **kwargs
        )
        if query.exists():
            return query.first().measures.all()

        return False

    def has_measure_in_tree(self):
        ascendant_measures = self.get_ancestors().filter(
            indented_goods_nomenclature__measures__isnull=False
        )
        descendant_measures = self.get_descendants().filter(
            indented_goods_nomenclature__measures__isnull=False
        )
        return (
            self.measures.exists()
            or ascendant_measures.exists()
            or descendant_measures.exists()
        )

    def clean(self):
        validators.validate_indent_start_date_less_than_goods_end_date(self)
        validators.validate_goods_parent_validity_includes_good(self)
        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Goods Nomenclature Indent: {self.depth} - {self.indented_goods_nomenclature}"

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_goods_indents",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        )


class GoodsNomenclatureDescription(TrackedModel, ValidityMixin):
    record_code = "400"
    subrecord_code = "15"
    period_record_code = "400"
    period_subrecord_code = "10"

    sid = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99999999)]
    )
    described_goods_nomenclature = models.ForeignKey(
        GoodsNomenclature,
        on_delete=models.PROTECT,
        related_name="descriptions",
    )
    description = models.TextField()

    def clean(self):
        validators.validate_description_is_not_null(self)
        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = (
            ExclusionConstraint(
                name="exclude_overlapping_goods_descriptions",
                expressions=[
                    ("valid_between", RangeOperators.OVERLAPS),
                    ("sid", RangeOperators.EQUAL),
                ],
            ),
        )


class FootnoteAssociationGoodsNomenclature(TrackedModel, ValidityMixin):
    record_code = "400"
    subrecord_code = "20"

    goods_nomenclature = models.ForeignKey(GoodsNomenclature, on_delete=models.PROTECT)
    associated_footnote = models.ForeignKey(
        "footnotes.Footnote", on_delete=models.PROTECT
    )

    identifying_fields = "goods_nomenclature", "associated_footnote"

    def clean(self):
        validators.validate_goods_validity_includes_footnote_association(self)
        validators.validate_footnote_validity_includes_footnote_association(self)
        validators.validate_duplicate_footnote_associations_cant_overlap(self)
        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
