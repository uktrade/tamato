from django.forms import FileInput
from django.forms import widgets
from django.template import loader
from django.utils.safestring import mark_safe


class RadioSelect(widgets.ChoiceWidget):
    """Overrides templates to add the proper govuk classes."""

    template_name = "common/widgets/multiple_input.html"
    option_template_name = "common/widgets/radio_option.html"
    input_type = "radio"


class RadioNestedWidget(RadioSelect):
    """Custom form widget for use with RadioNested."""

    option_template_name = "common/widgets/nested_radio.html"

    def create_option(self, *args, **kwargs):
        return {
            **super().create_option(*args, **kwargs),
            "nested_forms": self.nested_forms[args[1]],
        }

    def bind_nested_forms(self, forms):
        self.nested_forms = forms


class FormSetFieldWidget(widgets.Widget):
    template_name = "common/widgets/formset_field.html"
    input_type = ""

    def bind_nested_forms(self, forms):
        self.nested_forms = forms

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["nested_forms"] = self.nested_forms
        return context


class AutocompleteWidget(widgets.Widget):
    template_name = "components/autocomplete.jinja"

    def get_context(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        display_string = ""
        if value:
            display_string = value.structure_code
            if value.structure_description:
                display_string = f"{display_string} - {value.structure_description}"

        return {
            "widget": {
                "name": name,
                "value": value.pk if value else None,
                "display_value": display_string,
                **self.attrs,
            },
        }

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)


class MultipleFileInput(FileInput):
    """Enable multiple files to be selected using FileInput widget."""

    allow_multiple_selected = True


class DecimalSuffix(widgets.NumberInput):
    """Identical to the Decimal widget but allows the addition of a suffix."""

    template_name = "common/widgets/decimal_suffix.html"

    def __init__(self, attrs=None, suffix="", **kwargs):
        self.suffix = suffix
        super().__init__(attrs, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        context = self.get_context(name, value, attrs)
        if self.suffix:
            context["widget"]["suffix"] = self.suffix

        template = loader.get_template(self.template_name).render(context)
        return mark_safe(template)
