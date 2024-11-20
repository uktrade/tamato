from reference_documents.check.base import BaseCheck


class Utils:
    """Utilities class providing tools to get check classes."""

    @staticmethod
    def get_child_checks(check_class: BaseCheck.__class__):
        """
        Utility to collect child classes for the provided class, only where they
        are defined in the reference_documents.checks namespace.

        Args:
            check_class: Parent class we want to find children for

        Returns:
            list(child, grand child, great grans child etc. of check_class)
        """
        result = []

        check_classes = Utils.subclasses_for(check_class)
        for check_class in check_classes:
            if "reference_documents.check." in str(check_class):
                result.append(check_class)

        return result

    @staticmethod
    def subclasses_for(cls) -> list:
        """
        Recursive function to collect child classes of a class.

        Args:
            cls: class to lookup child classes for

        Returns:
            list(child, grand child, great grans child etc. of cls)
        """
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(Utils.subclasses_for(subclass))

        return all_subclasses
