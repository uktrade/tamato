Feature: Edit Footnote

Background:
    Given a valid user named "Alice"
    And Alice has permission to update a footnote
    And footnote NC000
    And a current workbasket


Scenario: View Footnote edit screen
    Given I am logged in as Alice
    When I go to edit footnote NC000
    Then I should be presented with a form with an <enabled> <field> field

    Examples:
    | field | enabled |
    | id_footnote_type | disabled |
    | id_footnote_id | disabled |
    | id_valid_between_0 | enabled |
    | id_valid_between_1 | enabled |


Scenario: Update Footnote
    Given I am logged in as Alice
    When I submit a <change> to footnote NC000
    Then I should be presented with a footnote update screen

    Examples:
    | change     |
    | start date |
    | end date   |
