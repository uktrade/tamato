Testing
=======

Running tests
-------------

There are several ways to run tests, the recommended way is to use ``make``:

.. code:: sh

    $ make test

This will run all tests and generate a test coverage report. To run without coverage
(which is somewhat faster), use the following:

.. code:: sh

    $ make test-fast

Alternatively, you can run tests using ``pytest`` for more detailed configuration of the test run. See the various
options with the following:

.. code:: sh

    $ pytest --help

When running tests :envvar:`DJANGO_SETTINGS_MODULE` defaults to
``settings.test``


Find and debug intermittent test failures
-----------------------------------------

The simplest way to find intermittent test failures is to keep running
them in a loop. It's worth leaving it running for at least a few test
runs.

.. code:: sh

    $ while pytest -s -v; do :; done

In the example above -s -v is used to output stdout and enable verbose
output. Timing issues more bugs can be surfaced by setting the amount of
processes to a number higher than the amount of CPU threads, e.g. 12 or
16 for an 8 thread CPU:

.. code:: sh

    $ while sleep 45 && pytest -s -v -n=12; do :; done

Debugging with WebPDB, IPD, PDB++
---------------------------------

By default tests run in multiple processes using pytest-xdist - a side
effect is that debuggers over stdout such as pdb, ipdb, pdb++ do not
work.

Using webpdb gets round this: https://pypi.org/project/web-pdb/

When running in a single process (see below) pytest-ipdb or pdb++ can be
good choices, in that case use -s so that pytest doesn't capture stdout:

.. code:: sh

    $ pytest -s

Run tests in a single process
-----------------------------

Running in a single process can eliminate pytest-xdist as a cause of
errors.

.. code:: sh

    $ pytest -n0

pytest-random-order randomises the order of test, using it can surface
bugs around hidden state, install it:

.. code:: sh

    $ pip install pytest-random-order

Use random order:

.. code:: sh

    $ pytest -n0 --random-order

Speed up runtimes by using Pyston instead of CPython
----------------------------------------------------

| Pyston is a faster python implementation that aims for compatibility with the default CPython implementation.
| Ad-hoc testing on one laptop showed tests completed in 6 minutes in CPython and 4 with Pyston.

Download and install a release from here:
https://github.com/pyston/pyston/releases

*  Create a python environment using venv
   
*  Install TaMaTo and its dependencies.

*  Run tests as usual.

.. warning:: The version of virtualenv on Ubuntu 20.04 is old and incompatible, it is advisable to use venv instead here:

.. code:: sh

    $ pyston -mvenv
