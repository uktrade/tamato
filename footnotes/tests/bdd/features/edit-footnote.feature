@bdd
Feature: Edit Footnote

Background:
    Given a valid user named Bob
    And Bob is in the policy group
    And footnote NC000
    And there is a current workbasket


Scenario: Edit permission granted
    Given I am logged in as Bob
    When I edit footnote NC000
    Then I see an edit form


Scenario: Setting end date before start date errors
    Given I am logged in as Bob
    When I set the end date before the start date on footnote NC000
    Then I see the form error message "The end date must be the same as or after the start date."


Scenario: Violate business rule
    Given I am logged in as Bob
    When I set the start date of footnote NC000 to predate the footnote type
    Then I see the form error message "The validity period of the footnote type must span the validity period of the footnote."
