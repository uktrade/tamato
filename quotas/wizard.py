from formtools.wizard.storage.session import SessionStorage


# TODO: Check if this is necessary/if this and MeasureCreateSessionStorage
# can be homogenised to become a single helper class
class SubQuotaCreateSessionStorage(SessionStorage):
    """
    Session storage subclass, used by the wizard view to save data,
    ommitting ADD and DELETE elements used to manage form state.
    """
    def set_step_data(self, step, cleaned_data):
        print('*'*40, 'set_step_data', step)
        cleaned_data_copy = cleaned_data.copy()
        for key in list(cleaned_data_copy):
            # Don't save ADD and DELETE fields in the session.
            if key.endswith("-ADD") or key.endswith("-DELETE"):
                cleaned_data_copy.pop(key)
        super().set_step_data(step, cleaned_data_copy)
