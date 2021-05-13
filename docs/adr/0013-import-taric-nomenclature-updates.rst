13. Import TARIC nomenclature updates
=====================================

Date: 2021-04-26

Status
------

Approved


Context
-------

The Northern Ireland Protocol (NIP) requires the classification hierarchy of the
United Kingdom to be the same or a superset of the classification hierarchy of
the European Union (so that a trade against a product from the UK tariff can be
unambiguously mapped to a product in the EU tariff).

This means that any changes made to the TARIC nomenclature must also be made to
the UK nomenclature. Specifically, this means only changes to the following
TARIC record types need to be reflected:

* Goods nomenclature
* Goods nomenclature indent
* Goods nomenclature description
* Goods nomenclature origin
* Goods nomenclature successor

We will continue to have access to a TARIC XML feed that incorporates all of the
goods nomenclature changes for the lifetime of the NIP. We also have
:ref:`the-importer` that can read this XML format and reflect the contents in
our database.

Scenarios
^^^^^^^^^

Scenario 1: Add new code
~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: CodeAdded

    node [shape=circle, width=0.6, fixedsize=true];
    C1 -- C2;
    C1 -- C3;
    C2 [color=green, fillcolor=lightgreen];

When a new child code is added, there is not any scope for business rule
violations on related data.

Scenario 2: Delete code with a measure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: CodeDeleted

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C1 -- C3;
    C2 [color=red, fillcolor=pink];

    C2 -- C2 [headlabel="M", color=transparent]

:class:`~commodities.business_rules.NIG34` and
:class:`~commodities.business_rules.NIG35` do not allow a code to be deleted if
it still has a measure attached.

Scenario 3: Delete parent causing child to have new parent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: ParentCodeDeleted

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C1 -- C3;
    C3 -- C4;
    C2 -- C4 [style=dotted];

    C3 [color=red, fillcolor=pink];

    C2 -- C2 [headlabel="M", color=transparent];
    C4 -- C4 [headlabel="M", color=transparent];

Deleting (or moving) a parent node can will cause the child node to inherit a
new parent. This happens implicitly without any change required to the child or
parent themselves. :class:`~measures.business_rules.ME32` will not allow the
child code and its new parent to have measures that overlap.

Scenario 4: Change time span
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: ChangeTimeSpan

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C1 -- C3;
    C2 [color=goldenrod, fillcolor=lightgoldenrod];

    C2 -- C2 [headlabel="M, F", color=transparent]

:class:`~commodities.business_rules.NIG30` and
:class:`~commodities.business_rules.NIG31` do not allow a code to have its
validity dates modified if they don't span the validity range of any measure
attached. :class:`~commodities.business_rules.NIG22` has the same requirement
for footnotes.

Scenario 5: Change suffix from real to intermediate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: ChangeSuffix

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C1 -- C3;
    C3 -- C4;

    C3 [color=goldenrod, fillcolor=lightgoldenrod];
    C4 [color=green, fillcolor=lightgreen];

    C3 -- C3 [headlabel="M", color=transparent];

When a code receives new children, a code can be converted into a non-declarable
code and new codes created underneath. If the suffix on a code is updated from
80 to non-80, :class:`~measures.business_rules.ME7` does not allow measures to
continue to exist on the code.

Scenario 6: Increase indent level to get sibling as parent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: IncreaseIndent

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C1 -- "C3 v1";
    C2 -- "C3 v2" [style=dotted, color=goldenrod];

    "C3 v1" [color=goldenrod, fillcolor=lightgoldenrod];
    "C3 v2" [color=goldenrod, fillcolor=lightgoldenrod];

    "C3 v1" -- "C3 v1" [headlabel="M, F", color=transparent];
    "C3 v2" -- "C3 v2" [headlabel="M, F", color=transparent];
    C2 -- C2 [headlabel="M", color=transparent];

If the indent of a code is increased it can now appear under a new parent. Both
of the codes could have measures that previously did not overlap but now would.
:class:`~measures.business_rules.ME32` does not allow two measures in the same
commodity code hierarchy to overlap.

