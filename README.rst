Tariff Management Tool
======================

|codecov|

The Tariff Management Tool (TaMaTo) is a web application that enables Tariff Managers to
browse and make changes to the UK Global Tariff, and submit these changes to HMRC.

The tool is available at https://www.manage-trade-tariffs.trade.gov.uk/


Development environment setup
-----------------------------

Prerequisites
~~~~~~~~~~~~~

The following dependencies are required to run this app:

- Python_ 3.8.x
- Node.js_ 16.8.x
- PostgreSQL_ 12
- Redis_ 5.x

The app requires an AWS S3 bucket or a compatible implementation, such as MinIO_

.. _Python: https://python.org/
.. _Node.js: https://nodejs.org/
.. _PostgreSQL: https://postgresql.org/
.. _Redis: https://redis.io/
.. _MinIO: https://min.io/

If using MacOS then libmagic is required:

    $ brew install libmagic


Database
~~~~~~~~

Create a database instance and user:

.. code:: sh

    $ sudo su - postgres
    postgres $ createdb tamato
    postgres $ psql -c "CREATE USER <username> SUPERUSER PASSWORD '<password>';"

Make a note of the ``<username>`` and ``<password>`` for use in the
:envvar:`DATABASE_URL` environment variable.

Import from a dump of the database:

.. code:: sh

    postgres $ psql -d tamato -f /tmp/tamato-db-dump.sql

To get a database dump, please contact the TAP team.

Installing
~~~~~~~~~~

.. code:: sh

    $ git clone git@github.com:uktrade/tamato
    $ cd tamato
    $ python -m venv venv
    $ source venv/bin/activate
    $ pip install -U pip
    $ pip install wheel -r requirements-dev.txt
    $ npm install
    $ npm run build

Those using Mac m1 laptops may have problems installing certain packages (e.g. 
psycopg2 and lxml) via requirements-dev.txt. In this scenario you should run the 
following from a rosetta terminal (see `this article 
<https://www.courier.com/blog/tips-and-tricks-to-setup-your-apple-m1-for-development/>`_ ), 
substituting your own python version as appropriate:

.. code:: sh

    $ pip uninstall psycopg2
    $ brew install postgresql
    $ export CPPFLAGS="-I/opt/homebrew/opt/openssl@1.1/include"
    $ export LDFLAGS="-L/opt/homebrew/opt/openssl@1.1/lib -L${HOME}/.pyenv/versions/3.8.10/lib"
    $ arch -arm64 pip install psycopg2 --no-binary :all:

Credit due to armenzg and his `answer here 
<https://github.com/psycopg/psycopg2/issues/1286#issuecomment-914286206>`_ .

Running
~~~~~~~

Create a ``.env`` file containing :doc:`environment variables <envvars>`

.. code:: sh

    $ cp sample.env .env

Open another terminal and Compile SCSS and Javascripts:

.. code:: sh

    $ python manage.py collectstatic

To be able to login to the app, you will first need to create a Django user with
superuser access:

.. code:: sh

    $ python manage.py createsuperuser

Then run the app:

.. code:: sh

    $ python manage.py runserver

Then you can browse to http://localhost:8000/ to view the app.
To access the Django admin page, browse to http://localhost:8000/admin/.

Testing
~~~~~~~

To run tests use the following command:

.. code:: sh

    $ python manage.py test

For more detailed information on running tests, see :doc:`testing`


Dockerisation
-------------

Fully dockerised service
~~~~~~~~~~~~~~~~~~~~~~~~

Prerequisites:
    - A local instance of the tool can be run using `Docker <https://www.docker.com/>`__.
    - A database dump - contact the TAP team for a database snapshot.


Download the codebase:

.. code:: sh

    $ git clone git@github.com:uktrade/tamato
    $ cd tamato

Build and Run for the first time:

