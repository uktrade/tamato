Feature: Geographical areas


Background:
    Given a valid user named "Alice"
    And geographical_area 1001 with a lorem ipsum description

Scenario Outline: Searching for a geographical_area
    Given I am logged in as Alice
    When I search for a geographical_area using a <search_term>
    Then the search result should contain the geographical_area searched for

    Examples:
    | search_term |
    | 1001        |
    | ipsum       |
