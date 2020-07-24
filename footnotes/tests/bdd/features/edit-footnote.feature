Feature: Edit Footnote

Background:
    Given a valid user named "Alice"
    And Alice has permission to update a footnote
    And footnote NC000


Scenario: View Footnote edit screen
    Given I am logged in as Alice
    When I go to edit footnote NC000
    Then I should be presented with a form with the following fields
        Footnote type
        Footnote ID
        Footnote start date
        Footnote end date
    And only the start and end date should be editable


Scenario: Update Footnote
    Given I am logged in as Alice
    When I submit a <change> to footnote NC000
    Then I should be presented with a footnote update screen

    Examples:
    | change     |
    | start date |
    | end date   |
