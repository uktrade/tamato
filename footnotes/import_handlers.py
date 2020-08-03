from importer.handlers import ElementHandler
from importer.handlers import TextElement
from importer.handlers import Writable
from importer.namespaces import Tag


class FootnoteAssociationMeasure(Writable, ElementHandler):
    tag = Tag("footnote.association.measure")
    measure_sid = TextElement(Tag("measure.sid"))
    footnote_type_id = TextElement(Tag("footnote.type.id"))
    footnote_id = TextElement(Tag("footnote.id"))
