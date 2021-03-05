.. _12-ordering-of-tariff-transactions:

12. Ordering of tariff transactions
===================================

Date: 2021-02-24

Status
------

Approved

Context
-------

The tariff is communicated to other systems through a stream of transactions.
Each transaction represents an “atomic” set of changes to a single business
object (which may involve multiple records e.g. creating a new measure results
in the creation of the measure itself and a number of components or conditions).

In particular, it’s important to stress that a transaction “should not” contain
a collection of related changes, but “should” focus on a specific record code
(e.g. the removal of a goods nomenclature and the measures that apply to it
would need to happen in multiple transactions).

The TARIC3 business rules almost exclusively talk about what is and is not a
valid end-state for the data to be in. For example,
:class:`~quotas.business_rules.QA3` specifies that a sub-quota must not have a
bigger balance than it’s parent quota.

Ordering within transactions
----------------------------

The point at which the business rules are applied to each transaction is not
consistent – the TARIC Principles doc has the following to say:

    CREATES: All  validations  can  be applied  on  a  record  by  record  basis
    for  inserts,  but  the  final acceptance should be done at transaction
    level. Validations can be applied at record level as the records are sent in
    a logical order, but the transaction should be refused as a whole if a
    validation fails.

    UPDATES: Validations must be applied at transaction level for updates.

    DELETES: Validations must be applied at transaction level for deletes.

This leads us to the conclusion that records should be sorted by record code and
subrecord code in a transaction in order to meet the create requirements and
that in the best case all business rules must be met by the end of a
transaction.

In reality, it does not seem to matter what order the subrecord codes appear in
a transaction as long as they do not depend on each other. For example, there
seems to be no issue with sending measure footnote associations (430-20) before
measure components (430-05).

Ordering of transactions
------------------------

However, many of the business rules talk about the relationship between
different business objects – and hence edits to these objects will occur in
separate transactions. As business rules must be fulfilled at the end of every
transaction, some of the rules therefore impose tricky constraints on the
ordering of transactions.

Here are some specific cases where the business rules describe relationships
between models, and the ordering constraints this imposes on the transactions.

#1: Terminating a geographical area membership where exclusions exist
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The business rule :class:`~measures.business_rules.ME67` links membership of a
geographical area to measure exclusions:

    The membership period of the excluded geographical area
    must span the validity period of the measure.

This means that whenever a geographical area is to be removed from a group, any
measures for that group that exclude the geographical area and are still active
must be changed too. This will require one transaction to update the
geographical area membership and another transaction per measure.

The updates to the measures must happen first, because if end-dating the
geographical membership went first ME67 would be violated at the end of the
first transaction. So in this case we have an update to one record type (250)
needing to come after changes to another record type (430) despite it having a
greater record code.

Because exclusions do not have their own validity dates, there are actually two
ways to handle this depending on the intention. The measure exclusions can be
deleted (which will affect the validity for the entire lifetime of the measure –
may not represent reality if the geographical area really was excluded in the
past) or the measures can be end-dated and replaced with new identical measures
without the exclusions (presumably to coincide with the end date on the
membership).

So, note that it would not be sufficient to sort transactions by record code or
by update type (create, delete, update) here – neither alone nor in combination
would this result in the correct ordering. But it’s possible that a more complex
system could understand the dependencies between objects (i.e. that memberships
depend on geo exclusions) and could order the transactions correctly such that
dependent records come after their dependencies.

#2: Changing the length of a goods nomenclature
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The business rule :class:`~commodities.business_rules.NIG30` requires the
validity of a goods nomenclature to always be greater than or equal to any
measure that references it:

    When a goods nomenclature is used in a goods measure then the validity
    period of the goods nomenclature  must span the validity period of the goods
    measure.

So if one wants to update the validity of a goods nomenclature code, there will
be one transaction to change the start or end date on the code and one
transaction per measure to update the validity dates on the measure (i.e. to
start the measure later or end it earlier). In this case, all of the changes
will be “updates” to existing records – no creations or deletions are needed.

If the end date on the goods nomenclature is being moved earlier, changing the
goods nomenclature first would break NIG30 so the measures must all be updated
first. If the end date on the goods nomenclature is being moved later, changing
the measures first would break NIG30 so the goods nomenclature must be updated
first.

So from this we see that the order of transactions cannot depend so
simply on record codes update types, or even on a topological dependency between
types, but is also dependent on the nature of the change being made.

#3: Changing the volume of quotas with associations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The business rule :class:`~quotas.business_rules.QA3` implies an ordering on
changes to linked quota volumes:

    When converted to the measurement unit of the main quota, the volume of a
    sub-quota must always be lower than or equal to the volume of the main
    quota.

As an example, if a main quota A and a sub-quota B are associated, QA3 implies A
>= B at the end of every transaction.

If one wants to reduce the volume of both quotas, this will necessitate a
transaction to update A and a transaction to update B. If the volume is being
reduced, QA3 requires that the sub-quota volume is reduced in the first
transaction (so B < A) and then the main quota volume is reduced in the second
transaction. But if the volume is being increased, the increase of A must come
first because if we increased B first we wouldn’t have B <= A at the end of the
transaction.