If the item ID of the commodity code gets updated as well, it's possible for
:class:`~measures.business_rules.ME88` to complain because any measures that
exist on the code may only have applied to codes at a higher explosion level.

There is a similar problem for footnotes caused by
:class:`~measures.business_rules.ME71` and
:class:`~commodities.business_rules.NIG18`.

Scenario 7: Change indent results in child with new parent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: IndentChangeNewChild

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C1 -- "C3 v1";
    C2 -- "C3 v2" [style=dotted, color=goldenrod];
    "C3 v1" -- C4;
    C2 -- C4 [style=dotted, color=goldenrod];

    "C3 v1" [color=goldenrod, fillcolor=lightgoldenrod];
    "C3 v2" [color=goldenrod, fillcolor=lightgoldenrod];

    C2 -- C2 [headlabel="M", color=transparent];
    C4 -- C4 [headlabel="M", color=transparent];

In the same way as Scenario 6, changing the indent and/or item ID of a code can
cause measure business rules to fire. In this case however the measures do not
need to be on the code being moved. If the moved code had children which have
now received new parents, it's possible to get any of the above errors on that
child's measures instead, even though no change was made to the child itself.

Scenario 8: Indent change results in taking children from other parent
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graph:: IndentChangeWithStolenChild

    node [shape=circle, width=0.6, fixedsize=true]
    C1 -- C2;
    C2 -- "C3 v1";
    C2 -- C4;
    C1 -- "C3 v2" [style=dotted, color=goldenrod];
    "C3 v2" -- C4 [style=dotted, color=goldenrod];

    "C3 v1" [color=goldenrod, fillcolor=lightgoldenrod];
    "C3 v2" [color=goldenrod, fillcolor=lightgoldenrod];

    "C3 v1" -- "C3 v1" [headlabel="M", color=transparent];
    "C3 v2" -- "C3 v2" [headlabel="M", color=transparent];
    C4 -- C4 [headlabel="M", color=transparent];

In this case an indent change causes a code to take on new children again at a
risk of :class:`~measures.business_rules.ME32` errors. Note though that there
aren't any other business rules that the child can trigger through having a new
parent.

Hence we learn that it will be sufficient to check all business rules on
a commodity code after its update and its *old* children – new children do not
need to be checked.

Decision
--------

We will extend the importer system to be able to read and process just the goods
nomenclature changes in a TARIC XML delta and whilst ignoring all other changes.

The EU has the opportunity to update any of its own data to avoid business rule
errors that would occur when a nomenclature change is made. For example, to
avoid a :class:`~commodities.business_rules.NIG30` error may require some
updates to measure end or start dates, and these will need to be made in a
transaction *before* the nomenclature change.

But the UK tariff will not know about possible nomenclature changes before
ingesting them, so in general a change to the nomenclature could introduce a
business rule error. To account for this, the import system will need to look
for errors as each nomenclature change is ingested and retroactively add
transactions that update related data to avoid those errors from occuring.

In the simplest version of the algorithm, business rules are checked at the end
of each transaction and related data can simply be updated or deleted. Any holes
in the data that are left will need to be corrected manually.

Added transactions could simply delete all related data that causes errors, but
there are opportunities for automatic fixes that remove some need to manually
recreate errored data. Where these fixes are safe to generally make, they should
be used in favour of simply deleting data to minimise manual rework.

There are also opportunities for errors to occur on models that aren't even
changed by the transaction, such as in Scenarios 3 and 7 above. So in addition
to running business rules on the goods nomenclature objects themselves, we will
also need to run them on any of the commodity code's children that it had
*before* it was updated.


Behaviour in responding to business rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The algorithm will need to respond to the following business rule violations:

NIG30 or NIG31
~~~~~~~~~~~~~~

.. autoclass:: commodities.business_rules.NIG30
  :noindex:
.. autoclass:: commodities.business_rules.NIG31
  :noindex:

This can occur if goods nomenclature validity dates have been changed (e.g. to
introduce an end date where one was not present) but there are measures using that
nomenclature that are valid outside of the new period.

