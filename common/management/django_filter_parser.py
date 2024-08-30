from django.db.models import Q
from lark import Lark
from lark import ParseTree
from lark import Transformer
from lark import v_args


class DjangoFilterQueryParser:
    """A parser for Django filter query strings."""

    grammar = """
        ?query: expression
                | -> empty_string

        ?expression: term
                    | expression "&" term -> and_expression
                    | expression "|" term -> or_expression

        ?term: condition
                | "(" expression ")"

        ?condition: field "=" value
        
        field: /\\w+/

        value: /[^&|()]+/
        
        %import common.WS
        %ignore WS
    """

    def __init__(self):
        self.parser = Lark(
            grammar=self.grammar,
            start="query",
        )

        self.transformer = DjangoFilterQueryTransformer()

    def parse(self, query: str) -> ParseTree:
        """Parses `query`, returning a parse tree."""
        return self.parser.parse(query)

    def transform(self, query: str) -> Q:
        """Parses `query` and transforms the returned parse tree into a Q
        object."""
        tree = self.parse(query)
        return self.transformer.transform(tree)


class DjangoFilterQueryTransformer(Transformer):
    """A transformer for converting parsed Django filter query strings into Q
    objects."""

    @v_args(inline=True)
    def and_expression(self, left_term, right_term):
        """Combines `left_term` and `right_term` into an AND expression."""
        return left_term & right_term

    @v_args(inline=True)
    def or_expression(self, left_term, right_term):
        """Combines `left_term` and `right_term` into an OR expression."""
        return left_term | right_term

    @v_args(inline=True)
    def condition(self, field, value):
        """Combines `field` and `value` into a Q object."""
        field_name = field.children[0].value
        field_value = value.children[0].value
        return Q(**{field_name: field_value})

    @v_args(inline=True)
    def empty_string(self):
        return None
