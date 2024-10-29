from django.db import models

from open_data.apps import APP_LABEL

SCHEMA_NAME = "reporting"


class ReportModel(models.Model):
    def contain_all_fields(self):
        # this_model_fields_dict = {}
        # for field in self._meta_get_fields():
        #     this_model_fields_dict[field.name] = field
        #
        # for tap_field in self.shadowed._meta.get_fields():
        #     if tap_field.name == "is_current":
        pass

    @staticmethod
    def create_table_name(shadowed_model):
        # to create a table in a different schema, we need to specify the schema
        # in the db_table. The new name is constructed by removing
        # the app name from the shadowed table, and prefixing the name
        # with 'report', the app_label and the schema

        shadowed_tb_name = shadowed_model._meta.db_table
        new_name = shadowed_tb_name.split(shadowed_model._meta.app_label + "_")[1]
        return f'{SCHEMA_NAME}"."{APP_LABEL}_{new_name}'

    @classmethod
    def create_update_query(cls):
        # used the generated queries for 'latest update' to create the query
        # updating the report table
        db_from_table = cls.shadowed_model._meta.db_table
        update_field = f'INSERT INTO "{cls._meta.db_table}" ('
        read_field = ") SELECT "
        latest_query = str(cls.shadowed_model.objects.latest_approved().query)
        query_splitted = latest_query.split(" FROM")
        query_from = f" FROM {query_splitted[1]}"
        field_list = query_splitted[0].split()
        for field in field_list:
            if db_from_table in field:
                read_field += field
                update_field += field.split(".")[1]
        return update_field + read_field + query_from + ";"

    def copy_data(self):
        pass

    def clear_data(self):
        pass

    class Meta:
        abstract = True
