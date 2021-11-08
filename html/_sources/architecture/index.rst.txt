Architecture
============

This page describes the high-level architecture of TaMaTo. If you want to
familiarize yourself with the code base, you are in just the right place!

Bird's Eye View
---------------

.. image:: birds-eye.svg

TaMaTo is a data storage and management system that acts as the single source of
truth for the UK customs tariff. Its role is to represent trade policy as
designed by HM Government's policy teams in the data domain and transmit this
downstream to border systems and other third-party users. It takes data in
various formats, validates it, and outputs it in various other formats.

The general principle for UK tariff data is to have border services working from
this single source of tariff data as much as possible. This avoids border
service delivery teams from having to manually interpret complex tariff policy
and configure their services accordingly. In general, we are trying to maximise
data flow from the source in policy to use at the border.

Policy teams forming trade policy have a number of levers to use in achieving
their aims. New or updated policies will change the tariff rates and controls
that are applied, and these changes then need to be reflected in the UK tariff
stored in TaMaTo. The main "format" used to do this is the user interface being
operated by a domain-aware tariff operations manager, who interprets and applies
the policy on behalf of all downstream consumers. Future work will consider more
input interfaces, such as the ability of policy teams to control the data
directly.

HMRC's Customs Declaration Services (CDS) system is a primary consumer of data
from TaMaTo. There are also a number of other consumers: the Jersey and Guernsey
border systems Caesar and GEMS, policy-makers via DIT's Data Workspace and other
third parties via open data.

Concepts
--------

TARIC
^^^^^

Most UK border systems were previously designed to take customs tariff updates
from the European Union. For this reason the tariff domain model and output
interfaces match those still used by the EU. This standard is called TARIC
(TARif Intégré Communautaire, or Integrated Tariff of the European Communities).

TARIC is a data exchange specification – the models, fields and formats that are
used to communicate the tariff are thus pre-specified and are difficult to
change. Primarily an XML format is used which follows a TARIC XSD.

TARIC was designed to communicate *changes* about the tariff – hence there are a
number of features that exist specifically to do this. Most notably, the TARIC
specification models the tariff as an ever changing *transaction stream* where
each transaction represents a change to a model to be applied.

The streaming nature means that the entire state of the system is decided by the
sum total of all of the transactions that have currently been applied – any
future transactions are not yet visible. This has an architectural implication
that TaMaTo must be able to read data and apply business rules as of a certain
transaction as opposed to just considering all data that is present (including
e.g. draft data). More detail on what practical difference this makes is in the
documentation on :ref:`12-ordering-of-tariff-transactions`.

Validity dates as version control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The domain model implements a version control system that specifies which models
of the tariff are live on the border on a given day. This allows a tariff update
to be sent to border systems in advance and take effect correctly at some future
time. Most models use a pair of validity dates, implemented using the
:class:`~common.models.mixins.validity.ValidityMixin`.

Description models have a requirement that there must always be one live
description at any time. For this reason, descriptions do not have end dates and
only have start dates. The description is live up until the start date of the
next description record. This is implemented using the
:class:`~common.models.mixins.validity.ValidityStartMixin`.

Tracked models as version control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The TARIC data exchange communicates about models in terms of what changes are
being made to them. Hence, it is not enough for a TARIC-aware system to just
have the latest data applied and stored – the system must also keep track of
previous versions of models and be able to describe the changes that have been
done to them.

Each model will exist multiple times in the database, with each row representing
a new version of that model. This is implemented using the
:class:`~common.models.records.TrackedModel` system.

Note that which version of a model is the "current" one depends in general on
what transactions have been applied. Each row is pinned to a specific
transaction in order to allow working out which model is the current version as
of a certain transaction. As TaMaTo will also deal with draft data, what is
"current" is somewhat dependent on what draft data is being considered.

In general, the system will consider any version that has been "approved" to be
eligible to be "current", such that the version from the most recent transaction
that is not draft is considered to be "current".

There are a number of convenience methods for finding "current" models.

.. autoclass:: common.models.records.TrackedModelQuerySet
  :members: latest_approved, approved_up_to_transaction

Domain Modules
--------------

The tariffs domain model is implemented across a number of **domain modules**,
each itself a Django App. Each module is responsible for one family of tariff
objects.

:mod:`measures`
^^^^^^^^^^^^^^^
.. automodule:: measures

:mod:`commodities`
^^^^^^^^^^^^^^^^^^
.. automodule:: commodities

:mod:`additional_codes`
^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: additional_codes

:mod:`quotas`
^^^^^^^^^^^^^
.. automodule:: quotas