.. code:: sh

    $ cp sample.env .env
        # Not used will be used for specific local docker stuff
        # cp docker-compose.override.yml.example docker-compose.override.yml

    # to overwrite default db dump name pass in DUMP_FILE=db_dump.sql
    $ make docker-first-use
        # take a tea break to import the db dump then
        # enter super user details when prompted 
        # and visit localhost:8000/ when the containers are up

Run the tamato app every other time:

 .. code:: sh

    $ make docker-build
    $ make docker-up

Go to http://localhost:8000/ in your web browser to view the app

Import from a dump of the database:

.. code:: sh

    # to overwrite default db dump name pass in DUMP_FILE=tamato_db.sql
    # this overwrites the default file set in the makefile variable
    $ make docker-db-dump

Sometimes docker gets clogged up and we need to clean it:

.. code:: sh

    # cleans up images & volumes
    $ make docker-clean
    # cleans up everything including the cache which can get filled up because of db dumps
    $ make docker-deep-clean

Run database migrations:

.. code:: sh

    $ make docker-migrate

Create a superuser, to enable logging in to the app:

.. code:: sh

    $ make docker-superuser

Run tests from within a docker container:

.. code:: sh

    $ make docker-test
    $ make docker-test-fast

DOCKER_RUN=run --rm by default but can be set to exec if you have containers up and running
General commands:

.. code:: sh

    $ make docker-down # brings down containers
    $ make docker-up-db # brings up db in the background
    $ make docker-makemigrations # runs django makemigrations
    $ make docker-checkmigrations # runs django checkmigrations
    $ make docker-bash # bash shell in tamato container
    $ make docker-django-shell # django shell in tamato container


Hybrid host + container approach
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may prefer a hybrid approach to running Tamato, say, executing the Redis
service and Celery workers in containers and the remaining services in the host
environment. To do so, create a `docker-compose.override.yml` file to allow
loading environment settings that are specific to this configuration:

.. code:: yml

    version: '3'

    services:
    celery:
        env_file: 
        - .env
        - settings/envs/docker.env
        - settings/envs/docker.override.env

    rule-check-celery:
        env_file: 
        - .env
        - settings/envs/docker.env
        - settings/envs/docker.override.env

Create a `docker.override.env` file:

.. code::

    # Point containerised services at the host environment hosted DB.
    DATABASE_URL=postgres://host.docker.internal:5432/tamato

Now start dockerised instances of Redis and the Celery worker services:

.. code:: sh

    $ docker-compose up -d celery-redis celery rule-check-celery


Using the importer
------------------

The Tariff Management Tool (TaMaTo) needs to import TARIC3 XML data from
both the EU (for historical data) and from HMRC (for VAT measures).

TaMaTo provides an import which parses TARIC3 XML and inserts the data
into the TAMATO database.

Run the script to see the command line arguments:

.. code:: sh

    $ python manage.py import_taric --help

This command is broken into two stages:

1. Chunking the file and loading into the DB. If a file is greater than
   50MB it is broken into chunks and those chunks saved into the
   database. This can be run in isolation using the command

   .. code:: sh

      $ python manage.py chunk_taric

2. Passing the chunks through the importer system into TrackedModels.
   This can be run in isolation using the command

   .. code:: sh

      $ python manage.py run_import_batch

Using the exporter
------------------

The Tariff Management Tool (TaMaTo) exports data to HMRC.

During normal operation uploads trigger the ``upload_transactions`` task
which uploads transactions as XML to the HMRC bucket.

Running the exporter
~~~~~~~~~~~~~~~~~~~~

The exporter pushes data to a queue, which one or more asynchronous worker
processes monitor and perform the upload to S3, so as not to block the web
server.

To run the exporter queue process, run the following command:

.. code:: sh

    celery -A common.celery beat --loglevel=info

Open another terminal and start a Celery worker:

.. code:: sh

    celery -A common.celery worker --loglevel=info -Q standard,rule-check
    # The celery worker can be run as two workers for each queue 
    celery -A common.celery worker --loglevel=info -Q standard
    celery -A common.celery worker --loglevel=info -Q rule-check

