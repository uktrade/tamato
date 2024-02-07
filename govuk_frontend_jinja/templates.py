import builtins
import os.path as path
import re
from collections.abc import Sized

import jinja2
import jinja2.ext
from jinja2.lexer import Token
from markupsafe import Markup


def njk_to_j2(template):
    # Some component templates (such as radios) use `items` as the key of
    # an object element. However `items` is also the name of a dictionary
    # method in Python, and Jinja2 will prefer to return this attribute
    # over the dict item. Handle specially.
    template = re.sub(r"\.items\b", ".items__njk", template)

    # Some component templates (such as radios) append the loop index to a
    # string. As the loop index is an integer this causes a TypeError in
    # Python. Jinja2 has an operator `~` for string concatenation that
    # converts integers to strings.
    template = template.replace("+ loop.index", "~ loop.index")

    # The Character Count component in version 3 concatenates the word count
    # with the hint text. As the word count is an integer this causes a
    # TypeError in Python. Jinja2 has an operator `~` for string
    # concatenation that converts integers to strings.
    template = template.replace(
        "+ (params.maxlength or params.maxwords) +",
        "~ (params.maxlength or params.maxwords) ~",
    )

    # Nunjucks uses elseif, Jinja uses elif
    template = template.replace("elseif", "elif")

    # Some component templates (such as input) call macros with params as
    # an object which has unqoted keys. This causes Jinja to silently
    # ignore the values.
    template = re.sub(
        r"""^([ ]*)([^ '"#\r\n:]+?)\s*:""",
        r"\1'\2':",
        template,
        flags=re.M,
    )

    # govukFieldset can accept a call block argument, however the Jinja
    # compiler does not detect this as the macro body is included from
    # the template file. A workaround is to patch the declaration of the
    # macro to include an explicit caller argument.
    template = template.replace(
        "macro govukFieldset(params)",
        "macro govukFieldset(params, caller=none)",
    )

    # Many components feature an attributes field, which is supposed to be
    # a dictionary. In the template for these components, the keys and values
    # are iterated. In Python, the default iterator for a dict is .keys(), but
    # we want .items().
    # This only works because our undefined implements .items()
    # We've tested this explicitly with: govukInput, govukCheckbox, govukTable,
    # govukSummaryList
    template = re.sub(
        r"for attribute, value in (params|item|cell|action).attributes",
        r"for attribute, value in \1.attributes.items()",
        template,
        flags=re.M,
    )

    # Some templates try to set a variable in an outer block, which is not
    # supported in Jinja. We create a namespace in those templates to get
    # around this.
    template = re.sub(
        r"""^([ ]*)({% set describedBy =( params.*describedBy if params.*describedBy else)? "" %})""",
        r"\1{%- set nonlocal = namespace() -%}\n\1\2",
        template,
        flags=re.M,
    )
    # Change any references to describedBy to be nonlocal.describedBy,
    # unless describedBy is a dictionary key (i.e. quoted or dotted).
    template = re.sub(r"""(?<!['".])describedBy""", r"nonlocal.describedBy", template)
    # govukSummaryList
    template = re.sub(
        r"""^([ ]*)({% set anyRowHasActions = false %})""",
        r"\1{%- set nonlocal = namespace() -%}\n\1\2",
        template,
        flags=re.M,
    )
    template = re.sub(
        r"""(?<!['".])anyRowHasActions""",
        r"nonlocal.anyRowHasActions",
        template,
    )
    # govukRadios and govukCheckboxes
    # Since both of these templates set describedBy before isConditional, we can use
    # the existing nonlocal.
    template = re.sub(
        r"""(?<!['".])isConditional""",
        r"nonlocal.isConditional",
        template,
    )

    # Issue#16: some component templates test the length of an array by trying
    # to get an attribute `.length`. We need to handle this specially because
    # .length isn't a thing in python
    template = re.sub(r"\.length\b", ".length__njk", template)

    # see `indent_njk`
    template = re.sub(re.escape("| indent") + r"\b", "| indent_njk", template)

    return template


def indent_njk(
    s,
    width=4,
    first=False,
    blank=False,
    indentfirst=None,
):
    """Return a copy of the string with each line indented by 4 spaces."""

    # to include an unreleased fix for https://github.com/pallets/jinja/pull/826
    # which causes the file upload component to escape HTML markup.
    # TODO: Remove once jinja2 2.11 is released and in use.

    if indentfirst is not None:
        first = indentfirst

    indention = " " * width
    newline = "\n"

    if isinstance(s, Markup):
        indention = Markup(indention)
        newline = Markup(newline)

    s += newline  # this quirk is necessary for splitlines method

    if blank:
        rv = (newline + indention).join(s.splitlines())
    else:
        lines = s.splitlines()
        rv = lines.pop(0)

        if lines:
            rv += newline + newline.join(
                indention + line if line else line for line in lines
            )

    if first:
        rv = indention + rv

    return rv


