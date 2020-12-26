@bdd
Feature: Footnotes
    Notes on commodities or measures


Background:
    Given a valid user named "Alice"
    And footnote NC000


Scenario: Searching by footnote ID
    Given I am logged in as Alice
    When I search for a footnote using a footnote ID
    Then the search result should contain the footnote searched for
