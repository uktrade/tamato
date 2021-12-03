from django import forms


class SessionStore:
    """Session-backed dictionary store."""

    def __init__(self, request, store_id):
        self._store_id = store_id
        self._request = request

        if self._store_id not in self._request.session:
            self._init_data()

    def _init_data(self):
        self._request.session[self._store_id] = dict()
        self._request.session.modified = True

    def _get_data(self):
        self._request.session.modified = True
        return self._request.session[self._store_id]

    def _set_data(self, value):
        self._request.session[self._store_id] = value
        self._request.session.modified = True

    data = property(_get_data, _set_data)

    def add_objects(self, objs):
        copy = self.data.copy()
        copy.update(objs)
        self.data = copy

    def remove_objects(self, objs):
        copy = self.data.copy()
        for k in objs.keys():
            copy.pop(k, None)
        self.data = copy

    def clear(self):
        """Clear out all objects from the store."""
        self._init_data()


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
