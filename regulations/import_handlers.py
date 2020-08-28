from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import Record
from regulations import serializers


class RegulationGroup(Writable, ElementParser):
    tag = Tag("regulation.group.id")


@Record.register_child("base_regulation")
class BaseRegulation(ValidityMixin, Writable, ElementParser):
    serializer_class = serializers.RegulationSerializer

    tag = Tag("base.regulation")
    role_type = TextElement(Tag("base.regulation.role"))
    regulation_id = TextElement(Tag("base.regulation.id"))
    published_at = TextElement(Tag("published.date"))
    official_journal_number = TextElement(Tag("officialjournal.number"))
    official_journal_page = TextElement(Tag("officialjournal.page"))
    community_code = TextElement(Tag("community.code"))
    regulation_group_id = TextElement(Tag("regulation.group.id"))
    replacement_indicator = TextElement(Tag("replacement.indicator"))
    stopped = TextElement(Tag("stopped.flag"))
    information_text = TextElement(Tag("information.text"))
    approved = TextElement(Tag("approved.flag"))
    valid_between_lower = TextElement(Tag("validity.start.date"))
    valid_between_upper = TextElement(Tag("validity.end.date"))
