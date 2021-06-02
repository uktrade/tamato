Record sequencing
-----------------

One of the major objectives of TARIC is to extract at regular intervals all
amendments to the database and to send them to the Member States. The
transmitted data should be in such a format that upon receipt it can be
processed automatically by a computer, and provide the source for national
tariff updates.

In order to allow Member States to process (and to validate if they wish) the
data in a meaningful way, it is important that the sequence of the data is
properly understood.

All records contain the following common information:

- a record sequence number; this controls the physical sequence of the records
- a transaction identifier, record identifier, update type: these fields
  identify the record from a logical point of view.

A particular problem is that a logical unit of work for a user can be
distributed over several tables in the database; for instance, closing a goods
nomenclature code results in changing the end date but this also closes any
footnote associations, nomenclature group memberships, etc., information which
is held in different tables.

A transaction identifier will be used to group together all database actions
covering a logical unit of work. As a result, all records involved in closing a
goods nomenclature code will be tagged with the same (unique) value, ie the
transaction identifier. As a result, records can be extracted in any sequence.
Subsequently they will be sorted by transaction identifier and record
identifier. In this way the interface file will reflect all data capture work
and system updates.

The Member States should process the file based on this transaction principle. 

Inserts
"""""""

All validations can be applied on a record
by record basis for inserts, but the final acceptance should be done at
transaction level. For example, when a goods nomenclature code is
created, several physical records will be sent in the following order:

- goods nomenclature: record identifier 40000
- goods nomenclature indent: record identifier 40005
- goods nomenclature description period: record identifier 40010
- goods nomenclature description(s): record identifier 40015
- potential relationships with nomenclature groups, footnotes: record identifiers 40020, 40025
- goods nomenclature origin: record identifier 40035

Validations can be applied at record level as the records are sent in a logical
order, but the transaction should be refused as a whole if a validation fails.

Updates
"""""""

Validations must be applied at transaction level for updates.

For example, when a nomenclature code is closed, several physical records will
be sent in the following order:

- goods nomenclature with the new end of validity date: record identifier 40000
- relationships with nomenclature groups, footnotes: record identifiers 40020, 40025
- goods nomenclature successor: record identifier 40040
 
Validations cannot be applied at record level. Validating the goods nomenclature
code means, among other things, that its validity period must span the validity
periods of its relationships. This is not the case when processing the goods
nomenclature record, but MUST be the case when all the records of that
transaction are processed. 

Deletes
"""""""

Validations must be applied
at transaction level for deletes. For example, when a goods nomenclature
code is deleted, several physical records will be sent in the following
order: 

- goods nomenclature: record identifier 40000
- goods nomenclature indent(s): record identifier 40005
- goods nomenclature description period(s): record identifier 40010
- goods nomenclature description(s): record identifier 40015
- relationships with nomenclature groups, footnotes: record identifiers 40020, 40025
- goods nomenclature origin: record identifier 40035
- goods nomenclature successor: record identifier 40040
 
Validations could be applied at record level. Deleting the goods nomenclature
code will result in deleting all its relationships. The interface file will
contain all these deletes in detail. If validation is required at that level one
could check at the end of the transaction if all the relationships have been
deleted before accepting the delete as a whole.


