# Tariff Management Tool (TAMATO)

[![codecov](https://codecov.io/gh/uktrade/tamato/branch/master/graph/badge.svg)](https://codecov.io/gh/uktrade/tamato)

## Quickstart

### Using Docker

## Environment Variables

Apart from environment variables mentioned in the running locally section, these additional settings are available. 
 
| Name | Description |
| ---- | ----------- | 
| MINIO_ACCESS_KEY        | Username for local Minio instance (s3 implementation) |
| MINIO_SECRET_KEY        | Password for local Minio instance (s3 implementation  |


## Building

Run the following command to build the docker image:

    docker-compose build


## Running

Run the app:

    docker-compose up
    
On your first run, you will need to run database migrations (in another terminal):

    docker-compose run tamato ./manage.py migrate
    
Create the HMRC bucket:

Browse to Minio http://localhost:9003 and create a local s3 bucket with a name 
matching the HMRC_STORAGE_BUCKET_NAME setting in .env

View the app:

Browse to http://localhost:8000/


### Prerequisites

Skip this section if running under docker.

The following dependencies are required to run this app:
 * Python 3.9.x
 * Node 14.16.x
 * Postgres 12.x
 * Redis 5.x

The app requires an s3 bucket on AWS or a compatible implementation, such as Minio


### Running locally

Create a database instance:

    $ sudo su - postgres
    postgres $ createdb tamato

Create a user / role:

    postgres $ psql
    postgres=# CREATE USER <user> SUPERUSER PASSWORD '<password>';

Import from a dump of the database:

    postgres $ psql -d tamato -f /tmp/tamato-db-dump.sql

You can either instruct postgres to trust local connections via settings
in your `pg_hba.conf` file or, preferably, add an entry in your `.env` file in
order to provide the database username and password that you have set (as
above):

    DATABASE_URL=postgres://<user>:<password>@localhost:5432/tamato

Create a Python virtualenv and install the dependencies:

    python -m venv venv
    . venv/bin/activate
    pip install -U pip
    pip install wheel
    pip install -r requirements-dev.txt

Create a `.env` file containing environment variables:

    cp sample.env .env

Fetch and compile GOV.UK Frontend dependency:

    npm install
    npm run build

Collect static assets:

    ./manage.py collectstatic
    
Open another terminal and start Celery beat:

    celery -A common.celery beat --loglevel=info

Open another terminal and start a Celery worker     

    celery -A common.celery worker --loglevel=info     

In the first terminal, run the app:

    ./manage.py runserver

Then you can browse to http://localhost:8000/ to view the app.

In order to login, first create a Django user with superuser access:

    ./manage.py createsuperuser

Set the value of `SSO_ENABLED` environment variable to `false` in your `.env`
and navigate to and sign in via the Django admin login at
http://localhost:8000/admin/.


## Testing

To run tests use the following command:

    ./manage.py test

To run with coverage use the following:

    ./manage.py test -- --cov

When running tests the settings module defaults to settings.test


## Environment Variables

| Name | Description |
| ---- | ----------- | 
| SSO_ENABLED              | Use DIT staff SSO for authentication. You may want to set this to `"false"` for local development. If `"false"`, Django's ModelBackend authentication is used instead. (default `"true"`) |
| AUTHBROKER_URL           | Base URL of the OAuth2 authentication broker (default https://sso.trade.gov.uk) |
| AUTHBROKER_CLIENT_ID     | Client ID used to connect to the OAuth2 authentication broker |
| AUTHBROKER_CLIENT_SECRET | Client secret used to connect to the OAuth2 authentication broker |
| DATABASE_URL             | Connection details for the database, formatted per the [dj-database-url schema](https://github.com/jacobian/dj-database-url#url-schema) |
| LOG_LEVEL                | The level of logging messages in the web app. One of CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.                                     |
| CELERY_LOG_LEVEL         | The level of logging for the celery worker. One of CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET.                                       |
| TAMATO_IMPORT_USERNAME   | The TAMATO username to use for the owner of the workbaskets created.                                                                    |
| NURSERY_CACHE_ENGINE     | The engine to use the the Importer Nursery Cache. Defaults to importer.cache.memory.MemoryCacheEngine.                                  |
| CACHE_URL                | The URL for the Django cache. Defaults to redis://0.0.0.0:6379/1.                                                                       |
| SKIP_VALIDATION          | Whether Transaction level validations should be skipped or not. Defaults to False.                                                      |
| USE_IMPORTER_CACHE       | Whether to cache records for the importer (caches all current records as they are made). Defaults to True.                              |
| CELERY_BROKER_URL        | Connection details for Celery to store running tasks, defaults to the CACHE_URL.                                                        |
| CELERY_RESULT_BACKEND    | Connection details for Celery to store task results, defaults to CELERY_BROKER_URL.                                                     |
| HMRC_STORAGE_BUCKET_NAME | Name of s3 bucket used for uploads by the exporter                                                                                      |
| HMRC_STORAGE_DIRECTORY   | Destination directory in s3 bucket for the exporter                                                                                     |
| AWS_ACCESS_KEY_ID        | AWS key id, used for s3                                                                                                                 |
| AWS_SECRET_ACCESS_KEY    | AWS secret key, used for s3                                                                                                             |
| AWS_STORAGE_BUCKET_NAME  | Default bucket [unused]                                                                                                                 |
| AWS_S3_ENDPOINT_URL      | AWS s3 endpoint url                                                                                                                     |                                                                                                                   |


## Using the importer

The Tariff Management Tool (TAMATO) needs to import TARIC3 XML data from both the
EU (for historical data) and from HMRC (for VAT measures).

TaMaTo provides an import which parses TARIC3 XML and inserts the data into the
TAMATO database.

Run the script to see the command line arguments:

    ./manage.py import_taric --help

This command is broken into two stages:

1) Chunking the file and loading into the DB. If a file is greater than 50MB it is broken into chunks and those chunks
   saved into the database. This can be run in isolation using the command `./manage.py chunk_taric`.

2) Passing the chunks through the importer system into TrackedModels. This can be run in isolation using the
   command `./manage.py run_import_batch`.

## Using the exporter

The Tariff Management Tool (TAMATO) exports data to HMRC.

During normal operation uploads trigger the upload_transactions task which uploads transactions as XML to the HMRC bucket. 

### Manually trigger the upload to s3

    celery -A common.celery call exporter.tasks.upload_transactions  

The celery job UUID is output and the command quits.  To see output switch to the celery workers console.
A more ergonomic way of launching the celery job is to launch the management command:

    ./manage.py upload_transactions

### Dump transactions

Transactions waiting to be uploaded to the HMRC S3 bucket can be saved to a file or output to stdout
using a management command: 

     ./manage.py dump_transactions [-o filename]
     
Output defaults to stdout if filename is - or is not supplied.


## How to deploy

The app is hosted using GOV.UK PaaS and is deployed with Jenkins.

### Accessing databases in GOV.UK PaaS

To access databases hosted in GOV.UK PaaS directly, you will need a PaaS login and the
[cf CLI tool](https://docs.cloudfoundry.org/cf-cli/install-go-cli.html). There are a couple of useful `Makefile` targets to make creating an SSH
tunnel to the databases easier.

NB this requires [`jq`](https://stedolan.github.io/jq/) to be installed too.

```sh
$ make paas-login
> Login to PaaS
API endpoint: api.london.cloud.service.gov.uk

Temporary Authentication Code ( Get one at https://login.london.cloud.service.gov.uk/passcode ): 
```
Open the URL above to login and get a code, then paste it into the terminal. You will then be prompted to select a space:
```sh
Targeted org dit-staging.

Select a space:
1. tariffs-dev
2. tariffs-staging
3. tariffs-training
4. tariffs-uat

Space (enter to skip):
```

Then, start the SSH tunnel
```sh
$ make paas-db-tunnel app=tamato-staging
> Get tamato-staging-db service key...
> SSH Tunnel to tamato-staging-db...
```
At this point, you can connect your local database client to `127.0.0.1:54321`, the credentials are stored in `${app}-db.json` in the current directory - **DO NOT ADD THIS FILE TO THE REPO!**

To close the tunnel, hit Ctrl-c.

For convenience, the following command parses the JSON file and connects using the `psql` client. Run this in another terminal, in the same directory as the JSON file.
```sh
$ make paas-db-tunnel-shell app=tamato-staging
```

Make sure to delete the `${app}-db.json` file after use.

## How to write tests

Tests are written with Pytest

## How to contribute

Please submit a Pull Request

### Formatting.

This project uses the [pre-commit](https://pre-commit.com/) tool to run [black](https://github.com/psf/black) as an autoformatter and [reorder-python-imports](https://github.com/asottile/reorder_python_imports) to format imports.

By pip-installing `requirements-dev.txt` you will have the pre-commit package
installed, so you should now set up your pre-commit hooks:

    $ pre-commit install

## How to change application dependencies (libraries)

## Known manual procedures
