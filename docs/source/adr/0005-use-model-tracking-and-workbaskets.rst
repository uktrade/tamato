.. _5-use-tracked-models-and-workbaskets:

5. Use tracked models and workbaskets
=====================================

Date: 2020-05-21

Status
------

Approved

Context
-------

The Tariff Management Tool (TAMATO) requires a system to trial and
approve changes which, once accepted, can be tracked as a series of
changes from any previous state. This is currently termed as
“workbaskets” in the current application.

This can be split into four parts:

1. Drafting and viewing proposed changes
2. Approving changes
3. Applying changes
4. Auditing changes

This ADR is primarily concerned with the data model underlying this
system and not the application of the system.

Decision
--------

The proposed data model would involve two models, a ``WorkBasket`` model
and a ``TrackedModel`` like so (column names subject to ORM standards):

WorkBasket
~~~~~~~~~~

+---------------+-------------------------+-------------------------+
| Column        | Type                    | Description             |
+===============+=========================+=========================+
| ID            | Positive Integer (NOT   | Primary Key             |
|               | NULL) (PK)              |                         |
+---------------+-------------------------+-------------------------+
| TransactionID | FK (UNIQUE)             | links to the            |
|               |                         | Transaction ID given to |
|               |                         | HMRC when uploading     |
|               |                         | TARIC3 XML              |
+---------------+-------------------------+-------------------------+
| User          | FK (User) (NOT NULL)    | the person making and   |
|               |                         | editing the WorkBasket  |
+---------------+-------------------------+-------------------------+
| Approver      | FK (User)               | the person who approves |
|               |                         | the WorkBasket.         |
+---------------+-------------------------+-------------------------+
| State         | CharField (NOT NULL)    | Holds the position of   |
|               |                         | the WorkBasket in a     |
|               |                         | Finite State Machine    |
|               |                         | style system.           |
+---------------+-------------------------+-------------------------+
| Name          | CharField (UNIQUE) (NOT | A descriptive name for  |
|               | NULL)                   | the WorkBasket          |
+---------------+-------------------------+-------------------------+
| Reason        | Description (NOT NULL)  | Furthers the name.      |
+---------------+-------------------------+-------------------------+
| Created At    | Date Time Field (NOT    | When the workbasket was |
|               | NULL)                   | created.                |
+---------------+-------------------------+-------------------------+
| Updated At    | Date Time Field (NOT    | when changes were last  |
|               | NULL)                   | made.                   |
+---------------+-------------------------+-------------------------+

TrackedModel
~~~~~~~~~~~~

+-------------+--------------------------+--------------------------+
| Column      | Type                     | Description              |
+=============+==========================+==========================+
| ID          | Positive Integer (NOT    | Primary Key              |
|             | NULL) (PK)               |                          |
+-------------+--------------------------+--------------------------+
| WorkBasket  | FK (WorkBasket) (NOT     | Links to the WorkBasket  |
|             | NULL)                    | which created the        |
|             |                          | object.                  |
+-------------+--------------------------+--------------------------+
| Draft       | Boolean                  | If the Object is still   |
|             |                          | in draft (i.e. the       |
|             |                          | WorkBasket hasn’t been   |
|             |                          | approved yet) or if it   |
|             |                          | has been applied and     |
|             |                          | sent to HMRC.            |
+-------------+--------------------------+--------------------------+
| Predecessor | FK (TrackedModel)        | Links to the previous    |
|             |                          | version of this object.  |
+-------------+--------------------------+--------------------------+
| Update Type | Choice (Update, Create,  | Specifies whether this   |
|             | Delete)                  | represents a new version |
|             |                          | of an existing item, a   |
|             |                          | new item, or is the      |
|             |                          | deletion of an existing  |
|             |                          | item.                    |
+-------------+--------------------------+--------------------------+

Each object table that implements the TrackedModel pattern has a FK to
the ``TrackedModel`` table.

Reasoning
---------

WorkBaskets
~~~~~~~~~~~

Most of the WorkBasket model is self-explanatory.

WorkBaskets must be reviewed before being applied. As a result two FKs
to the ``User`` table are required, one for the creator and another for
the approver. A lack of approval would act as a blocker, stopping the
workbasket from being submitted to CDS, therefore serving as an inherent
rejection of the WorkBasket. Once approved all attached
``TrackedModel``\ s should be considered live and immutable and a TARIC3
file sent to HMRC.

Transaction IDs have some complexity as they are interdependent on how
HMRC will handle TARIC3 submissions. However the idea is that once a
WorkBasket is approved the Transaction ID will need to be generated as a
unique sequential identifier. This is how HMRC will identify the TARIC3
submission - and how TaMaTo will identify which errors are relevant to
this WorkBasket. There may be some complexity around whether HMRC
rejects the Transaction itself.

The process of creating, reviewing, approving, submitting and validating
a WorkBasket reflects a Finite-state machine. As a result a status
attribute allows us to track where the WorkBasket is within the machine
and add transitions from one state to another based on events within the
system.

.. _trackedmodel-1:

TrackedModel
~~~~~~~~~~~~

The TrackedModel holds some intermediate data on the object being
introduced, such as the update type applied to the object, however its
main purpose is to act as a through table for the WorkBasket to the
object. For this purpose the TrackedModel holds a key to the WorkBasket,
but also a GenericForeignKey to the object being changed. This generally
consists of a key field for the objects ID and a content type field to
identify the actual table being linked to. This way the WorkBasket can
stay naïve to the multiple tables it is affecting and let the
TrackedModel table handle the generic relations.

The TrackedModel holds some intermediate data on the object being
introduced, such as whether the relevant object is still being drafted
or not, however its main purpose is to act as a through table for the
WorkBasket to the object. For this purpose the TrackedModel holds a key
to the WorkBasket, but also a GenericForeignKey to the object being
changed. This generally consists of a key field for the objects ID and a
content type field to identify the actual table being linked to. This
way the WorkBasket can stay naïve to the multiple tables it is affecting
and let the TrackedModel table handle the generic relations.

Consequences
------------

The consequences of this decision are significant, as WorkBaskets
underpin the majority of the app's purpose. However there are a number
of advantages to this approach.

1. As data models WorkBaskets will be very light and easy to manage in
   code.
2. When approved and applying changes the only necessary step is to flip
   a Boolean on the relevant models - other implementations would
   generally involve a custom system for running the changes and
   maintaining data integrity during this process.
3. The TrackedModel can be done using concrete inheritance and a
   polymorphic data model for which there are libraries already - in
   terms of code it is quite clean.
4. By keeping the draft data in their tables all the validations that
   are applied to those tables can also apply.
5. Viewing the draft changes is as simple as querying for the object in
   it’s table, as opposed to having to mock up the data for it based on
   the changes.

There are however a few limitations:

1. Queries for all WorkBasket data are at a minimum n+1, there is 1
   query to get all WorkBasket and all connected TrackedModels, but
   another n queries for each other table the TrackedModels connect to.
   With this in mind the number of tables that will be possible to link
   to should not be massive.
2. This method only allows editing objects by row, which increases the
   chances of merge conflicts. Other methods would allow editing each
   individual column which would lower this risk.
