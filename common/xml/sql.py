"""
Library XML functions.

TODO – should these be part of Django? I read somewhere that XML didn't used to
be included by default in most Postgres installations which is why Django chose
not to include these alongside their JSON counterparts. Is that still true? If
not, should we be opening a PR to merge the XML functions in?
"""

from typing import List

from django.db.models import Aggregate
from django.db.models import Func
from django.db.models.expressions import BaseExpression
from django.db.models.fields import TextField


class XMLSyntax(Func):
    """
    Base class for XML features defined by XML/SQL standard to use special
    syntax.

    These are things which are not really functions and cannot be treated like
    them, but for which :class:`~django.db.models.Func` is the easiest way to
    generate the SQL we need.
    """

    def get_group_by_cols(self) -> List[BaseExpression]:
        cols = []
        for source in self.get_source_expressions():
            cols.extend(source.get_group_by_cols())
        return cols


class XMLAttribute(XMLSyntax):
    arity = 1
    template = '%(expressions)s AS "%(name)s"'


class XMLAttributes(XMLSyntax):
    function = "XMLATTRIBUTES"


class XMLComment(Func):
    """
    The function `XMLComment` creates an XML value containing an XML comment
    with the specified text as content.

    The text cannot contain "--" or end with a "-", otherwise the resulting
    construct would not be a valid XML comment. If the argument is null, the
    result is null.
    """

    # xmlcomment ( text ) -> xml

    arity = 1
    function = "XMLCOMMENT"


class XMLElement(Func):
    """
    The `XMLElement` expression produces an XML element with the given name,
    attributes, and children.

    The name and attname items shown in the syntax are simple identifiers, not
    values. The attvalue and content items are expressions, which can yield any
    PostgreSQL data type. The argument(s) within XMLATTRIBUTES generate
    attributes of the XML element; the content value(s) are concatenated to form
    its content.
    """

    # xmlelement (
    #   NAME name
    #   [, XMLATTRIBUTES ( attvalue [ AS attname ] [, ...] ) ]
    #   [, content [, ...]]
    # ) -> xml

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
    output_field = TextField()


class XMLAgg(Aggregate):
    """
    The function `XMLAgg` is an aggregate function that concatenates the input
    values to the aggregate function call much like
    :class:`~common.xml.sql.XMLConcat` does.

    As this is an aggregate function concatenation occurs across rows rather
    than across expressions in a single row.
    """

    # xmlagg ( xml ) -> xml

    function = "XMLAGG"
    output_field = TextField()


class XMLConcat(Func):
    """
    The function `XMLConcat` concatenates a list of individual XML values to
    create a single value containing an XML content fragment.

    Null values are omitted; the result is only null if there are no nonnull
    arguments.
    """

    # xmlconcat ( xml [, ...] ) -> xml

    function = "XMLCONCAT"
    output_field = TextField()


class XMLSerialize(Func):
    """
    The function `XMLSerialize` produces a character string value from XML.

    According to the SQL standard, this is the only way to convert between type
    xml and character types.
    """

    # XMLSERIALIZE ( { DOCUMENT | CONTENT } value AS type )

    function = "XMLSERIALIZE"
    output_field = TextField()
    template = "%(function)s(CONTENT %(expressions)s AS text)"
    arity = 1


class Identity(Func):
    function = ""
    template = "%(expressions)s"
    arity = 1
