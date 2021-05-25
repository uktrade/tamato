@bdd
Feature: Edit Certificates

Background:
    Given a valid user named Carol
    And a valid user named David
    And Carol is in the policy group
    And certificate X000
    And there is a current workbasket

Scenario: Edit permission granted
    Given I am logged in as Carol
    When I edit certificate X000
    Then I see an edit form

Scenario: Edit permission denied
    Given I am logged in as David
    When I edit certificate X000
    Then I am not permitted to edit

Scenario: Setting end date before start date errors
    Given I am logged in as Carol
    When I set the end date before the start date on certificate X000
    Then I see the form error message "The end date must be the same as or after the start date."
