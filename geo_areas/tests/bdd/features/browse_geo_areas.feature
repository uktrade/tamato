@bdd
Feature: Geographical areas


Background:
    Given a valid user named Alice
    And geographical_area 2222 with a description and area_code 0

Scenario Outline: Searching for a geographical_area
    Given I am logged in as Alice
    When I search for a geographical_area using a <search_term>
    Then the search result should contain the geographical_area searched for

    Examples:
    | search_term  |
    | 2222         |
    | This is 2222 |

Scenario Outline: Searching for a geographical_area that does not exist
    Given I am logged in as Alice
    When I search for a geographical_area using a <search_term>
    Then the search should return nothing

    Examples:
    | search_term                               |
    | Search term that shouldn't match anything |
