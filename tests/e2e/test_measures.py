import re
from datetime import date

from playwright.sync_api import expect

from common.tests import factories
from common.validators import ApplicabilityCode
from geo_areas.validators import AreaCode


def test_create_a_new_measure(
    page,
    empty_current_workbasket,
    duty_sentence_parser,
    celery_worker,
):
    today = date.today()
    measure_type = factories.MeasureTypeFactory.create(
        measure_component_applicability_code=ApplicabilityCode.PERMITTED,
    )
    regulation = factories.RegulationFactory.create()
    commodity = factories.GoodsNomenclatureFactory.create()
    erga_omnes = factories.GeographicalAreaFactory.create(
        area_code=AreaCode.GROUP,
        area_id="1011",
    )

    page.goto("/measures/create/start/")

    # Start
    expect(page.get_by_role("heading", name="Create a new measure")).to_be_visible()
    page.get_by_role("button", name="Start now").click()

    # Enter basic data step
    expect(page.get_by_role("heading", name="Enter the basic data")).to_be_visible()

    page.locator("#measure_details-measure_type_autocomplete").fill(measure_type.sid)
    page.get_by_role("option", name=measure_type.sid).click()

    start_date_field = page.get_by_role("group", name="Start date")
    start_date_field.get_by_label("Day").fill(str(today.day))
    start_date_field.get_by_label("Month").fill(str(today.month))
    start_date_field.get_by_label("Year").fill(str(today.year))

    page.get_by_label("Commodity code count").fill("1")
    page.get_by_role("button", name="Continue").click()

    # Regulation step
    expect(page.get_by_role("heading", name="Enter the regulation ID")).to_be_visible()
    page.locator("#regulation_id-generating_regulation_autocomplete").fill(
        regulation.regulation_id,
    )
    page.get_by_role("option", name=regulation.regulation_id).click()
    page.get_by_role("button", name="Continue").click()

    # Quota step
    expect(
        page.get_by_role("heading", name="Enter a quota order number ("),
    ).to_be_visible()
    page.get_by_role("button", name="Continue").click()

    # Geo areas step
    expect(
        page.get_by_role("heading", name="Select the geographical area"),
    ).to_be_visible()
    page.get_by_label("All countries (erga omnes)").check()
    page.get_by_role("button", name="Continue").click()

    # Commodities and duties step
    expect(
        page.get_by_role("heading", name="Select commodities and enter"),
    ).to_be_visible()
    page.locator("#measure_commodities_duties_formset-0-commodity_autocomplete").fill(
        commodity.item_id,
    )
    page.get_by_role("option", name=commodity.item_id).click()
    page.get_by_label("Duties").fill("0%")
    page.get_by_role("button", name="Continue").click()

    # Additional code step
    expect(
        page.get_by_role("heading", name="Assign an additional code"),
    ).to_be_visible()
    page.get_by_role("button", name="Continue").click()

    # Conditions step
    expect(page.get_by_role("heading", name="Add any condition codes")).to_be_visible()
    page.get_by_role("button", name="Continue").click()

    # Footnotes step
    expect(page.get_by_role("heading", name="Add any footnotes")).to_be_visible()
    page.get_by_role("button", name="Continue").click()

    # Review step
    expect(page.get_by_role("heading", name="Review your measure")).to_be_visible()
    page.get_by_role("button", name="Create").click()

    # Confirmation
    expect(
        page.get_by_role("heading", name="You successfully submitted"),
    ).to_be_visible()
    expect(page).to_have_url(re.compile("/measures/create/done-async/.+/"))

    # Measures process queue
    page.get_by_role("button", name="View status").click()
    expect(page).to_have_url("/measures/process-queue/")
    page.wait_for_timeout(10000)
    page.reload()
    expect(page.locator('span:has-text("COMPLETED")')).to_be_visible()
