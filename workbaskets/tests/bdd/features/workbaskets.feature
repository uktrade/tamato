Feature: Workbaskets
    Groups of changes to the tariff to be applied in one go


Background:
    Given a valid user named "Alice"


Scenario: No work in progress
    Given I am logged in as Alice
    When I view the main menu
    Then I see a notification that I have no current workbaskets


Scenario: Work in progress
    Given I am logged in as Alice
    And I have a current workbasket
    When I view the main menu
    Then I see a list of my current workbaskets
