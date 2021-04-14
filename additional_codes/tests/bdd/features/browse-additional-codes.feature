@bdd
Feature: Additional Codes

Background:
    Given a valid user named Alice
    And additional code X000

Scenario: Searching by additional code
    Given I am logged in as Alice
    When I search additional codes with a <search_term>
    Then the search result should contain the additional code searched for

    Examples:
    | search_term |
    | X000 |
