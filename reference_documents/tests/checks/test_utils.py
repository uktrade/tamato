import pytest

from reference_documents.check import utils
from reference_documents.check.base import BaseCheck
from reference_documents.check.ref_order_numbers import OrderNumberChecks


@pytest.mark.reference_documents
class TestUtils:
    def test_get_child_checks(self):

        checks = utils.Utils.get_child_checks(BaseCheck)
        assert len(checks) > 0
        assert OrderNumberChecks in checks

    def test_subclasses_for(self):

        classes = utils.Utils.subclasses_for(BaseCheck)
        assert len(classes) > 0
        assert OrderNumberChecks in classes
