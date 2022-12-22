from datetime import datetime
from datetime import timezone

import freezegun
import pytest

from common.tests import factories
from taric.models import Envelope

pytestmark = pytest.mark.django_db


def test_envelope_transactions(date_ranges):
    factories.EnvelopeFactory.reset_sequence()

    envelope = factories.EnvelopeFactory()

    assert envelope.envelope_id == f"{date_ranges.now:%y}0001"


@freezegun.freeze_time(datetime(2030, 1, 1, tzinfo=timezone.utc))
def test_new_envelope_populates_envelope_id():
    """Verify Envelope.new_envelope correctly populates envelope_id."""
    # Create 3 envelopes: the first envelope in a year uses
    #                     different logic to subsequent years,
    #                     this verifies that ids increment in both cases.

    packaged_wb1 = factories.PackagedWorkBasketFactory.create()
    packaged_wb2 = factories.PackagedWorkBasketFactory.create()
    packaged_wb3 = factories.PackagedWorkBasketFactory.create()
    envelope1 = Envelope.objects.create(packaged_work_basket=packaged_wb1)
    assert envelope1.envelope_id == "300001"

    envelope2 = Envelope.objects.create(packaged_work_basket=packaged_wb2)
    assert envelope2.envelope_id == "300002"

    envelope3 = Envelope.objects.create(packaged_work_basket=packaged_wb3)
    assert envelope3.envelope_id == "300003"


@freezegun.freeze_time(datetime(2024, 1, 1, tzinfo=timezone.utc))
def test_new_envelope_enforces_daily_limit():
    factories.EnvelopeFactory.create(envelope_id="249999")

    with pytest.raises(ValueError) as e:
        Envelope.new_envelope()

    assert e.value.args == ("Cannot create more than 9999 Envelopes on a single year.",)
