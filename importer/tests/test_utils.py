from importer import utils
from quotas.models import QuotaDefinition
from quotas.models import QuotaEvent


def test_generate_key():
    """
    Verifies that generate_key produces the expected key.

    TODO: This test needs to be more robust.
    """
    key = utils.generate_key("test", ["1", "2"], {"1": 1, "2": 2})
    assert key == "a98ec5c5044800c88e862f007b98d89815fc40ca155d6ce7909530d792e909ce"


def test_get_record_codes():
    codes = utils.get_record_codes(QuotaEvent)
    assert codes == [QuotaEvent.record_code]


def test_get_subrecords():
    qd_codes = utils.get_record_codes(QuotaDefinition, use_subrecord_codes=True)
    qe_codes = utils.get_record_codes(QuotaEvent, use_subrecord_codes=True)

    qd_identifier = f"{QuotaDefinition.record_code}{QuotaDefinition.subrecord_code}"
    qe_choices = [code for code, _ in QuotaEvent.subrecord_code.field.choices]
    qe_identifiers = [f"{QuotaEvent.record_code}{code}" for code in qe_choices]

    assert qd_codes == [qd_identifier]
    assert qe_codes == qe_identifiers
