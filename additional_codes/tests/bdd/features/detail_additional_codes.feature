Feature: Additional Codes

Background:
    Given a valid user named "Alice"
    And additional code X000

Scenario: View additional code core data
    Given I am logged in as Alice
    When I select the additional code X000
    Then the core data against the additional code should be presented
