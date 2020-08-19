import logging

from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import Record


logger = logging.getLogger(__name__)


@Record.register_child("footnote_type")
class FootnoteTypeParser(ValidityMixin, Writable, ElementParser):
    tag = Tag("footnote.type")

    footnote_type_id = TextElement(Tag("footnote.type.id"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
    application_code = TextElement(Tag("application.code"))


@Record.register_child("footnote_type_description")
class FootnoteTypeDescriptionParser(ValidityMixin, Writable, ElementParser):
    tag = Tag("footnote.type.description")

    footnote_type_id = TextElement(Tag("footnote.type.id"))
    description = TextElement(Tag("description"))
