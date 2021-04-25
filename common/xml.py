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
    output_field = TextField()


class XMLAgg(Aggregate):
    function = "XMLAGG"
    output_field = TextField()


class XMLConcat(Func):
    function = "XMLCONCAT"
    output_field = TextField()


class XMLSerialize(Func):
    function = "XMLSERIALIZE"
    output_field = TextField()
    template = "%(function)s(CONTENT %(expressions)s AS text)"
    arity = 1


class Identity(Func):
    function = ""
    template = "%(expressions)s"
    arity = 1
