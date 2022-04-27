Environment variables
---------------------

.. envvar:: SSO_ENABLED

    (default ``True``)

    Use DIT staff SSO for authentication. You may want to set this to ``"false"`` for
    local development. If ``"false"``, Django's ModelBackend authentication is used
    instead.

.. envvar:: AUTHBROKER_URL

    (default ``https://sso.trade.gov.uk``)

    Base URL of the OAuth2 authentication broker

.. envvar:: AUTHBROKER_CLIENT_ID

    Client ID used to connect to the OAuth2 authentication broker

.. envvar:: AUTHBROKER_CLIENT_SECRET

    Client secret used to connect to the OAuth2 authentication broker

.. envvar:: DATABASE_URL

    (default ``postgres://localhost:5432/tamato``)

    Connection details for the database, formatted per the `dj-database-url schema
    <https://github.com/jacobian/dj-database-url#url-schema>`__

.. envvar:: LOG_LEVEL

    (default ``DEBUG``)

    The level of logging messages in the web app. One of ``CRITICAL``, ``ERROR``,
    ``WARNING``, ``INFO``, ``DEBUG``, ``NOTSET``

.. envvar:: CELERY_LOG_LEVEL

    (default ``DEBUG``)

    The level of logging for the celery worker. One of ``CRITICAL``, ``ERROR``,
    ``WARNING``, ``INFO``, ``DEBUG``, ``NOTSET``

.. envvar:: TAMATO_IMPORT_USERNAME

    (default ``test``)

    The TAMATO username to use for the owner of the workbaskets created

.. envvar:: NURSERY_CACHE_ENGINE

    (default ``importer.cache.memory.MemoryCacheEngine``)

    The engine to use the the Importer Nursery Cache

.. envvar:: CACHE_URL

    (default ``redis://0.0.0.0:6379/1``)

    The URL for the Django cache

.. envvar:: SKIP_VALIDATION

    (default ``False``)

    Whether Transaction level validations should be skipped

.. envvar:: USE_IMPORTER_CACHE

    (default ``True``)

    Whether to cache records for the importer (caches all current records as they are made)

.. envvar:: CELERY_BROKER_URL

    (default :envvar:`CACHE_URL`)

    Connection details for Celery to store running tasks

.. envvar:: CELERY_RESULT_BACKEND

    (default :envvar:`CELERY_BROKER_URL`)

    Connection details for Celery to store task results

.. envvar:: HMRC_STORAGE_BUCKET_NAME

    (default ``hmrc``)

    Name of S3 bucket used for uploads by the exporter

.. envvar:: HMRC_STORAGE_DIRECTORY

    (default ``tohmrc/staging/``)

    Destination directory in S3 bucket for the exporter

.. envvar:: AWS_ACCESS_KEY_ID

    AWS key id, used for S3

.. envvar:: AWS_SECRET_ACCESS_KEY

    AWS secret key, used for S3

.. envvar:: AWS_STORAGE_BUCKET_NAME

    Default bucket [unused]

.. envvar:: AWS_S3_ENDPOINT_URL

    AWS S3 endpoint url

.. envvar:: SQLITE_STORAGE_BUCKET_NAME

    (default ``sqlite``)

    Bucket used for SQLite uploads

.. envvar:: SQLITE_S3_ACCESS_KEY_ID

    (default ``test_sqlite_key_id``)

    AWS key id, used for SQLite storage bucket uploads

.. envvar:: SQLITE_S3_SECRET_ACCESS_KEY

    (default ``test_sqlite_key``)

    AWS secret key, used for SQLite storage bucket uploads

.. envvar:: SQLITE_S3_ENDPOINT_URL

    (default ``https://test-sqlite-url.local/``)

    AWS S3 endpoint url, used for SQLite storage bucket uploads

.. envvar:: SQLITE_STORAGE_DIRECTORY

    (default ``sqlite/``)

    Destination directory in s3 bucket for the SQLite storage bucket

.. envvar:: GOOGLE_ANALYTICS_ID

    The id used to configure Google Tag Manager in production

.. envvar:: MINIO_ACCESS_KEY

    Username for local MinIO instance 

.. envvar:: MINIO_SECRET_KEY

    Password for local MinIO instance

.. envvar:: EXPORTER_DISABLE_NOTIFICATIONS

    (default ``False``)

    Do not call the HMRC API notification endpoint after each upload

.. envvar:: DJANGO_SETTINGS_MODULE

    (default ``settings``, or ``settings.test`` when running tests)

    The dotted import path to the python module to use for Django settings.
    Options include ``settings``, ``settings.dev`` and ``settings.test``.
