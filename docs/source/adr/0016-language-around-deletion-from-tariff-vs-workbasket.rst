.. _16-language-around-deletion-from-tariff-vs-workbasket-

16. Use language to make the distinction between removing data from the workbasket vs deleting from the tariff clearer
=====================================================================================================================

Date: 2022-05-9

Status
------

Proposed

Context
-------

Based on actual user experience editing a workbasket.

When the user is editing the workbasket there are two similar actions they can perform:

 - Removing an item from the workbasket
 - Requesting an item be deleted from the tariff

Currently both items use the term "delete" but the action and consequences are different.

It is easy for the user to create an item and instead of removing it from the workbasket add a request
that it is immediately deleted.

Although creating and immediately deleting is valid, it is not what the user wants and uses up an SID,
under the system as-is, every SID used has a chance of clashing with another in a concurent workbasket[1].

[1] SID clashes will be addressed in a seperate ADR.

Decision
--------

Always ensure that removing items from the workbasket and deleting from the tariff are dis-ambiguated by using language "Remove from the workbasket", and "Delete from the tariff".

"Remove" and "delete" are consistently used as extra context.

Longer examples can have context about 'what' is being taken from 'where':

 - "Remove footnote C099 from workbasket #299".
 - "Delete footnote C099 from the tariff".

Notes on language used in this example:

- The type of data being removed.
- The trackedmodels unique identifier
- The workbasket id (where appropriate)
- "Delete" for an action that will add a "Delete" transaction to the tariff (corresponding to "DELETE" in TARIC).
- "Remove" for an action that removes a trackedmodel from a workbasket.


Consequences
------------

It should be more obvious whether an action results in deleting an item from the tariff vs removing it from the workbasket, saving user and support time.


Future work
-----------

If a workbasket contains a "create" and later a "delete" transaction for the record, the UI could let
the user remove it from the workbasket instead. 

