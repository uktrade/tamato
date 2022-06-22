from django.forms import widgets


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
