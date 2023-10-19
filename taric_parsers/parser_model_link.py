from __future__ import annotations

from typing import List


class ModelLinkField:
    def __init__(self, parser_field_name, object_field_name):
        self.parser_field_name = parser_field_name
        self.object_field_name = object_field_name


class ModelLink:
    def __init__(
        self,
        model,
        fields: List[ModelLinkField],
        xml_tag_name: str,
        optional=False,
    ):
        self.model = model
        self.fields = fields
        self.xml_tag_name = xml_tag_name
        self.optional = optional
