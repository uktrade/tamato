.. _2-use-pytest-bdd-for-bdd-testing:

2. Use pytest-bdd for BDD testing
=================================

Date: 2020-04-21

Status
------

Accepted

Context
-------

We want to write tests to prove that the TAMATO app functions
equivalently to the old TAP project that it replaces.

We have a large amount of pre-existing documentation of functional
requirements in the form of test scenarios and data.

We have already chosen pytest as our testing framework, due to the
development team's familarity with it.

Decision
--------

Acceptance criteria for user stories will be written in Gherkin format
(Given-When-Then).

We will write tests that interpret these criteria using pytest-bdd.

Test result reports will be automatically generated and published
somewhere stakeholders can view them.

Consequences
------------

Collaboration between business analysts and the development team will be
easier due to a shared use of Gherkin formatted feature specifications.

The development team can continue to use pytest and not have to learn a
new test framework or tool.

Stakeholders can see easy to understand reports on test results and
requirements coverage.