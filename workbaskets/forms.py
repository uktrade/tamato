from django import forms


class SelectedObjectsStore:
    """
    This class provides a storage and update abstraction for user-selected
    items. An example use is when the contents of a Workbasket instance are
    presented to the user for selection over several pages. Because items are
    paged, a mechanism is required to preserve selections when navigating
    between item pages or away from the pages entirely.

    Django's Session class is used to preserve items.

    Selection state is updated by performing a three way difference between:
    1. State held in the session,
    2. Available list items (have any new items been added, or somehow removed),
    3. User submitted changes (POST requests performed by changing page or
       submitting a bulk operation).
    """

    def __init__(self, session, store_id):
        self._store_id = store_id  # "SELECTABLE_OBJECT_STORE"
        self._session = session

        if self._store_id not in self._session:
            self._session[self._store_id] = {}

    @property
    def object_store(self):
        return self._session[self._store_id]

    def add_selected_objects(self, objs):
        self.object_store |= objs

    def remove_selected_objects(self, objs):
        self.object_store -= objs

    def clear(self):
        """Clear out all objects from the store."""
        self.object_store.clear()


class SelectableObjectField(forms.BooleanField):
    """Associates an object instance with a BooleanField."""

    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop("obj")
        super().__init__(*args, **kwargs)


class SelectableObjectsForm(forms.Form):
    """Form used to dynamically construct a variable number of selectable
    objects."""

    def __init__(self, *args, **kwargs):
        objects = kwargs.pop("objects")
        selected_items = kwargs.get("data", [])

        super().__init__(*args, **kwargs)

        for obj in objects:
            self.fields[f"tracked_model_{obj.pk}"] = SelectableObjectField(
                required=False,
                obj=obj,
                initial=obj.pk in selected_items,
            )
