.. _17-workbasket-suggested-fixes

17. Workbasket suggested fixes
==============================

Date: 2022-06-09

Status
------

Proposed

Context
-------

Some issues with workbaskets could be fixed automatically.

This ADR proposes a framework for the system to suggest and implement fixes using real issues that have arisen during usage of the system.

It is proposed to have two parts to the system: detect issues, and suggest fixes.

There are two clases of issue this ADR will address:

 - Changes in the system that have undesired effects
 
 - Changes that break business rules.



Example - Create and Delete an unpublished item:

In one or more workbaskets it is possible to create a trackedmodel and then delete it.
It would make more sense to not create it in the first place.


Detection:

On finding delete transaction, the system would see if the trackedmodel is already published.
If the trackedmodel is not yet published then it would flag it.


Suggested fix:

The system would suggest removing the item from the editing workbasket(s) instead of
deleting it from the tariff.


Example - Unique identifier re-use "sid clash.

The workbasket contains a new trackedmodel with an identifier already used by a published trackedmodel.

This can occur when workbaskets are edited concurrently when a workbasket is unarchived.

In a future system with multiple workbaskets the same issue may occur when re-ordering
workbaskets.


Detection:

On finding a create transaction in the workbasket the system would see if it corresponds to a published trackedmodel whose last transaction status is not DELETE.


Suggested fix:

The system would suggest allocating a new unique identifier to the trackedmodel in the workbasket.



Example - Deleting a trackedmodel that was already deleted.

The workbasket contains a request to delete a trackedmodel from the system that was already deleted.

This can occur when workbaskets are edited concurrently when a workbasket is unarchived.

In a future system with multiple workbaskets the same issue may occur when re-ordering
workbaskets.


Suggested fix:

The system would suggest removing the transaction the current workbasket.


Decision
--------


Consequences
------------

