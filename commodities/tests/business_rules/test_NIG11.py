import pytest

from commodities import business_rules
from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def test_NIG11_one_indent_mandatory():
    """At least one indent record is mandatory."""

    good = factories.GoodsNomenclatureFactory.create(indent=None)
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(good.transaction).validate(good)


def test_NIG11_first_indent_must_have_same_start_date(date_ranges):
    """The start date of the first indentation must be equal to the start date
    of the nomenclature."""

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.normal,
        validity_start=date_ranges.overlap_normal.lower,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(indent.transaction).validate(
            indent.indented_goods_nomenclature,
        )


def test_NIG11_no_overlapping_indents():
    """No two associated indentations may have the same start date."""

    existing = factories.GoodsNomenclatureIndentFactory.create()
    duplicate = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature=existing.indented_goods_nomenclature,
        validity_start=existing.validity_start,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(duplicate.transaction).validate(
            existing.indented_goods_nomenclature,
        )


def test_NIG11_start_date_less_than_end_date(date_ranges):
    """The start date must be less than or equal to the end date of the
    nomenclature."""

    indent = factories.GoodsNomenclatureIndentFactory.create(
        indented_goods_nomenclature__valid_between=date_ranges.normal,
        validity_start=date_ranges.later.lower,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NIG11(indent.transaction).validate(
            indent.indented_goods_nomenclature,
        )


def test_NIG11_skips_when_goods_deleted(date_ranges):
    """Example failure,"""

    # Create goods nomenclature
    goods = factories.GoodsNomenclatureFactory.create(indent=None)

    # create new workbasket
    editable_workbasket = factories.WorkBasketFactory()

    # create transaction
    editable_transaction = factories.TransactionFactory.create(
        workbasket=editable_workbasket,
        order=2,
    )

    # delete the goods nomenclature
    delete_goods = goods.new_version(
        transaction=editable_transaction,
        update_type=UpdateType.DELETE,
        workbasket=editable_workbasket,
    )

    business_rules.NIG11(editable_transaction).validate(delete_goods)
