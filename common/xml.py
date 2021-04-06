from django.contrib.contenttypes.models import ContentType
from django.db.models import Aggregate
from django.db.models import Case
from django.db.models import Func
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Value
from django.db.models import When
from django.db.models.expressions import Window
from django.db.models.fields import TextField
from django.db.models.functions import Lower
from django.db.models.functions import Upper
from django.db.models.functions.window import RowNumber

import measures.import_parsers
import measures.models
from common.models import TrackedModel
from common.models.records import TrackedModelQuerySet

# TODO: Library XML functions – should these be part of Django? I read somewhere
# that XML didn't used to be included by default in most Postgres installations
# which is why Django chose not to include these alongside their JSON
# counterparts. Is that still true? If not, should we be opening a PR to merge
# the XML functions in?


class XMLAttribute(Func):
    arity = 1
    template = '%(expressions)s AS "%(name)s"'


class XMLAttributes(Func):
    function = "xmlattributes"


class XMLComment(Func):
    arity = 1
    function = "XMLCOMMENT"


class XMLElement(Func):
    def __init__(self, name, *children, **attributes):
        if any(attributes):
            children = [
                XMLAttributes(
                    *(
                        XMLAttribute(value, name=key)
                        for (key, value) in attributes.items()
                    )
                ),
                *children,
            ]
        super().__init__(*children, name=name, output_field=TextField())

    function = "XMLELEMENT"
    template = '%(function)s(name "%(name)s", %(expressions)s)'


class XMLAgg(Aggregate):
    function = "XMLAGG"


class XMLConcat(Func):
    function = "XMLCONCAT"


def parser_to_xml_element(parser, fieldname=None):
    # TODO: This special handling of valid_between is clearly slightly smelly.
    # There probably also needs to be some more fine-grained control of how
    # things are formatted – we ultimately need to replace all of the logic in
    # serializers and templates.
    children = parser._field_lookup.items()
    if fieldname == "valid_between_lower":
        null_condition = "valid_between__lower_inf"
        field = Lower("valid_between")
    elif fieldname == "valid_between_upper":
        null_condition = "valid_between__upper_inf"
        field = Upper("valid_between")
    else:
        null_condition = f"{fieldname}__isnull"
        field = fieldname

    if any(children):
        return XMLElement(
            parser.tag.name,
            *(parser_to_xml_element(*child) for child in children),
        )
    else:
        return Case(
            When(
                **{null_condition: False},
                then=XMLElement(
                    parser.tag.name,
                    field,
                ),
            ),
            default=Value(""),
        )


# TODO: We should be auto-generating this – how do we map them back? An
# attribute on the model perhaps? Or a decorator that declares a given parser as
# representative? Given that we're using these for more than parsing now, should
# we be renaming them – e.g. `measures.xml_models.MeasureXMLModel` or something?
MAPPING = {
    measures.models.Measure: measures.import_parsers.MeasureParser,
    measures.models.MeasureComponent: measures.import_parsers.MeasureComponentParser,
    measures.models.MeasureCondition: measures.import_parsers.MeasureConditionParser,
    measures.models.MeasureConditionComponent: measures.import_parsers.MeasureConditionComponentParser,
}


def tracked_model_to_xml(qs: TrackedModelQuerySet):
    types = {c.model_class(): c for c in ContentType.objects.all()}
    return qs.annotate_record_codes().annotate(
        xml=XMLElement(
            "record",
            XMLElement("transaction.id", "transaction__order"),
            XMLElement(
                "record.code",
                "record_code",
            ),
            XMLElement(
                "subrecord.code",
                "subrecord_code",
            ),
            XMLElement("record.sequence.number", 1),
            XMLElement(
                "update.type",
                "update_type",
            ),
            # This builds a massive CASE WHEN that covers each possible content
            # type, and then wraps getting the XML in a subquery. For some
            # reason, this does not seem to be horrendously slow.
            Case(
                *(
                    When(
                        polymorphic_ctype=types[model],
                        then=Subquery(
                            model.objects.annotate(xml=parser_to_xml_element(parser()))
                            .filter(pk=OuterRef("pk"))
                            .values_list("xml"),
                        ),
                    )
                    for (model, parser) in MAPPING.items()
                ),
                defualt=None,
            ),
        ),
    )


def transaction_to_xml(qs):
    # TODO: at some point these tags all need to have namespaces, how do we do that?
    return qs.annotate(message_id=Window(expression=RowNumber())).annotate(
        # TODO: These all have `ImportParsers` of their own – can we avoid
        # hard-coding these? We'd need to find some way to handle the above
        # annotation.
        #
        # Perhaps a common method:
        #     def to_xml_element(self, children: XmlElement) -> Tuple[XmlElement, Dict[str, Expression]]:
        #         return XmlElement(self.tag.name, children), {}
        # which can be overriden for app.message?
        xml=XMLElement(
            "transaction",
            XMLElement(
                "app.message",
                XMLElement(
                    "transmission",
                    Subquery(
                        (
                            # https://stackoverflow.com/questions/55925437/django-subquery-with-aggregate
                            # TODO: This may not be necessary since Django
                            # introduced `alias` on querysets?
                            tracked_model_to_xml(TrackedModel.objects)
                            .filter(transaction=OuterRef("pk"))
                            .values("transaction__pk")
                            .annotate(xmldoc=XMLAgg("xml"))
                            .values("xmldoc")
                        ),
                        output_field=TextField(),
                    ),
                ),
                id="message_id",
            ),
            id="order",
        ),
    )


def transaction_chunks(qs):
    # TODO: this and the others should be queryset methods rather than free
    # functions. This method (iterator with 32k chunks) has won out as being
    # slightly fastest on my machine. Run this with e.g.
    # transaction_chunks(Transaction.objects.filter(order__gte=300000))
    return (
        transaction_to_xml(qs).values_list("xml", flat=True).iterator(chunk_size=32000)
    )
