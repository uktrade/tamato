@bdd
Feature: Footnotes
    Notes on commodities or measures


Background:
    Given a valid user named "Alice"
    And footnote NC000


Scenario: View footnote core data
    Given I am logged in as Alice
    When I select footnote NC000
    Then a summary of the core information should be presented


Scenario: View footnote descriptions data
    Given I am logged in as Alice
    When I select footnote NC000
    Then the descriptions against the footnote should be presented
