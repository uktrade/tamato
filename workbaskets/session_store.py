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

    def add_items(self, items_dict):
        copy = self.data.copy()
        copy.update(items_dict)
        self.data = copy

    def remove_items(self, items_dict):
        copy = self.data.copy()
        for k in items_dict.keys():
            copy.pop(k, None)
        self.data = copy

    def clear(self):
        """Clear out all objects from the store."""
        self._init_data()