To monitor celery workers or individual tasks run:

.. code:: sh

    celery flower

See `flower docs <https://flower.readthedocs.io/en/latest/>`_ for more details


Manually trigger the upload to s3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

    $ celery -A common.celery call exporter.tasks.upload_transactions

The celery job UUID is output and the command quits. To see output
switch to the celery workers console. A more ergonomic way of launching
the celery job is to launch the management command:

.. code:: sh

    $ python manage.py upload_transactions

Dump transactions
~~~~~~~~~~~~~~~~~

Transactions waiting to be uploaded to the HMRC S3 bucket can be saved
to a file or output to stdout using a management command:

.. code:: sh

     $ python manage.py dump_transactions [-o filename]


Output defaults to stdout if filename is ``-`` or is not supplied.

Mocking s3 upload with minio
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Follow `instructions <https://min.io/docs/minio/macos/index.html>`_ to install minio server 
2. Export MINIO_ROOT_USER and MINIO_ROOT_PASSWORD variables of your choice
3. Run server with: 

.. code:: sh
    
    minio server --quiet --address 0.0.0.0:9003 ~/data

4. Navigate to http://localhost:9003/ and login using root user and password credentials just 
   created. Create a bucket and an access key via the console.
5. Export environment variables for any storages you wish to dummy (e.g. for sqlite dump export
   this will be SQLITE_STORAGE_BUCKET_NAME, SQLITE_S3_ACCESS_KEY_ID, SQLITE_S3_SECRET_ACCESS_KEY,
   SQLITE_S3_ENDPOINT_URL, and SQLITE_STORAGE_DIRECTORY), setting s3 endpoint url to 
   http://localhost:9003/
6. Alternatively, export all environment variables temporarily to an environment such as Bash
   (useful when running a local development instance of a Celery worker):

   .. code:: sh

    set -a && source .env && set +a

Virus Scan and running locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We use a shared service accross the department for virus scanning to run locally set up the following:
1. Follow set up `instructions <https://github.com/uktrade/dit-clamav-rest>`_ and run it
2. set SKIP_CLAM_AV_FILE_UPLOAD to False and CLAM_USE_HTTP True
3. add CLAM_AV_DOMAIN without http(s):// 
4. set CLAM_AV_USERNAME,CLAM_AV_PASSWORD as the username and password found in the config.py in the dit-clamav-rest project

How to contribute
-----------------

See :ref:`contributing`


How to deploy
-------------

The app is deployed with Jenkins via the `Tariffs/TaMaTo` job. The ``master`` branch
may be deployed to ``development``, ``staging``, ``uat``, ``training`` or
``production`` environments by selecting the environment name from the **ENV**
dropdown on the `Build with Parameters` page.

Accessing databases in GOV.UK PaaS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To access databases hosted in GOV.UK PaaS directly, you will need a PaaS
login and the `cf CLI
tool <https://docs.cloudfoundry.org/cf-cli/install-go-cli.html>`__.

You will need to install the `conduit plugin <https://github.com/alphagov/paas-cf-conduit>`__:

.. code:: sh

    cf install-plugin conduit

Then you need to login to the DIT GOV.UK PaaS:

.. code:: sh

    cf login --sso -s <space>

Where ``<space>`` is one of ``tariffs-dev``, ``tariffs-staging``,
``tariffs-training`` or ``tariffs-uat``.

Once you are logged in, you can list the services hosted in the space with

.. code:: sh

    cf services


You can access ``postgres`` services with the following command:

.. code:: sh

    cf conduit <name> -- psql

So if you are logged in to the ``tariffs-dev`` space, you could access the dev
environment database with ``cf conduit tamato-dev-db -- psql``.

.. |codecov| image:: https://codecov.io/gh/uktrade/tamato/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/uktrade/tamato
