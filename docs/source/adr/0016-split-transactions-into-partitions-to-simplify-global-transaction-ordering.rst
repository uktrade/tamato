.. _16-split-transactions-into-partitions-to-simplify-global-transaction-ordering:

16. Split Transactions into partitions to simplify global transaction ordering

Date: 2022-02-03

Status
------

Retrospective ADR for TP-841

Context
-------

TAMATO follows TARICs concept of a "transaction" as a record of changes to the Tariff.

In TAMATO Transaction is a concrete database model with records reflecting TRANSACTION elements imported from TARIC XML.

Order of transactions is important, before the PR for partitioning was written global ordering of transactions used the following logic:

1.  Transactions with DELETED status were excluded.

2. Transactions were ordered into groups:
 - The first workbasket (considered the "seed file")
 - Any following workbaskets that are not draft
 - Transactions in the DRAFT workbaskets are last

Within these groups transactions were sorted by the `order` field.


Decision
--------

Where possible replace grouping logic with concrete data in the database.

This is achieved by adding a `partition` field, to Transaction, corresponding to the above groups and with values that reflect the groups ordering:

    SEED_FILE = 1

    REVISION = 2

    DRAFT = 3

Maintaining compatibility with the existing system
--------------------------------------------------

To ensure the system works as before, the concept of a Transaction Partition Schema is introduced.
`TransactionPartitionScheme`s implement the logic that is called when a workbasket is saved and it's Transactions need to move from `DRAFT` to `SEED_FIRST` or `REVISION`.

The logic in `TransactionPartitionScheme` is executed during workbasket approval, at the moment of saving.
It is important that `TransactionPartitionScheme` is called at the last moment to ensure consistency.


SEED_FIRST
..........
The SEED_FIRST Transaction Schema implements the same logic the app had before partitions were implemented.
Transactions in the first workbasket are set to SEED_FIRST and any others go in the REVISION partition.

SEED_ONLY, REVISION_ONLY
........................
These schemas can be used when there is a need to manually specify a partition from the commandline.


Consequences
------------

- Global ordering is simplified to sorting by partition, order.
- Ordering in views is much simpler
- More complex logic is moved to `TransactionPartitionScheme` and only called during workbasket approval.
- In the future multiple seed file transactions may be used if required.


Implementation
--------------
https://github.com/uktrade/tamato/pull/334
