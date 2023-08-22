from os import path

import pytest

from commodities import forms
from common.models.transactions import Transaction
from common.tests import factories

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")
pytestmark = pytest.mark.django_db


def test_commodity_footnote_form():
    commodity = factories.GoodsNomenclatureFactory.create()
    footnote = factories.FootnoteFactory.create()
    data = {
        "goods_nomenclature": commodity.id,
        "associated_footnote": footnote.id,
        "start_date_0": commodity.valid_between.lower.day,
        "start_date_1": commodity.valid_between.lower.month,
        "start_date_2": commodity.valid_between.lower.year,
        "end_date": "",
    }
    tx = Transaction.objects.last()
    form = forms.CommodityFootnoteForm(data=data, tx=tx)
    assert form.is_valid()
