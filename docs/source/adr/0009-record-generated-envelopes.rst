.. _9-generate_envelope_files:

9. Generate envelope files
==========================

Date: 2020-10-14

Status
------

Proposed

Context
-------
We must geneate XML envelope files as a way of communicating tariff data to HMRC
and our other consumers. The spec for envelope files is defined as an XSD
schema. An envelope file contains multiple transactions.

The way in which database models are packed into transactions is partly defined
by the TARIC spec. HMRC systems place additional requirements on the
transactions that are still partially undefined.

We have known since the beginning that CDS would accept or reject changes sent
from TaMaTo. We have also had some notion that this happens in two stages with
different validations applied at each stage. The first stage will reject an
entire envelope if it contains erroneous data. The second stage will only reject
specific transactions. It was, until recently, unknown what CDS expects as
replacement data in either of these failure modes.

We have since learnt more about interacting with the CDS system and the use of
TARIC3 XML. Particularly around the metadata associated with the interface in
the form of a gateway API call, envelopes, transactions and messages. This has
come from a better understanding of the new HMRC design and through further
review of the pre-existing Trade Tariff Management (TTM) codebase.

The envelope, transaction or message ID are always set automatically in TTM and
can't be manually controlled. The envelope ID is set based on the current date
and a sequence number. The transaction and message IDs are both set sequentially
on a per-envelope basis. When a validation error occurs at CDS a new envelope ID
is used.

HTTPS interface
~~~~~~~~~~~~~~~

HTTPS clients already expect TARIC3 XML over an HTTPS API. The existing HTTPS
API in TTM provides TARIC3 XML envelopes and metadata about them including the
envelope ID. There may be little to substantially change about this API – it
returns a list of envelopes generated per day.

There is no limit on the size of returned envelopes and there is no limit on the
number of envelopes generated in one day.

HMRC interface
~~~~~~~~~~~~~~

According to HMRC envelope and transaction IDs affect the sequence numbers used
by CDS for processing. TaMaTo should use the same envelope ID when an envelope
is rejected. Transaction IDs should also be reused when individual transactions
are errored. It is possible in the past that data that errored in CDS was
corrected manually. As we are using a new API pattern from HMRC it may be more
difficult to correct things manually.

Metadata submitted to HMRC must include a checksum and file size. The filename
should match the envelope ID.

The files transferred have a maximum file size. Rather than trying to ensure
workbaskets don't get too large it may better for a large transaction to be
split across multiple envelopes. The transactions in the envelopes will require
different and subsequent transaction IDs.

The HMRC interface can support multiple envelope files transferred in one day
but it is unknown if there is a limit. This means that it may be discovered in
the future that we need to pack multiple transactions into a single envelope.

This essentially means that a "workbasket" does not correspond to any specific
element in HMRC XML – it could be formed from several transactions across
several envelopes.

Decision
--------

The concept of "workbasket", "transaction" and "envelope" will all be separated
and therefore tracked with separate sequence numbers.

Envelopes
~~~~~~~~~

The envelope ID is a numeric value that ends up as an attribute on the root
element of the envelope. It will be prepended with 'DIT' when used as the
filename of the envelope. E.g. an envelope with ID 200001 will be called
DIT200001.xml.

The pattern for envelope IDs will be `YYxxxx` where `YY` is the current year and
`xxxx` is a sequential envelope ID through this year. Every year the sequence
will be reset for the first envelope generated in the year, e.g
190001, 200001, 210001. This is the format agreed with HMRC. We may need to
reuse envelope IDs if we send data that contains errors and it is rejected.

An envelope must not end up larger than the maximum file size of 50Mb.

An envelope should not contain any empty transaction elements. Transaction
elements should not be split across envelopes. Transactions must appear ordered
in the file by their transaction ID.

Generating an envelope will be a function of one or more workbaskets and the
sequence numbers for envelopes and transactions. Envelope files should be
generated to wholly contain the passed workbaskets and this might require
multiple files, and hence multiple envelope IDs. An example signature of a
function to do this might be:

.. code:: python

    def generate_envelopes(
        envelope_counter: Callable[[], int],
        transaction_counter: Callable[[], int],
        *workbaskets: WorkBasket
    ):
      # TODO: code

Transactions
~~~~~~~~~~~~

Transactions should contain the minimum number of records required to represent
a "logical" database operation that passes all reqired validations. For most use
cases this means only one record will need to be contained.

In particular, in cases where we are replacing one model with another (like
end-dating a measure and creating a new one) we must always output the old model
in a previous transaction to a new one. It is not enough to ensure the business
rules are validated at the end of the transaction in the case of ME32 – they
must be valid after every model addition and are only validated against the view
of measures as per the start of the transaction.

Multiple records within a transaction should have the same record code and
differ only in their subrecord code.

Records in a transaction should be sorted by subrecord code. E.g. the record for
a new footnote description period (20005) should come before the record for the
new description (20010).

Examples:

-  Updating a measure end-date: only one measure record
-  Replacing a measure: one transaction containing the end-dating followed by
   one transaction containing the measure along with any components and
   conditions
-  Adding a footnote: three records, one for the new footnote, followed by one
   for the description period, followed by one for the description.

Consequences
------------

As the rules for forming transactions are complex, and partially dependent on
what has already been added to an envelope, it does not necessarily make sense
to keep track internally of what models have ended up in what transactions.
However, we still expect both transactions and envelopes to come back as
"ERRORED" from HMRC. It might make sense to retire our current table of
transactions and only use workbaskets for internal grouping purposes.

We could choose to deal with errors in an automated fashion and build a complex
system that maps model versions to the individual transactions that were put
into envelopes (taking into account that this is a many-to-many relationship).
Or we can record minimal information and handle error conditions as a special
case manually.

By keeping a record of envelopes we have sent and their metadata, we would:

-  Have a record of what was sent to HMRC, even in unhappy path cases where
   errors have occured
-  Stay flexible about what external envelope IDs we use, including reusing them
   or changing them if necessary
-  Have a way to quickly generate API responses without calling out to an
   existing file store, if we choose to cache generated files