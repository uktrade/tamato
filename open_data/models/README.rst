Important
=========

Ignore it at your own risk
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you create a new model, patch the created migration!

Add from open_data.models.utils import schema_required

Inside the class Migration add the following code
    if schema_required():
        schema_name = 'reporting"."'
    else:
        schema_name = ""

Change the db_table in options:
          "db_table": f"{schema_name}XXXX",

Look at 0002_create_tables.


In this way  the SCHEMA name is not used when testing or creating SQLite database.


If you forget to do it, you will get several misterious failures while testing!

If you are not interested in the why, you can stop reading.


Why
===
The tables in the open_data app are stored in a separate SCHEMA.
This allows to exclude them from daily backups.

To create the table in a different schema using Django, the table name (including the SCHEMA)
is specified in db_table in the META of the model. The function create_table_name takes care of
the correct format for the name.
The SCHEMA is created in the first migration.

Because TAP runs the test using a 'nomigration' flag, the tests will fail because there is no
SCHEMA available.
Also, the migrations are used to create the tables in the SQLITE database used to export
the data, and SQLITE does not support SCHEMA.

The utility function 'schema_required' can catch the test and SQLITE situations.
If the SCHEMA is not needed, the schema name can be removed from the table name
and the migration will work as expected.

It is a clever hack, and as all the clever hacks do,
will catch the developer ignoring the README

