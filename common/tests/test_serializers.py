import io

import pytest

from common.serializers import EnvelopeSerializer


def test_serializer_throws_error_if_max_size_is_too_small():
    """If EnvelopeSerializer gets an max_envelope_size_in_mb is an int < 32k it will raise a ValueError
    otherwise it does not raises no exception.
    """
    with pytest.raises(ValueError) as e:
        EnvelopeSerializer(io.StringIO(), envelope_id=1, max_envelope_size=32767)
    assert e.value.args == ("Max envelope size 32767 is too small, it should be at least 32768.",)

    EnvelopeSerializer(io.StringIO(), envelope_id=1, max_envelope_size=32768)
