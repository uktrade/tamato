from formtools.wizard.storage.session import SessionStorage


class MeasureCreateSessionStorage(SessionStorage):
    """Session storage subclass used by the wizard view used to save only "real"
    data, which shouldn't include the ADD and DELETE elements that are used to
    manage form state."""

    def set_step_data(self, step, cleaned_data):
        cleaned_data_copy = cleaned_data.copy()
        for key in list(cleaned_data_copy):
            # Don't save ADD and DELETE fields in the session.
            if key.endswith("-ADD") or key.endswith("-DELETE"):
                cleaned_data_copy.pop(key)
        super().set_step_data(step, cleaned_data_copy)


class MeasureEditSessionStorage(MeasureCreateSessionStorage):
    pass
