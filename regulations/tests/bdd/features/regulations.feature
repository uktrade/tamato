Feature: Regulations
    Legal Acts which generate measures or affect applicability of existing regulations

Background:
    Given a valid user named "Alice"
    And some regulations
    And regulation C2000000

Scenario: Searching by Regulation Number
    Given I am logged in as Alice
    When I search for a regulation using a valid Regulation Number
    Then the search result should contain the regulation searched for