So in this use case, records of the same type are being updated and again the
order of transactions is dependent on what the change actually is.

#4: Changing the quota order number of a quota
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The business rule :class:`~measures.business_rules.ME116` requires a quota order
number linked to a measure to exist:

    When a quota order number is used in a measure then the validity period of
    the quota order number must span the validity period of the measure.

As quota order numbers can be reused with different validity periods, this
essentially implies that where a quota order number is referenced on a measure
at least one quota order number record must exist with a greater than or equal
validity period.

What’s interesting is that quota order number records come with a SID as a
logical key. This means that an update to the quota order number record can
change the order number without requiring the creation of a new record. The UK
Tariff has done this in a couple of places because it means the quota order
number record retains any definitions, origins or exclusions already created as
these reference the SID. The measure however does not reference the SID –
presumably for legacy reasons, it only references the order number.

So a change of an order number requires one transaction to update the quota
order number record and then one each to update the measures. If one was to
update the order number first, any measures that referenced it would now be
referencing a missing order number and would no longer be valid. If one was to
update the measures first, they would be now referencing an order number that
doesn’t exist yet and they wouldn’t be valid.

The only solution here is to first delete all of the measures referencing the
order number, issue a transaction changing the order number, and then recreate
all the measures referencing the new number. This is one of many examples where
the “single record per transaction” model breaks down and we are forced to
delete measures to cope with an update to something they reference (there are
similar problems with additional codes and goods nomenclature).

Here there is no ordering of transactions that would not break the business
rules if we just tried to solve the problem with updates (which would be a
reasonable starting assumption). The system or its users will need to “know”
that changing a quota order number can only be performed to a certain pattern.

What we have learned
^^^^^^^^^^^^^^^^^^^^

* It’s possible to define an order using dependencies between records in some
  cases.
* Dependencies between transactions relies not just on the type of the
  records in them but also on the exact change being made.
* There are certain sets of transactions that are impossible to order correctly,
  and whose changes need to be performed in a different/specific way.
* We therefore cannot rely completely on automatic ordering – we also have to
  solve the problem of generating transactions in the first place that correspond
  to a known pattern (whether automatically or through training).

Handling business rule errors
-----------------------------

Given the above learning about the inability of the system to correctly order
transactions by itself, two options present themselves for the approach to
business rule errors:

1. Apply the business rules after every change, and do not save any change that
   results in a business rule violation. The ordering of the transactions is just
   the order in which they were created.
2. Let the users apply edits in any order, and only check business rules once
   all the changes have been made. The ordering of the transactions is decided
   later, and by default would be the creation order but could be tweaked to handle
   any rule violations that arise from ordering.

Both of these options require users to understand the business rules violations
and them being able to perform certain types of change correctly (e.g. #4
above). Some features can be written to assist (e.g. by giving more helpful
messages than just the text of the rule) but as noted above this is limited and
so user training will always be necessary.

The advantage of option 1 over option 2 is that it reduces the possibility that
users will have to undo much of their work in order to fix violations. It is
also easier from a system perspective to assume that any data is always
compliant with the business rules. It also removes the need for the system to
provide features to reorder transactions and edit away errored data.

Using multiple workbaskets
^^^^^^^^^^^^^^^^^^^^^^^^^^

Option 1 falls down when multiple workbaskets come into play. As each
application of the business rules should only take into account the transactions
that have come previously, it’s possible that two workbaskets that separately
pass validation will not work when applied sequentially (e.g. if workbasket 1
updates a commodity code description and workbasket 2 creates a different
description on the same day). In general then data in a workbasket can come into
violation of business rules even after it has been authored.

Option 1 is therefore of limited use, and we are forced to accept that even if
we enforce the business rules on edit we still have to deal with errored data
(assuming of course that we want to support multiple draft workbaskets at once).
We will need to provide training and/or tools to allow users to deal with these
situations – again, the number of possibilities for the rules to be broken like
this is numerous and automation is only of limited use.

Decision
--------

The business rules and the code that runs them will be refactored to reflect the
ordering instructions: business rules will be run at the end of every
transaction, or after every model for CREATE transactions, and will only
consider data that has been committed as of the transaction being checked.

The system will not attempt to reorder transactions itself and will instead use
the order in which the transactions were created. Business rules will still be
enforced on save for models in draft mode, but the system will not assume that
draft data meets all the business rules.

Patterns will be used to handle particular use cases that are tricky or
unintuitive. These will encode the domain-level ordering required to avoid
business rule violations (e.g. when updating an order number). They will be
exposed in the UI in some form and may override the simpler operations in some
cases (e.g. it may be appropriate to not allow users to update order numbers
without using the pattern).

The system will provide tools to allow users to deal with errored data. The
exact nature of these is to be defined, but will need to include the ability to
reorder transactions and remove errored models.
