Celery Tasks
^^^^^^^^^^^^

Exporter celery tasks are triggered on setting Workbaskets READY_FOR_EXPORT [TBD], the upload_transactions management command, or via the celery commandline or GUI.

upload_workbaskets
------------------

`upload_workbaskets` is the main Task, delegating to two subtasks: `upload_work_workbasket_envelopes` and `send_upload_notifications`.

The two tasks are split up the end-point they call, which has some advantages:
 - Failure in one task won't delay the other (and thus the whole task queue).
 - Retries, will only retry the affected end-point (e.g. a notification failure won't result in re-uploading data).

The tasks are not split up any further because ordering of data is important, files are also used and under Celery Tasks
may not run on the same machine.


upload_work_workbasket_envelopes
--------------------------------

Responsibilities:

 - Serialize Workbaskets into XML Envelopes of 40mb or less.
 - Upload Envelope XML to the HMRC S3 Bucket.

Workbaskets with the status READY_FOR_EXPORT are queried for Transactions, which are then serialized into 1 or more
Envelope XML files with a (configurable) maximum size of 40mb.

Data is validated against the TARIC XSD before creating objects in the database (Envelope, EnvelopeTransaction and Upload) and uploading to s3.

Avoiding race conditions
------------------------

It is important that transaction ids within envelopes start at a number then iterate continuously from there.
Since data must be output to XML and only later in the Task saved to the database the Envelope table is locked for writing between writing the XML and saving to the database.

In the case of a failure in `upload_work_workbasket_envelopes` an exception is raised:
 - Connectivity exceptions:  Celery will attempt to retry the Task later [1]
 - All other exceptions: Data is rolled back and the task will fail.

[1] Retry behaviour due to connectivity failures is configurable, the defaults specifying exponential backoff and jitter (randomisation).


send_upload_notifications
-------------------------

Responsibilities:
 - Call the HMRC notification API for each uploaded file.

send_upload_notifications accepts a sequence of Envelope primary keys[2] that the `upload_work_workbasket_envelopes` saved to s3.

[2] - Best practice using Celery is to use primary keys, not model instances.


Database models
^^^^^^^^^^^^^^^

.. autoclass:: taric.models.Envelope

Represents one XML taric file that was exported.

.. autoclass:: taric.models.EnvelopeTransaction

Each Envelope has one or more EnvelopeTransactions linking it to the concrete Transactions it contains.

.. autoclass:: exporter.models.Upload

Represents the whether an upload was successful or not.


Other classes
^^^^^^^^^^^^^

As well as database models, plain old classes are used to represent ephemeral data.

RenderedTransactions
--------------------

RenderedTransactions link Transaction objects with rendered envelops in an XML file, before it has been validated or added to the database as Envelope and EnvelopeTransaction objects for upload.

MultiFileEnvelopeTransactionSerializer.split_render_transactions, generates instances of RenderedTransactions, a namedtuple holding:
 - envelope_id: TARIC envelope id, to use when later when Envelope object is created.
 - transactions:  Transaction objects rendered in this envelope.
 - output: file object envelope
 - is_oversize: True if the rendered envelope was above the max size (default 40mb)
 - max_envelope_size: The maximum envelope size that was used (default 40mb).


UploadTaskResultData:
---------------------

`Uploaded envelope ids, and user readable messages`.

Responsibilities:
 - Save state passed between the upload / notify Tasks
 - Save human readable messages for the user on Task completion.
 - Serialize data for Celery when passing data between Tasks.

Data here is passed between the subtasks of upload_workbaskets including information for the user the triggered the tasks, i.e. from a management command.
