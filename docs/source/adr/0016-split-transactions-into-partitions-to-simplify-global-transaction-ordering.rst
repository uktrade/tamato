.. _16-split-transactions-into-partitions-to-simplify-global-transaction-ordering:

16. Split Transactions into partitions to simplify global transaction ordering

Date: 2022-02-03

Status
------

Retrospective ADR for TP-841

Context
-------

TAMATOs database represents the tariff - (in effect: taxes paid at the border).
Changes to the tariff are originate from EU and UK.   EU data is specified in XML files following the TARIC schema, refered to as Envelopes.

TARIC changes date to the formation of the EU, and TAMATOs database schema is analogous to a simplied form of TARIC.

TAMATO follows TARICs concept of a "transaction", that groups individual changes to the Tariff.

In TAMATO a Transaction is a concrete database model that representing a TRANSACTION element imported from a TARIC envelope.

Since ordering in TARIC is significant, TAMATO must respect the ordering of data imported from TARIC XML envelopes.


Before partitioning was implemented. ordering in TAMATO occurred mostly in views using the following logic:

1. Transactions with DELETED status were excluded.

2. Transactions were grouped by workbasket; within each workbasket the transactions were sorted by their `order` field.


Workbaskets themselves were sorted in the following order:

 - The first workbasket (with pk=1)
   This workbasket only contains data imported from the initial "seed file" (a TARIC XML file containing the tariff from the formaing of the EU up to some date).

 - Published workbaskets (with any of the "approved" statuses).
   These workbaskets were imported from "delta files" (TARIC XML files containing changes from one date to another), or created in TaMaTo itself.

 - Workbaskets that have not been published (workbaskets with none of the "approved" statuses).
   These workbaskets were created in TaMaTo but have not yet been published.

This ordering was split between the views and the importer.


Transaction Types
-----------------

Based on the ordering used in the old system, transactions in TaMaTo can be split into three types:

Seed File Transactions
......................

A seed file is a large XML file used to populate the database initially, containing all the changes from the start of the
EU tariff up when then file was issued.

Transactions in the seed file are used to initially populate TaMaTo, under the old system the workbasket with id=1
is assumed to contain these transactions and was always ordered first.

"seed file" transactions should be treated as if they are immutable.


Revision Transactions
.....................

Subsequent updates are imported from "delta XML" files and called revisions (in the earlier version of the system
this naming was not formalised).

Keeping revision transactions separate from those from the seed file has advantages:

- For parallelization (the seed file can be imported in parallel with the delta files).
- For debugging versioning (you don't need to know how many transactions are in the seed file),

"revision" transactions should be treated as if they are immutable.


Draft Transactions
..................

"draft" transactions are those in a workbasket that is being edited and may be changed or deleted.

In the older system "draft" transactions were those contained in a workbasket with one of the non approved statuses (APPROVED, SENT, PUBLISHED, ERRORED).

Conceptually draft transactions come after revision transactions, ordering is only within a workbasket.

When an workbasket is published, it's transactions become "revision", and it's order number is set to the last revision transactions order number + 1.


Grouping Concepts
-----------------

These groupings encode two overlapping concepts, "ordering" and "lifecycle".

Ordering
........

Global transaction ordering is implemented by incrementing grouping transactions in order of "seed_file", "revision" and "draft" and within those using the Transaction.order field.


Lifecycle
.........

Transactions start as "draft" transactions where they are mutable, and then become "seed_file" or "revision" transactions, after which they should be immutable.


Problems
--------

The existing system didnt centralise ordering splitting it between the view and the importer.
Ordering was complex - with information having to be fetched from the workbasket to order transactions, this can add up when there is a lot of data (for example there are 9 million items in the seed file workbasket).


Decision
--------

Where possible replace grouping logic with concrete data in the database.

This is achieved by adding a `partition` enum field, to Transaction with values corresponding to the above groups and with values that reflect the groups ordering:

    SEED_FILE = 1

    REVISION = 2

    DRAFT = 3

Ordering can then by achieved by using `Transaction.objects.order_by("partition", "order")` instead of the complex queries used before.
Values in the same part of the lifecycle are next to each other (approved: SEED_FILE, REVISION, then draft: DRAFT) greatly simplifying filters for approved/non approved data.



Caveats
-------

This de-normalises some information that is in the workbasket, and when workbaskets are published it is important to update the partition of the contained transactions from DRAFT to REVISION or SEED_FILE.


Getting data into the correct partition
---------------------------------------

When draft workbaskets are published the system needs a way to save a transactions to the correct partition, this is implemented by subclasses of `TransactionPartitionScheme` which provide `get_partition` to maps a WorkbasketStatus to a Transaction partition.

Scenarios:
 - During normal operation of TaMaTo, to direct data into a SEED_FILE or REVISION

 - From the command line, where developer may need to specify a the partition to fixup some data.

Subclasses of `TransactionPartitionScheme` implement the following logic:
  - `SeedFirstTransactionPartitionScheme`
  If the transaction is in the first workbasket, partition is set to SEED_FILE (the same logic TaMaTo originally implemented in the view/importer before)

  - `UserDefinedTransactionPartitionScheme`
  Allow the user to request a particular partition (e.g. from the commandline).

The logic in `TransactionPartitionScheme` is executed during workbasket approval, at the moment of saving.
It is important that `TransactionPartitionScheme` is called at the last moment to ensure consistency.

To allow schemes to be specified on the commandline, or via celery a mechanism to look up schemes by name is provided.


Consequences
------------

- Global ordering is simplified to sorting by partition, order with no need to lookup information from the workbasket.
- More complex logic is moved to `TransactionPartitionScheme` and only called during workbasket approval.
- In the future multiple seed file transactions may be used if required.


Conclusion, what is not covered
-------------------------------

The partitioning PR moved the logic from the view and importer to somewhere central (while providing some more facilities) - it doesn't make any effort to separate those concerns, future work may want to cover this.
Because the partitions are used for more than one thing (and hold a de-normalised version of the workbasket status) it can be hard for new users to get acquainted with.

Implementation
--------------
https://github.com/uktrade/tamato/pull/334