class NunjucksExtension(jinja2.ext.Extension):
    def filter_stream(self, stream):
        if stream.filename and stream.filename.endswith(".njk"):
            return self.filter_njk_stream(stream)
        else:
            return stream

    def filter_njk_stream(self, stream):
        for token in stream:
            # patch strict equality operator `===`
            if token.test("eq:==") and stream.current.test("assign:="):
                yield Token(token.lineno, "name", "is")
                yield Token(token.lineno, "name", "sameas")
                stream.skip(1)
            else:
                yield token

    def preprocess(self, source, name, filename=None):
        if filename and filename.endswith(".njk"):
            return njk_to_j2(source)
        else:
            return source


class NunjucksUndefined(jinja2.runtime.Undefined):
    __slots__ = ()

    def __getattr__(self, _):
        """
        Make undefined that is chainable, where both __getattr__ and __getitem__
        return itself rather than raising an :exc:`UndefinedError`:

        >>> foo = ChainableUndefined(name='foo')
        >>> str(foo.bar['baz'])
        ''
        >>> foo.bar['baz'] + 42
        Traceback (most recent call last):
          ...
        jinja2.exceptions.UndefinedError: 'foo' is undefined
        """
        return self

    __getitem__ = __getattr__

    # Allow treating undefined as an (empty) dictionary.
    # This works because Undefined is an iterable.
    def items(self):
        return self

    # Allow escaping with Markup. This is required when
    # autoescape is enabled. Debugging this issue was
    # annoying; the error messages were not clear as to
    # the cause of the issue (see upstream pull request
    # for info https://github.com/pallets/jinja/pull/1047)
    def __html__(self):
        return str(self)

    # attempt to behave a bit like js's `undefined` when concatenation is attempted
    def __add__(self, other):
        if isinstance(other, str):
            return "undefined" + other
        return super().__add__(other)

    def __radd__(self, other):
        if isinstance(other, str):
            return other + "undefined"
        return super().__radd__(other)


class NunjucksCodeGenerator(jinja2.compiler.CodeGenerator):
    def visit_CondExpr(self, node, frame):
        if not (self.filename or "").endswith(".njk"):
            return super().visit_CondExpr(node, frame)

        def write_expr2():
            if node.expr2 is not None:
                return self.visit(node.expr2, frame)
            # rather than complaining about a missing else
            # clause we just assume it to be the empty
            # string for nunjucks compatibility
            return self.write('""')

        self.write("(")
        self.visit(node.expr1, frame)
        self.write(" if ")
        self.visit(node.test, frame)
        self.write(" else ")
        write_expr2()
        self.write(")")


_njk_signature = "__njk"
_builtin_function_or_method_type = type({}.keys)


class Environment(jinja2.Environment):
    code_generator_class = NunjucksCodeGenerator

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("extensions", [NunjucksExtension])
        kwargs.setdefault("undefined", NunjucksUndefined)
        super().__init__(*args, **kwargs)
        self.filters["indent_njk"] = indent_njk

    def join_path(self, template, parent):
        """Enable the use of relative paths in template import statements."""
        if template.startswith(("./", "../")):
            return path.normpath(path.join(path.dirname(parent), template))
        else:
            return template

    def _handle_njk(method_name):
        def inner(self, obj, argument):
            if isinstance(argument, str) and argument.endswith(_njk_signature):
                # a njk-originated access will always be assuming a dict lookup before an attr
                final_method_name = "getitem"
                final_argument = argument[: -len(_njk_signature)]
            else:
                final_argument = argument
                final_method_name = method_name

            # pleasantly surprised that super() works in this context
            retval = builtins.getattr(super(), final_method_name)(obj, final_argument)

            if (
                argument == f"length{_njk_signature}"
                and isinstance(retval, jinja2.runtime.Undefined)
                and isinstance(obj, Sized)
            ):
                return len(obj)
            if (
                isinstance(argument, str)
                and argument.endswith(_njk_signature)
                and isinstance(retval, _builtin_function_or_method_type)
            ):
                # the lookup has probably gone looking for attributes and found a builtin method. because
                # any njk-originated lookup will have been made to prefer dict lookups over attributes, we
                # can be fairly sure there isn't a dict key matching this - so we should just call this a
                # failure.
                return self.undefined(obj=obj, name=final_argument)
            return retval

        return inner

    getitem = _handle_njk("getitem")

    getattr = _handle_njk("getattr")
