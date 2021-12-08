from django import forms


class SelectableObjectField(forms.BooleanField):
    """Associates an object instance with a BooleanField."""

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop("obj")
        super().__init__(*args, **kwargs)


class SelectableObjectsForm(forms.Form):
    """
    Form used to dynamically build a variable number of selectable objects.

    The form's initially selected objects are given in the form's initial data.
    """

    def __init__(self, *args, **kwargs):
        self.field_name_prefix = kwargs.pop("field_name_prefix")
        objects = kwargs.pop("objects")

        super().__init__(*args, **kwargs)

        for obj in objects:
            self.fields[f"{self.field_name_prefix}{obj.pk}"] = SelectableObjectField(
                required=False,
                obj=obj,
                initial=str(obj.id) in [str(k) for k in self.initial.keys()],
            )

    @property
    def cleaned_data_no_prefix(self):
        """Get cleaned_data without the form field's name prefix."""
        return {
            key.replace(self.field_name_prefix, ""): value
            for key, value in self.cleaned_data.items()
        }
