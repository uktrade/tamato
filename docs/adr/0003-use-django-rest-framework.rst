.. _3-use-django-rest-framework:

3. Use Django REST Framework
============================

Date: 2020-04-24

Status
------

Proposed

Context
-------

We want to build a RESTful API to allow users to easily consume our
data.

We are already building the project with Django.

The dev team are already familiar with Django REST Framework (DRF).

DRF is much more popular (and by implication, better supported and
documented) than the closest alternative, TastyPie.

Decision
--------

Use Django REST Framework to simplify resource representation, request
routing, API versioning, etc

Consequences
------------

DRF saves writing (and thinking about) large amounts of boilerplate code
to implement RESTful APIs