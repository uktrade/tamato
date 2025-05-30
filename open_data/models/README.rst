Important
=========

Ignore it at your own risk!!!
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you create a new model, you must patch the created migration using the following instruction.


Generate the migration from Django, and before running it, add to the module

.. code:: python

    from open_data.models.utils import schema_required

Inside the class ``Migration`` add the following code

.. code:: python

    if schema_required():
        schema_name = 'reporting"."'
    else:
        schema_name = ""


Change the ``db_table`` in options:

.. code:: python

          "db_table": f"{schema_name}XXXX",

Look at 0002_create_tables migration as an example implementation of the patch.


If you forget to patch the migration, you will get several misterious failures while testing!

(You can stop reading now if you are not interested in the why.)


Why
===
The tables in the open_data app are stored in a separate SCHEMA.
This allows to exclude them from daily backups.

To create a table in a different schema using Django, the table name (including the SCHEMA)
is specified in db_table in the META of the model. The function create_table_name takes care of
the correct format for the name.
The SCHEMA is created in the first migration.

Because TAP runs the test using a 'nomigration' flag, the tests will fail because there is no
SCHEMA available.
Also, the migrations are used to create the tables in the SQLITE database used to export
the data, and SQLITE does not support SCHEMA.

The utility function 'schema_required' catches the test and SQLITE situations.
If the SCHEMA is not needed, the schema name is removed from the table name
and the migration will work as expected.


.. note::
    The handling of the SCHEMA in TAP is a clever hack, and as all the clevers hack do,
    will catch the developer ignoring the information in this file!

