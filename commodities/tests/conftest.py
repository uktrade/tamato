import pytest

from common.tests import factories


def generate_good(
    valid_between, workbasket=None, indent_kwargs=None, with_description=True, **kwargs
):
    if not workbasket:
        workbasket = factories.WorkBasketFactory()
    kwargs["workbasket"] = workbasket
    goods_kwargs = {
        f"indented_goods_nomenclature__{key}": value for key, value in kwargs.items()
    }

    good = factories.GoodsNomenclatureIndentFactory(
        indented_goods_nomenclature__valid_between=valid_between,
        workbasket=workbasket,
        valid_between=valid_between,
        **indent_kwargs or {},
        **goods_kwargs,
    ).indented_goods_nomenclature

    if with_description:
        factories.GoodsNomenclatureDescriptionFactory(
            described_goods_nomenclature=good,
            workbasket=workbasket,
            valid_between=valid_between,
        )

    return good


@pytest.fixture
def normal_good(date_ranges):
    return generate_good(date_ranges.normal)
