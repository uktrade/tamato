Feature: 2. Creating a new suspension with footnotes

    A tariff suspension or tariff relief is where the normal import duty is
    removed or reduced (“suspended”) for imports. Suspensions are often
    time-limited whereas reliefs are often more permanent. Read more about
    `suspensions and reliefs`_.

    As with a Most Favoured Nation rate, a suspension is implemented using a
    measure attached to a specific commodity. The two main differences are that
    a suspension uses a different measure type and that suspension measures
    often have explanatory footnotes attached.

    A “footnote” is a short explanatory text that can be attached to a measure
    or commodity code. Footnotes are to advise traders about special conditions
    associated with a measure or code. Read more about `footnotes`_.

    Footnotes are grouped into different types – e.g. footnotes to do with
    sanctions, or footnotes to do with export control. Most footnotes that are
    applied to suspensions are of the “duty suspension” type. The types are just
    for grouping and don't serve any special purpose.

    Creating a new suspension will often involve creating a new duty suspension
    footnote as well. The footnote has to be created first and then the
    suspension measure is created next.

    In places where the suspension only covers part of a commodity code they
    are sometimes implemented using additional codes. That advanced scenario
    will be covered later.

    .. _suspensions and reliefs: https://uktrade.github.io/tariff-data-manual/documentation/trade-policies/suspensions-and-reliefs.html
    .. _footnotes: https://uktrade.github.io/tariff-data-manual/documentation/data-structures/footnotes.html


    @ui
    Scenario: Creating a footnote using the Tariff Editor

        You have been asked to create a new duty suspension which requires a
        footnote to provide information on how the new suspension is to be used.

        The duty suspension you create will be to allow butene to be imported
        without incurring any fees to do so.

        You will create the footnote first to explain the suspension it is to
        read: “This suspension does not apply to mixtures falling under this
        commodity code”.

        You will then create the duty suspension and add the footnote to it.

        Given I am on the training environment
        And there is a duty suspension (DS) footnote type

        When I visit the homepage
        And I select "Create a new footnote"
        Then I am taken to the next page

        When I am on the "Create a new footnote" page
        And I select "DS - Duty suspension" as the footnote type
        And I enter today as the start date
        And I enter "This suspension does not apply to mixtures falling under this commodity code" as the description
        And I press "Save"
        Then I see the confirmation message


    @ui
    Scenario: Creating a suspension measure using the Tariff Editor

        You will now create a suspension measure to remove the duty. The
        relevant commodity code is 290123.

        This measure looks similar to the Most Favoured Nation duty measure, but
        now you are using a different measure type and regulation. You will also
        attach the footnote you created in the last scenario.

        Given I am on the training environment
        And there is a DS footnote

        When I visit the home page
        And I select "Create a new measure"
        And I press "Start now"
        Then I am taken to the next page

        When I am on the "Enter the basic data" page
        And I select "Autonomous tariff suspension" as the measure type
        And I select "C2100003" as the regulation ID
        And I select "All countries (erga omnes)" as the geographical area
        And I leave the quota order number blank
        And I select today as the start date
        And I leave the end date blank
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Select commodities and enter the duties" page
        And I select "2901230000" as the commodity code
        And I enter "0.00%" as the duties
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
        And I select "DS001" as the footnote
        And I press "Continue"
        Then I am taken to the next step

        When I am on the "Review your measure" page
        And I press "Create"
        Then I see the confirmation message


    @notebook
    Scenario: Creating a footnote using a Jupyter notebook

        This scenario is the first demonstration of creating a “described
        object” in a notebook. Footnotes, additional codes, certificates,
        geographical areas and commodity codes are all described objects, and
        all have the same rules and structure associated with their
        descriptions.

        This scenario also demonstrates an error condition being found using
        business rules. In this case, a described object is not allowed to exist
        without a description. Note that in order to fix this, the description
        we create must be in the same transaction as the footnote, because all
        business rules must pass after every transaction.

        Given a migration notebook
        And there is a duty suspension (DS) footnote type
        When I create a Footnote called DS001 with the following arguments:
            | argument      | value                                                   |
            | footnote_type | FootnoteType.current_objects.get(footnote_type_id="DS") |
            | footnote_id   | "001"                                                   |
            | valid_between | TaricDateRange(date.today(), None)                      |
            | transaction   | workbasket.new_transaction()                            |
            | update_type   | UpdateType.CREATE                                       |
        And I validate the workbasket
        Then I get errors

        When I create a FootnoteDescription with the following arguments:
            | argument           | value                                                                        |
            | described_footnote | DS001                                                                        |
            | description        | "This suspension only applies to mixtures falling under this commodity code" |
            | validity_start     | DS001.valid_between.lower                                                    |
            | transaction        | DS001.transaction                                                            |
            | update_type        | UpdateType.CREATE                                                            |
        And I validate the workbasket
        Then I get no errors


    @notebook
    Scenario: Creating a suspension measure using a Jupyter notebook

        This scenario demonstrates that defaults can be given to the
        MeasureCreationPattern, which removes the need to specify them with
        every call.

        Given a migration notebook
        And there is a commodity code
        When I create a MeasureCreationPattern with defaults:
            | argument              | value                                                                       |
            | measure_type          | MeasureType.current_objects.get(description="Autonomous tariff suspension") |
            | generating_regulation | Regulation.current_objects.get(regulation_id="C2100003")                    |
            | geographical_area     | GeographicalArea.current_objects.get(area_id="1011")                        |
        And I call create with the following arguments:
            | argument           | value                                                                    |
            | duty_sentence      | "0.00%"                                                                  |
            | goods_nomenclature | GoodsNomenclature.current_objects.get(item_id="2901230000", suffix="80") |
            | validity_start     | date.today()                                                             |
            | validity_end       | None                                                                     |
        And I validate the workbasket
        Then I get no errors
