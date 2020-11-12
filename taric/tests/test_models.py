import pytest

from common.tests import factories


pytestmark = pytest.mark.django_db


def test_envelope_transactions(date_ranges):
    factories.EnvelopeFactory.reset_sequence()

    envelope = factories.EnvelopeFactory()

    assert envelope.envelope_id == f"{date_ranges.now:%y}0001"
