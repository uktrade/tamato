from django.db import models

from open_data.apps import APP_LABEL

SCHEMA_NAME = "reporting"
LOOK_UP_VIEW = f"{SCHEMA_NAME}.foreign_key_lookup"


class ReportModel(models.Model):
    def contain_all_fields(self):
        # This function will check that there are no new field in the shadowed table
        pass

    @staticmethod
    def create_table_name(shadowed_model):
        # to create a table in a different schema, we need to specify the schema
        # in the db_table. The new name is constructed by removing
        # the app name from the shadowed table, and prefixing the name
        # with 'report', the app_label and the schema
        shadowed_tb_name = shadowed_model._meta.db_table
        new_name = shadowed_tb_name.split(shadowed_model._meta.app_label + "_")[1]
        # NOTE: the " around the stop are really important.
        # without them, the table will not be created in the correct schema
        return f'{SCHEMA_NAME}"."{APP_LABEL}_report{new_name}'

    @classmethod
    def create_update_query(cls):
        # used the generated queries for 'latest update' to create the query
        # updating the report table with the latest values
        db_from_table = cls.shadowed_model._meta.db_table
        update_field = f'INSERT INTO "{cls._meta.db_table}" ('
        read_field = ") SELECT "
        # Find the SQL query that return the latest_approved on the
        # model we are shadowing
        latest_query = str(cls.shadowed_model.objects.latest_approved().query)
        query_splitted = latest_query.split(" FROM")
        # The query is split at the FROM keyword, and the second part contains
        # the correct table we want to copy from and the correct WHERE
        query_from_and_where = f" FROM {query_splitted[1]}"
        field_list = query_splitted[0].split()
        # The Django generated latest_approved query contains fields from the
        # track models. We only want to copy the fields from the table
        # The next loop eliminates fields that don't belong to the table.
        for field in field_list:
            if db_from_table in field:
                read_field += field
                update_field += field.split(".")[1]
        return update_field + read_field + query_from_and_where + ";"

    @classmethod
    def create_update_fk_queries(cls):
        query_list = []
        for f in cls._meta.get_fields():
            if type(f) is models.fields.related.ForeignKey:
                query_list.append(
                    f'UPDATE "{cls._meta.db_table}" '
                    f"SET {f.column}=current_version_id "
                    f" FROM {LOOK_UP_VIEW} "
                    f" WHERE {f.column} = old_id;",
                )
        return query_list

    class Meta:
        abstract = True
