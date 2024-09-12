from reference_documents.check.base import BaseCheck


class Utils:
    @staticmethod
    def get_child_checks(check_class: BaseCheck.__class__):
        result = []

        check_classes = Utils.subclasses_for(check_class)
        for check_class in check_classes:
            if 'reference_documents.check.' in str(check_class):
                result.append(check_class)

        return result

    @staticmethod
    def subclasses_for(cls) -> list:
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(Utils.subclasses_for(subclass))

        return all_subclasses
