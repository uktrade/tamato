from django.db import models

from open_data.apps import APP_LABEL

SCHEMA_NAME = "reporting"
LOOK_UP_VIEW = f"{SCHEMA_NAME}.foreign_key_lookup"


def create_name_with_schema(name):
    # NOTE: the " around the stop are really important.
    # without them, the table will not be created in the correct schema
    return f'{SCHEMA_NAME}"."{APP_LABEL}_report{name}'


class ReportModel(models.Model):
    # Individual classes can define extra restrictions on the copy to the report data.
    # For instance, they may remove rows that have validity in the past
    # The 'AND' clause must be defined in the extra_where, otherwise it will give
    # an error. I could parse it and check if AND is in the clause, but it is too
    # much extra effort, as the error will be identified immediately.
    extra_where = ""
    # Some tables contains several version of the same object, but with different
    # validity. To make report creation easier, the old version will be removed
    # when remove_obsolete is set to True
    # The structure of the tables is identical, they always have a validity start
    # The field to use for aggregation has to be specified
    remove_obsolete = False
    patch_fk = True
    update_description = False
    update_table = True

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
        return create_name_with_schema(new_name)

    @classmethod
    def extra_queries(cls):
        # Individual classes can define a list of sql command to be executed
        # after the table has been updated
        return []

    @classmethod
    def update_query(cls):
        # used the generated queries for 'latest update' to create the query
        # updating the report table with the latest values
        db_from_table = cls.shadowed_model._meta.db_table
        update_field = f'INSERT INTO "{cls._meta.db_table}" ('
        read_field = ") SELECT "
        # Find the SQL query that return the latest_approved on the
        # model we are shadowing
        latest_query = str(cls.shadowed_model.objects.latest_approved().query)
        split_query = latest_query.split(" FROM")
        # The query is split at the FROM keyword, and the second part contains
        # the correct table we want to copy from and the correct WHERE clause
        query_from_and_where = f" FROM {split_query[1]}"
        # The first part of the query contains all the fields retrieved
        # by latest_approved.
        field_list = split_query[0].split()
        # The Django generated latest_approved query contains fields from the
        # track models. We only want to copy the fields from the table being shadowed
        # The next loop eliminates fields that don't belong to the table.
        for field in field_list:
            if db_from_table in field:
                read_field += field
                # Remove the table name from the field definition
                update_field += field.split(".")[1]
        # return update_field + read_field + query_from_and_where + ";"
        print(f"{cls.extra_where=}")
        return (
            f"{update_field} {read_field}  {query_from_and_where} {cls.extra_where} ;"
        )

    @classmethod
    def ignore_fk_list(cls):
        return []

    @classmethod
    def update_fk_queries(cls):
        # The foreign keys in a table don't always point to the object latest version
        # It is an unfortunate fact, with several causes. It will not be fixed, at least
        # for now. So there is a materialised view, mapping every single primary key to
        # the equivalent latest version.
        # The following code generate the queries required to update the foreign keys
        # in the table.
        # There is no attempt to make the process efficient!
        query_list = []
        if cls.patch_fk:
            ignore_list = cls.ignore_fk_list()
            for f in cls._meta.get_fields():
                if (
                    type(f) is models.fields.related.ForeignKey
                    and not f.name in ignore_list
                    and not f.primary_key
                ):
                    query_list.append(
                        f'UPDATE "{cls._meta.db_table}" '
                        f"SET {f.column}=current_version_id "
                        f" FROM {LOOK_UP_VIEW} "
                        f" WHERE {f.column} = old_id;",
                    )
        return query_list

    @classmethod
    def remove_obsolete_row_query(cls):
        query = ""
        if cls.remove_obsolete:
            #  TO DO
            # Raise error if cls.partition_field is not defined
            # Don't ask about the next horrible lines. It works
            partition_field_db = cls._meta.get_field(
                cls.partition_field,
            ).get_attname_column()[1]
            query = f"""
            DELETE 
            FROM \"{cls._meta.db_table}\"
            WHERE trackedmodel_ptr_id in
                (SELECT trackedmodel_ptr_id 
                    FROM 
                        (SELECT trackedmodel_ptr_id,
                        ROW_NUMBER() OVER (
                                      PARTITION BY {partition_field_db}
                                      ORDER BY validity_start DESC
                                    ) as DupRank                            
                        FROM \"{cls._meta.db_table}\") AS T
                        WHERE t.DupRank > 1 )
        """
        return query

    class Meta:
        abstract = True