import pytest

from reference_documents.check.base import BaseCheck


@pytest.mark.reference_documents
class TestUtils:
    @pytest.mark.skip(reason="test not implemented yet")
    def test_get_child_checks(self, check_class: BaseCheck.__class__):
        result = []

        check_classes = self.subclasses_for(check_class)
        for check_class in check_classes:
            result.append(check_class)

        return result

    @pytest.mark.skip(reason="test not implemented yet")
    def subclasses_for(self, cls) -> list:
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(self.subclasses_for(subclass))

        return all_subclasses