:mod:`certificates`
^^^^^^^^^^^^^^^^^^^
.. automodule:: certificates

:mod:`geo_areas`
^^^^^^^^^^^^^^^^
.. automodule:: geo_areas

:mod:`regulations`
^^^^^^^^^^^^^^^^^^
.. automodule:: regulations

:mod:`footnotes`
^^^^^^^^^^^^^^^^
.. automodule:: footnotes


Inside Domain Modules
---------------------

Each domain module has a similar layout, some of which is inherited from the
Django system. Inside each domain module, you might expect to see the following,
either as modules themselves or single files.

``models``
^^^^^^^^^^

Classes representing domain models. With again a few exceptions, most models
correspond directly to an element in the TARIC specification. Most of these will
inherit from :class:`~common.models.records.TrackedModel` which represents a
model for whom history is being tracked.

(The main exception is
:class:`~commodities.models.GoodsNomenclatureIndentNode` which is really just a
cache of the commodity code tree stored in the database and is not updated
independently of related models.)

The most notable places where the database schema has diverged from the TARIC
specification is on descriptions, which have been flattened into a single model
that represents both the description and the description period on the
assumption that we will only support English as a language, and for
:mod:`regulations`, where the UK legislative model is considerably simpler than
its European counterpart.

``business_rules``
^^^^^^^^^^^^^^^^^^

Classes that implement business logic checking on models. Most of the business
rules are defined by the TARIC specification. There are also some places where
new business rules have been written either based on observation of how
downstream systems react to certain situations or through a desire to more
tightly control the function of the system.

Business rules from the TARIC specification are named for the business rule code
used in that spec (e.g. :class:`~measures.business_rules.ME32`) and business
rules that have been added to the system are given descriptive names. Each
business rule has a docstring that describes the rule.

``patterns``
^^^^^^^^^^^^

Objects that implement an operation on the data taking into account the
high-level domain logic around how the tariff actually works. These are
responsible for providing a simple interface to create data that will pass the
more complex business rules around relationships between models and for encoding
how certain situations are handled.

For example, "origin quotas" are a special kind of quota that require a proof of
origin certificate, and the :class:`~measures.patterns.MeasureCreationPattern`
has a specific argument to its
:meth:`~measures.patterns.MeasureCreationPattern.create` method that will set up
the measure conditions correctly to handle this use case. There is nothing in
the business rules that specifies how origin quotas should be handled (and hence
it may change in the future), but at the moment they are always implemented in a
specific way and the pattern encodes that implementation.

So where the tariff works a certain way as the result of a business decision as
opposed to a constraint in the data, that decision should be implemented as a
pattern.

``serializers``
^^^^^^^^^^^^^^^

Classes that implement serialization logic. Most are derived from Django REST
Framework's serializer base class. The serializers are mostly used to output
TARIC3 XML and for this they rely on XML templates written in the Jinja2
templating language.

``import_parsers`` and ``import_handlers``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These are classes that extract data from TARIC XML and process that data into
complete models with all linked dependencies respectively.

See the documentation on :ref:`the importer <the-importer>` for a full
description.

``validators``
^^^^^^^^^^^^^^

Classes that implement model-specific validation routines. These mostly
implement rules around the correct formatting of data (e.g. if the code of a
model has the correct number of digits) compared to the business rules which
check correctness of fields and relationships between models.

``querysets``
^^^^^^^^^^^^^

Implementations of custom Django QuerySet classes that represent complex
database queries. In some places it is desirable to more tightly control how the
system fetches it's data – for example, to efficiently generate a new field using
aggregates.

The :class:`~common.models.records.TrackedModelQuerySet` is one of the most used
as it implements selecting the correct versions from the version control system.

``parsers``
^^^^^^^^^^^

Classes that implement custom parsers for use in translating from simple strings
in the user interface or spreadsheets into model objects (or sets of them).
These do not generally follow a specific implementation pattern.

``filters``
^^^^^^^^^^^

Django-style filter objects used by the search interfaces.

``views``
^^^^^^^^^

Django-style view objects used by the user interface.


Cross-Cutting Modules
---------------------

As well as domain modules, there are also a number of modules that provide
cross-cutting concerns to the rest of the system.

:mod:`importer`
^^^^^^^^^^^^^^^
.. automodule:: importer

:mod:`exporter`
^^^^^^^^^^^^^^^
.. automodule:: exporter

See the documentation on :ref:`the exporter <the-exporter>` for a full
description.


:mod:`hmrc_sdes`
^^^^^^^^^^^^^^^^
.. automodule:: hmrc_sdes

:mod:`taric`
^^^^^^^^^^^^
.. automodule:: taric
