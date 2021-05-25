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

Scenario: Setting end date before start date errors
    Given I am logged in as Carol
    When I set the end date before the start date on additional code X000
    Then I see the form error message "The end date must be the same as or after the start date."

Scenario: Violate business rule
    Given I am logged in as Carol
    And a previous additional code X000
    When I set the start date of additional code X000 to overlap the previous additional code
    Then I see the form error message "The validity period of the additional code must not overlap any other additional code with the same additional code type, additional code ID and start date."
