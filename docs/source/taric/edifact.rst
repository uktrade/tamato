EDIFACT
-------

Introduction
^^^^^^^^^^^^

For the electronic transmission of data, EDIFACT lays down guidelines referring
to the definition of data items, data segments and data messages in the
following documents: 

- UNTDED (United Nations Trade Data Elements Directory)
- UN/EDIFACT Syntax Implementation Guidelines
- UN/EDIFACT Message Design Guidelines
 
These guidelines have been used wherever appropriate. It is assumed that a
message equates to a file, and that a segment equates to a record.

Separators
^^^^^^^^^^

Every record has an EDIFACT data element separator (+) immediately after the
record identifier.

The UNB, UNH and UNZ segments have, in addition, a data element separator
between each attribute and, where an attribute is composed of two data elements,
a different separator (:) is used between them. For example, a colon will appear
between the syntax identifier and the syntax version number in the syntax
identifier group of the UNB segment.

Each record represents an EDIFACT segment and is terminated by an apostrophe (')
and a linefeed character (decimal 010).

Tags
^^^^

Where a four-digit numeric TAG (as defined under UNTDED) is shown, this has been
used to aid comprehension of the data. Where no TAG appears, there is no UNTDED
definition of the element. These codes will not exist in the TARIC 3 database.
The intention is to hold them in the TARIC 3 Data Dictionary System, which will
be used for the maintenance of the TARIC 3 Interface Data Specification.

Character set
^^^^^^^^^^^^^

The TARIC3 IDS uses the multi-byte Unicode character set in order to allow the
support of the descriptions in the languages of the candidate Member States.

Physically, each character is mapped onto one or more bytes according to the
encoding chosen. A number of encodings exist for Unicode. The TARIC3 IDS uses
the variable-length encoding UTF-8. The "Unicode transformation format" (UTF)
encoding is an algorithmic mapping from every Unicode scalar value to a unique
byte sequence. Detailed information can be found on http://www.unicode.org. 
