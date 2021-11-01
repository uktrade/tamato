Data access keys
----------------

Background and problem statement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In computer systems, a data access key consists of a single field or a
combination of fields which provide direct access to a single record. The
limitation of such a system is that none of the key fields can be changed
dynamically if the amendments have to be extracted and transmitted. 

Another problem is that, when an access key based on the logical business data
is too long (or consists of too many data elements), it becomes inefficient in
performance.

System generated number (SID)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the areas where there is a need to change access key data dynamically or
where the logical key is too long, the system will generate a unique number and
attribute it to each record occurrence. This is known as the System Identifier
or SID. The same mechanism is used in systems using e.g. invoice and order
numbers.

Example
^^^^^^^

For example, in the case of the goods nomenclature record, the access key in
logical terms is "goods nomenclature item (10) + product line (2) + validity
start date (8)". As the validity start date can change dynamically, a SID is
used as the physical access key. This SID is used in all related records, e.g.
indents, description periods, measures, etc.

The benefit is that if the user changes the validity start date, and all
validation rules are respected, there is no need to amend any related records.

Logical keys
^^^^^^^^^^^^

One negative aspect of the use of SIDs is that the system generated number,
created for technical purposes, has no tariff related meaning for a user when
reading the data. To resolve this, the system will keep within the same record a
meaningful key, i.e. the logical key. This will be the static part of the key,
i.e. the code without the date. In the example of the goods nomenclature, the
system will repeat the goods code in the related records in order that queries
based on this information can be made. This causes some data redundancy.

As a consequence of the extension of some fields, logical key fields may be
implemented as characters. This means that they may contain spaces. Spaces in
logical key fields are padded at the end of the logical key values and have no
special validity. For example the code ``XYZ `` is the same as ``XYZ``.

Conclusion
^^^^^^^^^^

Details of all records for which SIDs will be generated are shown in the records
document, the TARIC3 Interface Data Specification. Member States'
administrations, and other recipients of TARIC data, require this information
for two principal reasons: 

1. to take account of these keys in the design of their TARIC3 data reception
   software
2. to enable their computer systems to accurately process these keys.


