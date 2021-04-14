Feature: Edit Permissions

Background:
    Given a valid user named Carol
    And a valid user named David
    And Carol is in the policy group
    And a model exists
    And there is a current workbasket

Scenario: Edit permission granted
    Given I am logged in as Carol
    When I edit a model
    Then I see an edit form

Scenario: Edit permission denied
    Given I am logged in as David
    When I edit a model
    Then I am not permitted to edit
