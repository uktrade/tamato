@bdd
Feature: Edit Additional Codes

Background:
    Given a valid user named Carol
    And a valid user named David
    And Carol is in the policy group
    And additional code X000
    And there is a current workbasket

Scenario: Edit permission granted
    Given I am logged in as Carol
    When I edit additional code X000
    Then I see an edit form

Scenario: Edit permission denied
    Given I am logged in as David
    When I edit additional code X000
    Then I am not permitted to edit
