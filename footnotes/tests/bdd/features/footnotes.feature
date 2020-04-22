Feature: Footnotes
    Notes on commodities or measures

Scenario: Browsing footnotes
    Given some footnotes exist
    When I go to the footnotes page
    Then I should see a list of footnotes
