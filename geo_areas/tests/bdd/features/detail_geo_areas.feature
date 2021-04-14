@bdd @xfail
Feature: Geographical areas


Background:
    Given a valid user named Alice
    And geographical_area 1001 with a description and area_code 0
    And geographical_area 1002 with a description and area_code 1

Scenario: Viewing a geographical_areas core data
    Given I am logged in as Alice
    When I view a geographical_area with id 1001
    Then the core data of the geographical_area should be presented

Scenario: Viewing a geographical_areas description data
    Given I am logged in as Alice
    When I view a geographical_area with id 1001
    Then the descriptions against the geographical_area should be presented

Scenario: Viewing a geographical_areas membership data
    Given I am logged in as Alice
    When I view a geographical_area with id 1001
    Then the memberships against the geographical_area should be presented

Scenario: Viewing a geographical_areas groups membership data
    Given I am logged in as Alice
    When I view a geographical_area with id 1002
    Then the members against the geographical_area should be presented

