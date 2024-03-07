from reference_documents.checks.base import BaseCheck


class Utils:
    def get_child_checks(self, check_class: BaseCheck.__class__):
        result = []

        check_classes = self.subclasses_for(check_class)
        for check_class in check_classes:
            result.append(check_class)

        return result

    def subclasses_for(self, cls) -> list:
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(self.subclasses_for(subclass))

        return all_subclasses
