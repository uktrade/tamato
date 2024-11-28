MAINDB = "tamato"
REPORTINGDB = "reporting"
REPORTING_APP = "open_data"


class DatabaseRouter:
    def db_for_read(self, model, **hints):
        """Send all read operations to the specific database."""
        if model._meta.app_label == REPORTING_APP:
            return REPORTINGDB
        else:
            return MAINDB

    def db_for_write(self, model, **hints):
        """Send all write operations to the specific database."""
        if model._meta.app_label == REPORTING_APP:
            return REPORTINGDB
        else:
            return MAINDB

    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation between objects in the same database."""
        db_list = (MAINDB, REPORTINGDB)
        if obj1._state.db in db_list and obj2._state.db in db_list:
            return True
        return None

    # def allow_migrate(selfself, db, app_label, model_name=None, **hints):
    #     """Make sure the apps only appear in the related database."""
    #     if app_label == REPORTING_APP:
    #         return db == REPORTINGDB
    #     else:
    #         return db == MAINDB
