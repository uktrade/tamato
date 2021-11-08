.. _contributing:

How to contribute
#################

All efforts to contribute to this project are welcome and encouraged.

If you would like to contribute, there are principally two ways you can help.

Raising issues
==============

If we don't know there is a problem, we can't help fix it.

Please feel free to raise issues if you can't get something to work, find a bug, or you
have any ideas for improvements.

Try and be as specific as possible, ideally you should include steps to re-produce your
issue if it's a bug, or some sort of rationale for new features.

Code
====

We will always try to accept code submissions. If you'd like to discuss a change before
you make it, please raise an issue and describe the work you're planning to do.

If you would like to improve the project by contributing code, please fork the repo,
make your change and submit a pull request.


Formatting
----------

This project uses the `pre-commit <https://pre-commit.com/>`__ tool to run `black
<https://github.com/psf/black>`__ as an autoformatter and `isort
<https://github.com/PyCQA/isort>`__ to format imports.

By pip-installing ``requirements-dev.txt`` you will have the ``pre-commit``
package installed, so you should now set up your pre-commit hooks:

.. code:: sh

    $ pre-commit install


Style
-----

* Make sure your code uses intent-revealing variable, function and class names
* Prefer simple self-evident code to complex code that requires comments
* Always leave the code in a better state than you found it

Tests
-----

* Include unit, functional, e2e and compatibility tests (when applicable)
* Make sure CI build passes consistently without any flaky tests


Commits
-------

* The first line of a commit message should complete the sentence "Merging this commit
  will ...", eg: "Add debug logging to the importer"

Pull Requests
-------------

* Make sure your PR is atomic and doesn't solve multiple problems at the same time
* Keep your PR small and deployable - each PR **must** leave the main branch in a
  releasable state
* Use feature flags if your PR cannot be deployed to production at any time after being
  merged
* Use GitHub labels if your PR is blocked or depends on another
* Use a `draft PR`_ for WIP or if you want initial feedback

.. _`draft PR`: https://github.blog/2019-02-14-introducing-draft-pull-requests/

Description
~~~~~~~~~~~

* Document what the PR does and why the change is needed - use the `PR template`_
* Give full context - not everyone has access to Jira/Trello
* Detail anything that is out of scope and will be covered by future PRs
* Include details on the lifecycle of the feature and its nature. Is it a new feature or
  a change to an existing one? Is the code going to be short-lived? Is it part of a
  bigger piece of work?
* Highlight possible controversies
* Include instructions on how to test (e.g. what should I see?)
* Detail any considerations when releasing

.. _`PR template`: ../.github/pull_request_template.md

Screenshots
~~~~~~~~~~~

* Add before / after screenshots or GIFs

When your PR is approved
~~~~~~~~~~~~~~~~~~~~~~~~

* Rebase before merging to keep the history clean
* Squash commits


Code review
===========

For both authors and reviewers
------------------------------

Please refer to the :doc:`Code of conduct <CODE_OF_CONDUCT>`.

Attitude
~~~~~~~~

* Remember that you are starting a conversation
* Don't take feedback personally
* Be honest, but don't be rude

GitHub
~~~~~~

* Non-trivial questions and issues are best discussed via Slack/Teams or face-to-face
* The same applies to PRs with large number of comments
* At the end of a conversation, update GitHub with a summary

If you are the author
---------------------

* Don't dismiss change requests except in rare circumstances (e.g. when the reviewer is
  on holiday), document the reason
* Respond to comments if you don't agree with them
* If you decide not to implement the suggestion, come to a mutual understanding with the
  reviewer

If you are a reviewer
---------------------

Time
~~~~

* Whenever possible, review a PR in one go so that the author understands the amount of
  work needed and can plan with his/her team

Architectural feedback
~~~~~~~~~~~~~~~~~~~~~~

* Focus on big architectural issues or problems with overall design first. If you spot
  any, give your feedback immediately before continuing with the review
* Check out the branch and run it locally for a broader view as GitHub tends to focus on
  single lines

Language
~~~~~~~~

* Offer suggestions - "It might be easier to...", "Consider..."
* Be objective - "this method is missing a docstring" instead of "you forgot to write a
  docstring"

Being diplomatic
~~~~~~~~~~~~~~~~

* Feel free to constructively challenge approaches and solutions, even when coming from
  a seasoned developer
* It's OK to nit-pick on syntax issues, spelling errors, poor variable/function names,
  missing corner cases
* But don't be a perfectionist - allow some flexibility

Levels of importance
~~~~~~~~~~~~~~~~~~~~

* Prefix non-critical comments with (eg) *Non-critical:* so that the author knows what is
  important and what is not
* If all your comments are non-critical, leave your feedback but accept the PR at the
  same time so that you are not a blocker and you keep a positive attitude
