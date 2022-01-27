15. Make reverse relations aware of versions
============================================

Date: 2022-01-27


Status
------

Current


Context
-------

When tracked models exist in a one-to-many relationship (such as how one parent
object can have many descriptions) each description object will hold a foreign
key back to the parent object. The foreign key specifically links to the version
it was created against.

    Parent X (primary key = 1)
    Description X (primary key = 2, parent = 1)

Calling the reverse relation on the parent will correctly discover the
descriptions:

.. code-block:: python

    parent.descriptions
    # => [<Description: pk=2>]

If that parent object is updated, it receives a new row in the database, but the
descriptions are not updated and so the primary key they point to is still the
one of the old version.

This means that the reverse relationship when called on the new version will not
return any objects, because the reverse relationship by default tries to find
descriptions that have the primary key of the *new* parent object:

.. code-block:: python

    parent_v2 = parent.new_version(...)
    parent_v2.descriptions # => []

This is problematic because it means writing code that works correctly in the
presence of versions is not easy and bugs caused are not obvious – developers
currently need to remember that this does not work. This also makes the codebase
less intuitive to developers familiar with Django.


Decision
--------

The way that reverse relations are calculated will be modified to search using
version groups instead of primary keys. The version group of an object by
definition stays constant between versions.

The effect of this modification will be to change the query used by the reverse
relation to instead be equivalent to:

.. code-block:: python

    Description.objects.filter(parent__version_group=parent_v2.version_group)


Consequences
------------

With this change, reverse relations will start to work in the familiar way. Any
version of any object will correctly return related objects, even if the related
objects were created against an earlier version. There are no cases we have
discovered that won't work under this change.

Note that the result will still include all versions of any attached related
objects, and so the call still needs to be scoped down to a specific version.

.. code-block:: python

    current_descriptions = parent_v2.descriptions.latest_approved()

A future modification may be to apply automatic version filtering as described
in ADR #14 to reverse relations too, but the conseuqnces of this are slightly
harder to unpick and so are left as to-do.
