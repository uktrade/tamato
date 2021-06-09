Extractions
-----------

Overview
^^^^^^^^

The intention is to provide recipients of TARIC3 data with a complete picture of
the TARIC3 database. After the Commission has delivered the TARIC3 "start-up"
file to Member States, all subsequent updates will be transmitted on a regular
basis via the TARIC3 output bridge. This start-up file, along with the regular
updates, will provide a complete record of the state of the data held in the
TARIC3 database. The data transmitted to Member States will conform as closely
as possible to the data held by the Commission on the TARIC3 database, and for
this reason DG TAXUD will utilise the TARIC3 operational database log tables,
which hold a full audit trail of all database activity.

There will be no record conversion in the TARIC3 interface. 

All updates made to the database since the last extraction will be transmitted.
This will include, for example, errors made in data capture. Thus it will be
possible for Member States to receive an insert, a modification and a delete of
the same record in the same transmission.

Complete records
^^^^^^^^^^^^^^^^

As and when amendments are made to the TARIC3 database, extractions of
complete amended records will be transmitted via the output bridge.

Null values
^^^^^^^^^^^

Where ``NULL`` values can appear in the TARIC3 database, these fixed length
fields will be transmitted to Member States as "spaces". In the Records Section
of this document these fields have been specified by means of the symbol "°" (ie
degree) in the column headed "attributes". Long description fields are handled
differently - see the paragraph on :ref:`Long_descriptions`.

.. _Long_descriptions:

Long descriptions
^^^^^^^^^^^^^^^^^

Where a long description forms part of a record specification, it is always
placed as the last field in the record. In order to optimise data transmission
times, only the number of characters contained in this field will be transmitted
to Member States (i.e. trailing null characters will be suppressed, and ending
with a quote). This means that the following record types will be transmitted as
variable length records:

- 01000 TRANSMISSION COMMENT
- 20010 FOOTNOTE DESCRIPTION
- 24505 ADDITIONAL CODE DESCRIPTION
- 40015 GOODS NOMENCLATURE DESCRIPTION 
- 41010 EXPORT REFUND NOMENCLATURE DESCRIPTION

The data-type of a long description field is 'LONG'; this is the type used in
the record specification to allow the maximum record length to be calculated for
each record type. However, in practice, since a large percentage of long
descriptions in the database will be much shorter than this maximum,
transmitting variable length records will reduce the size of the transmission
files and hence the transmission times. 

If the long description is empty, then nothing will be transmitted for that
field.

Special characters in descriptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Certain control characters which may be data captured in the database short or
long description fields could cause problems for data processing. These will be
trapped by the extraction program and converted to mark-up. Since the migration
of TARIC to the Unicode character set, only the line feed character (decimal
010) causes problems and is therefore replaced by the tag ``<P>`` in the
extraction file. 


