Tariff Management Tool
======================

|codecov|

The Tariff Management Tool (TaMaTo) is a web application that enables Tariff Managers to
browse and make changes to the UK Global Tariff, and submit these changes to HMRC.

The tool is available at https://www.manage-trade-tariffs.trade.gov.uk/

Getting started
---------------

A local instance of the tool can be run using `Docker <https://www.docker.com/>`__.

Download the codebase:

.. code:: sh

    $ git clone git@github.com:uktrade/tamato
    $ cd tamato

Build the Docker image:

.. code:: sh

    $ cp sample.env .env
    $ docker-compose build

Run the tamato app:

.. code:: sh

    $ docker-compose up

Go to http://localhost:8000/ in your web browser to view the app

Import from a dump of the database:

.. code:: sh

    $ docker-compose exec -T db psql -U postgres < tamato-db-dump.sql

To get a database dump, please contact the `TAP team`_.

.. _`TAP team`: mailto:stephen.corder@trade.gov.uk?subject=TaMaTo+database+dump+request

Run database migrations (in another terminal):

.. code:: sh

    $ docker-compose exec tamato python manage.py migrate

Create a superuser (in another terminal), to enable logging in to the app:

.. code:: sh

    $ docker-compose exec tamato python manage.py createsuperuser


Development environment
-----------------------

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

    celery -A common.celery worker --loglevel=info


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
