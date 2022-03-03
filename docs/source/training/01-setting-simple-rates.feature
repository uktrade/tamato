Feature: 1. Setting simple rates

    The purpose of the UK Trade Tariff dataset is to specify policy measures
    that control trade. One of the main mechanisms for controlling trade is
    levying a duty that a trader must pay to import their goods into the United
    Kingdom.

    The most basic duty that policy defines is called the “third country duty”
    or alternatively “Most Favoured Nation” rate. This rate is paid by any
    trader that does not have access to a lower duty via a free trade agreement,
    suspension or quota.

    Each duty or control applied by the tariff is represented by a “measure”.
    Each measure defines what the duty or control is and what trades it applies
    to. For each Most Favoured Nation rate, there is a measure that defines the
    rate and the time period it applies for. Read more about `measures`_.

    The Most Favoured Nation rate is different for each kind of product. When a
    trader does an import or export, they must declare the kind of products they
    are trading. In order to efficiently specify policy, products are grouped
    together into a certain “classification”.

    For example, all live animals are classified together and so policy could
    specify rates or controls that apply to any live animal. There are also more
    specific classifications to cover, for example, live horses, pigs and
    poultry and so trade policy can target those more specific groups instead.

    Each classification is represented by a “commodity”, and traders declare
    which type of product they are importing using a “commodity code”. Each
    measure targets exactly one commodity code. Read more about
    `commodities`_.

    To set up a new Most Favoured Nation measure, you will need to know the new
    rate, the commodity code to apply it to, and the date range that it should
    apply for. Before starting this scenario, read more about how `Most Favoured
    Nation duties`_ work and how they are structured.

    .. _measures: https://uktrade.github.io/tariff-data-manual/documentation/data-structures/measures.html
    .. _commodities: https://uktrade.github.io/tariff-data-manual/documentation/data-structures/commodity-codes.html
    .. _Most Favoured Nation duties: https://uktrade.github.io/tariff-data-manual/documentation/trade-policies/most-favoured-nation-duties.html

    @ui
    Scenario: Creating an MFN in the Tariff Editor

        You have been asked to add a third country duty for polycarbonate infant
        feeding bottles. The commodity code is for this commodity is 3924100020.

        You are going to add a new MFN rate of 15% to this commodity code.

        You will do this by using the `Tariff Management Tool`_ to change the
        duty which will be paid by any trader that does not have access to a
        lower duty via a free trade agreement, suspension or quota.

        .. _Tariff Management Tool: https://tamato-training.london.cloudapps.digital

        Given I am on the training envrionment
        And there is a 3924100020 commodity code

        When I visit the home page
        And I select "Create a new measure"
        And I press "Start now"
        Then I am taken to the next page

        When I am on the "Enter the basic data" page
        And I select "Third country duty" as the measure type
        And I select "C2100001" as the regulation ID
        And I select "All countries (erga omnes)" as the geographical area
        And I leave the quota order number blank
        And I select today as the start date
        And I leave the end date blank
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Select commodities and enter the duties" page
        And I select "3924100020" as the commodity code
        And I enter "6.00%" as the duties
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Assign an additional code" page
        And I leave the additional code blank
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Add any condition codes" page
        And I leave the condition code blank
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Add any footnotes" page
        And I leave the footnote blank
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Review your measure" page
        And I press "Create"
        Then I see the confirmation message


    @notebook
    Scenario: Creating a measure in a Jupyter notebook

        Jupyter notebooks are used by data engineers to make backend changes to
        tariff data. If you are not a data engineer, you can ignore this
        scenario and any others make changes using a Jupyter notebook.

        If you are a data engineer, make sure to follow the steps outlined in
        the tariff data repository README to set up your environment first.

        Given a migration notebook
        And there is a 3924100020 commodity code

        When I create a MeasureCreationPattern
        And I call create with the following arguments:
            | argument              | value                                                                    |
            | duty_sentence         | "0.00%"                                                                  |
            | goods_nomenclature    | GoodsNomenclature.current_objects.get(item_id="3924100020", suffix="80") |
            | measure_type          | MeasureType.current_objects.get(description="Third country duty")        |
            | generating_regulation | Regulation.current_objects.get(regulation_id="C2100001")                 |
            | geographical_area     | GeographicalArea.current_objects.get(area_id="1011")                     |
            | validity_start        | date(2020, 1, 1)                                                         |
            | validity_end          | None                                                                     |
        And I validate the workbasket
        Then I get no errors
