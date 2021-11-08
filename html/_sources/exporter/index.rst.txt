.. _the-exporter:

The Exporter
^^^^^^^^^^^^

At a high level, the TARIC exporter has responsibility to:
 - Serialize Workbaskets into XML Envelopes of 40mb or less.
 - Upload Envelope XML to the HMRC S3 Bucket.
 - Call the HMRC notification API for each uploaded file.

These are handled by the Celery Tasks.

.. toctree::
   :maxdepth: 5
   :caption: The exporter docs:
   :glob:

   *