The course of action will be to reduce the validity period of the measure to
match the new constraint of the nomenclature. The validity period of the measure
should not be increased as this may not represent policy intent.

* If the nomenclature now ends before the measure, set the measure end date to
  be the end date of the nomenclature.
* If the nomenclature now starts after the measure, set the measure start date
  to be the start date of the nomenclature.
* If the nomenclature dates now no longer overlap with the measure, delete the measure.

NIG22
~~~~~

.. autoclass:: commodities.business_rules.NIG22
  :noindex:

This is similar to the above where the goods nomenclature validity dates have
been changed and now no longer cover the validity dates of a footnote
association.

The same rules as above should be applied with the footnote association in place
of the measure.

NIG34 or NIG35
~~~~~~~~~~~~~~

.. autoclass:: commodities.business_rules.NIG34
  :noindex:
.. autoclass:: commodities.business_rules.NIG35
  :noindex:

The goods nomenclature has just been deleted but there are a number of measures
that remain in existence.

The only course of action here is to delete the remaining measures.

Footnote association
~~~~~~~~~~~~~~~~~~~~

There is in fact another case here which no business rule accounts for: the
goods nomenclature can be deleted whilst still in use on a footnote association.

As above, the only course of action is to delete the remaining associations.

ME1 or ME32
~~~~~~~~~~~

.. autoclass:: measures.business_rules.ME1
  :noindex:
.. autoclass:: measures.business_rules.ME32
  :noindex:

In this case a goods nomenclature is now a parent of something where before it
was not, and the measures defined on that nomenclature now overlap with measures
on another code.

This can be if:

1. the delta has created a new indent
2. the delta has updated the dates on an old indent
3. the delta has updated the indent on an old indent
4. the delta has deleted some other indent and now this one is valid longer
5. the delta has changed the item id on the commodity and now it lives elsewhere

The strategy is to try and manouever the measure around the problematic indent
by updating the dates, which in case #1 or #2 can preserve as much data as
possible. If this isn't possible, we have to just give up and delete the
measure.

* If the measure overlaps with start of indent, update measure end date to be
  indent validity end
* If the measure overlaps with the end of indent, update measure start date to
  be indent validity end
* If the measure overlaps with the full range of indent, delete measure

A more complicated automatic fix involving trying to identify child codes that
should now host the measure is possible but requires more complex human
intervention, so it should not be used for now.

ME7
~~~

.. autoclass:: measures.business_rules.ME7
  :noindex:

It is technically possible to have the suffix of a goods nomenclature updated to
turn it from real to intermediate code where measures cannot be created.

The only feasible option is to delete the measure.

ME88, ME71 and NIG18
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: measures.business_rules.ME71
  :noindex:
.. autoclass:: measures.business_rules.ME88
  :noindex:
.. autoclass:: commodities.business_rules.NIG18
  :noindex:

When the item ID of the goods nomenclature is updated, its possible that the
measures or footnotes attached to the goods nomenclature are no longer allowed
to be present because the application code of the associated footnote or
explosion level of the associated measure type may limit how low in the goods
hierarchy the association can be made.

In the case of ME71 or NIG18, the footnote associations with the measure or
commodity code respectively will need to be deleted. (Changes to item ID do not
have validity dates associated with them, but should be very rare.)

In the case of ME88, the measure will need to be deleted.


Full algorithm
^^^^^^^^^^^^^^

