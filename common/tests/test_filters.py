import pytest

from commodities.filters import GoodsNomenclatureFilterBackend
from commodities.models.orm import GoodsNomenclature
from common.filters import TamatoFilterMixin
from common.filters import type_choices
from common.tests.factories import GoodsNomenclatureDescriptionFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import TestModel2Factory
from common.tests.models import TestModel2

pytestmark = pytest.mark.django_db


@pytest.fixture(params=(0, 1, 10))
def choice_inputs(request):
    return [TestModel2Factory() for _ in range(request.param)]


def test_type_choices(choice_inputs):
    get_choices = type_choices(TestModel2.objects.all())

    values = [choice.value for choice in get_choices()]
    custom_sids = [choice_input.custom_sid for choice_input in choice_inputs]

    assert values == custom_sids


def test_search_queryset_returns_partial_match():
    nomenclature = GoodsNomenclatureFactory.create(sid="131")
    qs = GoodsNomenclature.objects.all()
    result = TamatoFilterMixin().search_queryset(qs, "13")

    assert nomenclature in result


def test_search_queryset_returns_case_insensitive():
    nomenclature = GoodsNomenclatureDescriptionFactory.create(
        description="Red roses",
    ).described_goods_nomenclature
    qs = GoodsNomenclature.objects.all()
    result = GoodsNomenclatureFilterBackend().search_queryset(qs, "RED")

    assert nomenclature in result
