.. _16-content-checksums-for-tracked-models

16 Content checksums for Tracked Models
=======================================


Status
------

Proposed


Context
-------

After running the business rules it is useful to store the results of checks against models, and have a mechanism to check if the result is still valid to avoid re-running the check in future.

This ADR adds a mechanims to checksum the user-editable data to check if to versions of a Tracked Model are equivilent.

In the simplest sense this means hashing fields that exclude the PK.


TAP already has a mechanism to get the user editable fields, the attribute `.copyable_fields`, which provides a starting point.

Unlike pythons default hashing, it is nessacary to distinguish between two different types that produce the same hash - so the string that gets passed the hashing function ("hashable_string"), will include the module and class name.


The hash generated in this ADR will not currently be attached to TrackedModel - thought it may be desirable in future.
By limiting the scope to business rule checks this gives time for the code to bed in, and makes it easier to change things if there are issues.


Decision
--------

The fields to be hashed are contained in `copyable_fields` but since this doesn't communicate the intent used here, this will be proxied as `mutable_fields`, which is explicitly about providing which fields can be hashed to check equivilence.


TrackedModel will gain an API named get_content_hash() that returns a sha256 hash.

get_content_hash() -

Iterates the fields in `mutable_fields` and building a dict keyed by field name, the value contains the location __module__ and __name__ of the field.

If the field is not TrackedModel then the value includes the sha256 of their content, for foreign keys that are TrackedModels the value is obtained by calling get_content_hash()


Consequences
------------

This provides a mechanism to store the results of business rule checks, only becomming invalid when the TrackedModels they reference change.

When a workbasket is published, the validity of all other unpublished workbaskets must be verified - with this system, most of the business rule checks would remain valid and the only the checksums need to be verified.

