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

    FIELD_NAME_PREFIX = "selectableobject_"

    def __init__(self, *args, **kwargs):
        objects = kwargs.pop("objects")

        super().__init__(*args, **kwargs)

        for obj in objects:
            self.fields[
                SelectableObjectsForm.field_name_for_object(obj)
            ] = SelectableObjectField(
                required=False,
                obj=obj,
                initial=str(obj.id) in [str(k) for k in self.initial.keys()],
            )

    @classmethod
    def field_name_for_object(cls, obj):
        """Given an object, get its name representation for use in form field
        name attributes."""
        return f"{cls.FIELD_NAME_PREFIX}{obj.pk}"

    @classmethod
    def object_id_from_field_name(cls, name_value):
        """Given a field name from this form, extract the id of the associated
        object."""
        return name_value.replace(cls.FIELD_NAME_PREFIX, "")

    @property
    def cleaned_data_no_prefix(self):
        """Get cleaned_data without the form field's name prefix."""
        return {
            SelectableObjectsForm.object_id_from_field_name(key): value
            for key, value in self.cleaned_data.items()
        }
