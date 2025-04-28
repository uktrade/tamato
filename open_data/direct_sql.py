from open_data.apps import APP_LABEL
from open_data.models.utils import get_lookup_name


def get_create_materialised_view_sql():
    return f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {get_lookup_name()} AS
                SELECT  common_trackedmodel.ID as old_id, current_version_id
                FROM public.common_trackedmodel
                INNER JOIN common_versiongroup
                    ON (common_trackedmodel.version_group_id = common_versiongroup.id)
            WHERE (current_version_id IS NOT NULL AND NOT (common_trackedmodel.update_type = 2));
            
            CREATE UNIQUE INDEX old_id_idx ON {get_lookup_name()} (old_id);
            CREATE INDEX current_version_id_idx ON {get_lookup_name()} (current_version_id);
            """


def get_drop_fk_sql():
    # It will be impossible to update the tables in the open data area with the
    # foreign keys constrain in place. But it is useful to declare them in the Django
    # models, so Django will create the correct queryset: the following query t
    # dropped them in the database while they are still the model definition.
    # The 'magic' query has been copied from somewhere in Stackoverflow!

    return f"""
    DO $$DECLARE r record;
        BEGIN
            FOR r IN SELECT table_schema, table_name, constraint_name
    				FROM information_schema.table_constraints AS tc 
    				WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name like '{APP_LABEL}%'
            LOOP
                EXECUTE 'ALTER TABLE '|| quote_ident(r.table_schema) || '.' || quote_ident(r.table_name)|| ' DROP CONSTRAINT '|| quote_ident(r.constraint_name) || ';';
            END LOOP;
        END$$;
    """
