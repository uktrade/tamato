import re

from importer.validators import BatchImportErrorIssueType


class ImportIssueReportItem:
    """
    Class for in memory representation if an issue detected on import, the
    status may change during the process so this will not be committed until the
    import process is complete or has been found to have errors.

    params:
        object_type: str,
            String representation of the object type, as found in XML e.g. goods.nomenclature
        related_object_type: str,
            String representation of the related object type, as found in XML e.g. goods.nomenclature.description
        related_object_identity_keys: dict,
            Dictionary of identity names and values used to link the related object
        related_cache_key: str,
            The string expected to be used to cache the related object
        description: str,
            Description of the detected issue
    """

    def __init__(
        self,
        object_type: str,
        related_object_type: str,
        related_object_identity_keys: dict,
        description: str,
        issue_type: str = BatchImportErrorIssueType.ERROR,
        taric_change_type: str = "UNDEFINED",
        object_details: str = "UNDEFINED",
        transaction_id: int = 0,
    ):
        self.object_type = object_type
        self.related_object_type = related_object_type
        self.related_object_identity_keys = related_object_identity_keys
        self.description = description
        self.issue_type = issue_type
        self.taric_change_type = taric_change_type
        self.object_details = (object_details,)
        self.transaction_id = transaction_id

    def __str__(self):
        result = (
            f"{self.issue_type}: {self.description}\n"
            f"  {self.object_type} > {self.related_object_type}\n"
            f"  link_data: {self.related_object_identity_keys}"
        )
        return result

    def __repr__(self):
        return self.__str__()

    def missing_object_method_name(self):
        """Returns a string representing the related object data type (but
        replaces full stops with underscores for readability."""
        return re.sub("\\.", "_", self.related_object_type)
