.. _15-record-architecture-decisions:

15. Make Transactions Immutable by Default
==========================================

Date: 2021-11-19

Status
------

Proposed

Context
-------

Data in Tamato is written as an set of "changes to things", stored in the "Tracked Model" model grouped by the Transaction model.
The exception to this rule are Tracked Models with Transactions in the DRAFT partition, which may be modified.

Currently immutability is a convention, but unenforced.
This ADR attempts to make the places where writing happens more visible and default to being read-only elsewhere.


Decision
--------

1. Use typing to make read-only transactions the default:

i.   MutableTransaction will be added as a proxy to the Transaction class.

MutableTransaction will be used in places where we need to modify transactions, i.e. save_drafts.

This will be a proxy to the existing Transaction class, so will work in the same way as Transaction does today.


ii.  Transaction to become read-only by default.

Transaction will gain logic to prevent save() and update() and a mechanism to get it's mutable equivilent.


iii. Update TrackedModel disallow writing non-draft data.

Update TrackedModel will be updated to the new API.



Consequences
------------

Code that writes data will have a slight overhead while being more explicit.
