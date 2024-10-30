from django.db import models

from open_data.apps import APP_LABEL

SCHEMA_NAME = "reporting"
LOOK_UP_VIEW = f"{SCHEMA_NAME}.foreign_key_lookup"

# After creating the tables, I need to remove the FK from the database
# using direct SQL, so the Django table will still build the correct joins in the sql
# https://stackoverflow.com/questions/5273717/how-to-drop-constraint-by-name-in-postgresql
# The following will delete the foreign keys
# DO $$DECLARE r record;
#     BEGIN
#         FOR r IN SELECT table_schema, table_name, constraint_name
# 				FROM information_schema.table_constraints AS tc
# 				WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema='reporting'
#
#         LOOP
#             EXECUTE 'ALTER TABLE '|| quote_ident(r.table_schema) || '.' || quote_ident(r.table_name)|| ' DROP CONSTRAINT '|| quote_ident(r.constraint_name) || ';';
#         END LOOP;
#     END$$;

# To create materialised view
# create materialized view reporting.foreign_key_lookup as
# 	SELECT  common_trackedmodel.ID as old_id, current_version_id
# 	FROM public.common_trackedmodel
#  	INNER JOIN common_versiongroup
# 		ON (common_trackedmodel.version_group_id = common_versiongroup.id)
# WHERE (current_version_id IS NOT NULL AND NOT (common_trackedmodel.update_type = 2))
# ;
#
# CREATE UNIQUE INDEX old_id_idx
#   ON reporting.foreign_key_lookup (old_id);


class ReportModel(models.Model):
    def contain_all_fields(self):
        # This function will check that there are no new field in the shadowed table
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
        return f'{SCHEMA_NAME}"."{APP_LABEL}_report{new_name}'

    @classmethod
    def create_update_query(cls):
        # used the generated queries for 'latest update' to create the query
        # updating the report table with the latest values
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

    def copy_data(self):
        pass

    def clear_data(self):
        pass

    class Meta:
        abstract = True
