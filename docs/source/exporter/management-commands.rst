Management Commands
^^^^^^^^^^^^^^^^^^^

The Exporter Management Commands are wrappers around the celery tasks outputting user readable messages and a shell error-code.

upload_transactions
-------------------

Calls the `upload_workbaskets` Celery task and wait until completion and displays the result (or error) to the user.
