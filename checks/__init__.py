"""
The ``checks` subsystem runs background checks against models.

Users are able to produce models using the UI that do not pass validation of
TARIC business rules. When they do this, they need to be informed of the issues
so that they can go and manually correct them. Business rule checking is slow,
so running all of the rules to find and display errors cannot be run during a
single web request.

So the requirements on the checks subsystem are:

1. Show the user all of the errors in their (1000+) model changes in the UI.
2. When the user has finished all of their editing, allow the final output to be
   downloaded quickly without them having to wait for the checks to run.

Checks are designed to be run asynchronously using Celery. Synchronous checking
is available but is only designed for use in testing, debugging or within a
single database transaction in a Jupyter notebook.

Whilst the checks are designed to run business rules, this is not hard-coded and
it is easy to implement new types of checks that aren't business rule focused if
desired. Any new business rules that are implemented will automatically be
picked up.

In order to make web requests fast, the checks system includes a cache of what
checks have have been run, whether any have failed, and how. Like any cache,
checks can become outdated if transactions in draft are modified. The system
includes the ability to detect this and re-run new checks accordingly.

The system is designed to be tolerant towards background tasks being killed at
any point during their execution. The system does not assume that a task will be
completed if it is started. The database therefore is the only stateful part of
the system and only what is present in the database controls the execution of
new checks and whether or not a workbasket is valid and can be sent. This is
achieved by gathering metadata unique to the data to be processed and verifying
that the data hasn't been edited in the meantime by checking that the metadata
has the same values as it had at the beginning.

The system is also designed to be tolerant of poor integration with the rest of
the app. It does not require that all of the places that edit transactions also
know how to start checks. Instead, a scheduled task is used to hunt for
transactions that have not been checked yet and pre-emptively check them. This
means that developers on the whole do not need to think about how to start
checks and can just leave the system to run checks at appropriate times.

The assumptions in the system are:

1. Transactions are immutable once they have been approved (i.e. they enter a
   partition in ``TransactionPartition.approved_partitions()``). Checks against
   approved transactions will not be checked again.
2. There is at least one transaction in an approved partition.
3. Changes made to a draft transaction take the form of a removal or an addition
   of a model – models are never edited directly. Unpicking this assumption is
   hard, so it's recommended that the system sticks to this if it can.
4. Checks can be run independently of each other and do not modify data.
   (Actually, checks can modify data as long as they do it in the manner
   described in point #3 – all of other checks will then immediately be
   invalidated, so in the worst case this is a waste of resources.)
"""
