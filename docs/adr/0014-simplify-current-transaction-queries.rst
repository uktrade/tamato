14. Simplification of current transaction queries
=================================================

Date: 2021-09-27

Status
------

Approved


Context
-------

The TaMaTo application keeps a version history of the UK tariff, with each
version of a record having a version ID and an associated transaction ID.
TaMaTo enables users to create draft edits to the tariff, and these are
stored in the database as unpublished versions.

When querying the database, either to display the current UK tariff details, or
to check business rules are not violated, those queries must specify the
"current" transaction to fetch only the versions of records that are pertinent.
This is further complicated by the need to fetch unpublished versions when
querying data that has been modified in the user's current session.

This complication affects several aspects of the application:

1. Data entry. When users enter data into forms, the options they are presented
   with are retrieved from the database. These options must be only those that
   are valid at the time of the request, and must not include any historical
   versions.

2. Business rules. The current workbasket contains versions of database records
   which are not yet considered fact, but must be included in business rule
   queries to check that when they are published in the tariff they will not
   violate those rules.


Alternatives considered
-----------------------

Thread-local storage
~~~~~~~~~~~~~~~~~~~~

We store the current transaction in thread-local storage as a sort of global variable
that provides the context to all queries in the current thread - this avoids
interference with other concurrent requests to the application. Django-CRUM_ provides an
API to managing thread-local storage.

Some Django form fields (eg ``ModelChoiceField``) take a queryset as an initialisation
argument and execute the query at render-time. In this case, we want to construct a
queryset that retrieves the current transaction at execution time and not at
initialisation. To ensure we fetch the current transaction ID value at query execution
time, we can use a dynamic |Value|_ object, for example:

.. code:: python

    from crum import get_current_request
    from django.db.models import IntegerField, Value

    from workbaskets.models import WorkBasket


    class CurrentTransactionId(Value):
        def __init__(self, **kwargs):
            kwargs["output_field"] = IntegerField()
            # skip Value constructor which assigns to self.value
            super(Value, self).__init__(**kwargs)

        @property
        def value(self):
            request = get_current_request()
            if request:
                transaction = WorkBasket.get_current_transaction(request)
                if transaction:
                    return transaction.id

            return None


This allows us to construct a queryset that fetches the current transaction at query
execution time:

.. code:: python

    queryset = Footnotes.objects.filter(transaction_id=CurrentTransactionId())

Using these dynamic ``Value`` objects, we can refactor ``latest_approved`` and
``approved_up_to_transaction`` as follows:

.. code:: python

    def latest_approved(
        self,
        transaction: Optional[Transaction] = None,
    ) -> TrackedModelQuerySet:
        """
        Get the approved versions of the model, or the latest draft versions if they
        exist within a transaction preceding (and including) the given transaction in
        the workbasket of the given transaction.
        """

        if transaction:
            current_workbasket_id = Value(transaction.workbasket.id, output_field=IntegerField())
            transaction_order = transaction.order
        else:
            # dynamic values defined similarly to CurrentTransactionId above
            current_workbasket_id = CurrentWorkBasketId()
            transaction_order = CurrentTransactionOrder()

        is_current_version = Q(is_current__isnull=False)

        in_current_workbasket = Q(
            transaction__workbasket_id=F("current_workbasket_id"),
            transaction__order__lte=transaction_order,
        )

        versions_in_workbasket = Q(
            version_group__versions__transaction__workbasket_id=F("current_workbasket_id"),
            version_group__versions__transaction__order__lte=transaction_order,
        )
        latest_version_id = Max(
            "version_group__versions",
            filter=(Q(current_workbasket_id__isnull=False) & versions_in_workbasket),
        )

        unapproved_if_no_workbasket = Q(current_workbasket_id__isnull=True, is_current__isnull=True)
        older_versions_in_workbasket = Q(current_workbasket_id__isnull=False) & ~Q(latest=F("id"))

        deletions = Q(update_type=UpdateType.DELETE)

        return (
            self.annotate(current_workbasket_id=current_workbasket_id)
            .filter(is_current_version | in_current_workbasket)
            .annotate(latest=latest_version_id)
            .exclude(unapproved_if_no_workbasket)
            .exclude(older_versions_in_workbasket)
            .exclude(deletions)
        )

This allows initialising (for example) a ``ModelChoiceField`` with a queryset that uses the current
transaction at form render time:

.. code:: python

    measure_type = ModelChoiceField(queryset=MeasureType.objects.latest_approved())


Temporal database extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~

We extend the Postgres database with a temporal tables extension, which handles the
versioning of data so that we do not have to do it in our code. Compiled extensions may
not be permitted to install on our hosted database servers, so `nearform/temporal_tables`_
could be used instead as it is implemented in PL/SQL.

This approach, while moving a lot of complexity in queries out of the
application and into the database extension, would still require keeping track
of the current transaction in the application, possibly using the thread-local
storage solution above.


Decision
--------

For the purposes of making our Django ORM queries simpler, we will make use of
Django-CRUM_ and thread-local storage to automate fetching the current
transaction from the request (if it exists) and filtering querysets using it.


Consequences
------------

* Easier to read and invoke queries that must filter by the current transaction
* An added dependency to maintain
* Slightly "magical" code may make maintenance more difficult


.. _Django-CRUM: https://django-crum.readthedocs.io/en/latest/
.. _nearform/temporal_tables: https://github.com/nearform/temporal_tables
.. |Value| replace:: ``Value``
.. _Value: https://docs.djangoproject.com/en/dev/ref/models/expressions/#value-expressions
