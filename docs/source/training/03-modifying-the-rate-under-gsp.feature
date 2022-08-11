Feature: 3. Modifying the rate under GSP

    The Generalised System of Preferences (GSP) is a tariff regime that gives
    favourable access to developing countries. It is an example of a
    “preferential regime”, i.e. a mechanism by which tariff rates are lowered
    for certain countries in certain circumstances.

    GSP is a “unilateral” regime, meaning that the United Kingdom gives
    preferential access without expectation of anything in return. This is in
    contrast to a “bilateral” regime, in which preferential treatment is applied
    to both sides. Read more about `unilateral preferences`_.

    The Most Favoured Nation and suspension measures that were created in
    earlier scenarios applies to all countries. Handling a preference is similar
    but also requires specifying the geographical area that the preference
    applies to.

    A “geographical area” can be a country, region, trading bloc or other group.
    There is no technical difference between a country or a region – it just
    reflects the United Kingdom's official view that certain areas are not
    recognised as soverign countries.

    Groups can contain multiple countries or regions and allow specifying
    measures or quotas that should apply to the whole group. Membership of a
    group is controlled by a set of dates that specify for what periods a
    country or region is a member. Read more about `geographical areas`_.

    .. _`unilateral preferences`: https://uktrade.github.io/tariff-data-manual/documentation/trade-policies/unilateral-preferences.html
    .. _`geographical areas`: https://uktrade.github.io/tariff-data-manual/documentation/data-structures/geographical-areas.html

    @ui
    Scenario: Updating an existing GSP measure using the Tariff Editor

        In this scenario, you will modify the dates on an existing GSP measure to
        correct an error. You will first need to find the correct measure and
        edit it to correct the dates.

        The update is an error correction meaning that the existing measure does
        not correctly represent the policy that has been legislated for. The
        correct tool to use to make this update is therefore the “Edit measure”
        screen.

        Given I am on the training environment
        And there is a GSP measure

        When I visit the home page
        And I select "Find and edit measures"
        Then I am taken to the next page

        When I select "142 – Tariff preference" as the type
        And I select "2020 – GSP – General Framework" as the geographical area
        And I press "Search and Filter"
        Then at least 1 search result appears

        When I press on the 1st search result
        Then I see a measure screen

        When I press "Edit this measure"
        Then I see an edit measure details screen

        When I expand the Measure validity period area
        And I select today as the start date
        And I select tomorrow as the end date
        And I press "Save"
        Then I see the confirmation message

    @notebook
    Scenario: Updating an existing GSP measure using a Jupyter notebook

        Note here that we do an update to an existing object using the
        ``new_version`` call, as opposed to just modifying the attributes and
        calling ``save``. The existing version isn't modified and the change
        will get included in any updates sent out of the system.

        Given a migration notebook
        And a Measure with parameters:
            | argument                       | value                                                            |
            | measure_type                   | MeasureType.current_objects.get(description="Tariff preference") |
            | geographical_area__area_id     | "2020"                                                           |
            | geographical_area__description | "GSP – General Framework"                                        |
        When I get a Measure m with parameters:
            | argument                   | value               |
            | measure_type__description  | "Tariff preference" |
            | geographical_area__area_id | "2020"              |
            | valid_between__contains    | date.today()        |
        And I create a new version of m with parameters:
            | argument      | value                                               |
            | valid_between | TaricDateRange(m.valid_between.lower, date.today()) |
        And I validate the workbasket
        Then I get no errors