.. digraph:: BasicAlgorithm

    node [shape=box]
    graph [ratio=1.414]

    Start [shape=circle, color=green, label=""]
    Start -> "Find business rule violations" [label="Model is a Goods Nomenclature or Indent"]
    Start -> "Save model" [label="Model is Goods Nomenclature\nDescription,\nOrigin or Successor"]
    Start -> "Ignore model" [label="Model is something else"]

    "Find business rule violations" -> "Violation is NIG30/31"
      "Violation is NIG30/31" -> "Update measure end date" [label="Updated to end sooner"]
          "Update measure end date" -> "Re-run business rules"
      "Violation is NIG30/31" -> "Update measure start date" [label="Updated to start later"]
          "Update measure start date" -> "Re-run business rules"
      "Violation is NIG30/31" -> "Delete measure" [label="No longer overlaps"]
          "Delete measure" -> "Re-run business rules"

    "Find business rule violations" -> "Violation is NIG22"
      "Violation is NIG22" -> "Update footnote association\nend date" [label="Updated to end sooner"]
          "Update footnote association\nend date" -> "Re-run business rules"
      "Violation is NIG22" -> "Update footnote association\nstart date" [label="Updated to start later"]
          "Update footnote association\nstart date" -> "Re-run business rules"
      "Violation is NIG22" -> "Delete association" [label="No longer overlaps"]
          "Delete association" -> "Re-run business rules"

    "Find business rule violations" -> "Footnote association still exists"
      "Footnote association still exists" -> "Delete association"

    "Find business rule violations" -> "Violation is NIG34/35"
      "Violation is NIG34/35" -> "Delete measure"

    "Find business rule violations" -> "Violation is ME32"
      "Violation is ME32" -> "Update measure end date\nto be indent validity start" [label="Measure overlaps with\nstart of indent"]
        "Update measure end date\nto be indent validity start" -> "Re-run business rules"
      "Violation is ME32" -> "Update measure start date\nto be indent validity end" [label="Measure overlaps with\nend of indent"]
        "Update measure start date\nto be indent validity end" -> "Re-run business rules"
      "Violation is ME32" -> "Delete measure" [label="Measure overlaps with\nfull range of indent"]

    "Find business rule violations" -> "Violation is ME7"
      "Violation is ME7" -> "Delete measure"

    "Find business rule violations" -> "Violation is ME1"
      "Violation is ME1" -> "Delete measure"

    "Find business rule violations" -> "Violation is ME71"
      "Violation is ME71" -> "Delete association"

    "Find business rule violations" -> "Violation is NIG18"
      "Violation is NIG18" -> "Delete association"

    "Find business rule violations" -> "Violation is ME88"
      "Violation is ME88" -> "Delete measure"

    "Re-run business rules" -> "Find business rule violations"
    
    "Find business rule violations" -> "No violations on any measure"
      "No violations on any measure" -> "Save model"


Note that "save model" in the above diagram does not imply saving to the
database hasn't already occured. In order to check most of these business rules
it will be necessary to save the goods nomenclature model first and then to put
the measure "before" it. Hence, the system will also need to be able to reorder
transactions that may have already been saved.

Note also that transaction IDs present in the XML should be ignored and each
transaction allocated the next subsequent transaction ID in UK global order.


Consequences
------------

Note that it is very possible for the EU to update goods nomenclature objects in
a way that break its own rules. But as the system doesn't have a huge amount of
choice in the matter of whether to apply these, even if business rules on
imported nomenclature objects are checked, they need to be saved anyway.

If the system makes a change to related data the business rules for it will also
need to be run. This could result in violations of some business rule not listed
here which is outside the scope of the algorithm. In this case, the import will
need to abort and all changes should be rolled back.

As with any algorithm that makes arbitrary changes to its own state, it is
possible that repeated automatic fixes of data could result in a loop – one
business rule fix causes another to fire and the fix to that one causes the
original data to be recreated, etc. As a safety mechanism, the algorithm
probably needs a depth counter to understand how many passes of fixes have been
attempted for a given model. If this counter exceeds some finite configured
value, the import should fail and all changes should be rolled back.

Some advanced automatic fixing that avoids more holes in data is possible by
considering changes across multiple transactions. An example that has been
observed is a goods nomenclature being deleted and then recreated under a
different SID. Another example might be a goods nomenclature being removed and
then being recreated under a different heading.

In both of these cases, it would be nice to be able to apply automatic
resolutions based on all of the transactions processed, however this is
significantly harder to achieve as it requires a lot more storage of state. In
principle, state may need to be examined between import runs if the EU removes a
code on one day and then resurrects it on a subsequent day. So for now the
algorithm will only do the minimum required to avoid business rule violations
and only consider one transaction at a time with no memory between them.
