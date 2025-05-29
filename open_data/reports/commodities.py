from open_data.models import ReportGoodsNomenclature
from open_data.models.report_models import ReportCommodityReport


def create_commodities_report(verbose=True):
    """Produces data for the commodity report, stored in an open_data table."""

    ReportCommodityReport.objects.all().delete()

    commodities = ReportGoodsNomenclature.objects.all().select_related(
        "parent_trackedmodel_ptr",
    )

    total_rows = commodities.count()
    if verbose:
        print(f"Commodities: {total_rows} rows")

    id = 0
    for commodity in commodities:
        id += 1
        if verbose:
            if id % 1000 == 0:
                print(f"Completed {id} rows of Commodities")

        if commodity.parent_trackedmodel_ptr:
            parent_sid = commodity.parent_trackedmodel_ptr.sid
            parent_code = commodity.parent_trackedmodel_ptr.item_id
            parent_suffix = commodity.parent_trackedmodel_ptr.suffix
        else:
            parent_sid = None
            parent_code = None
            parent_suffix = None

        ReportCommodityReport.objects.create(
            id=id,
            commodity_sid=commodity.sid,
            commodity_code=commodity.item_id,
            commodity_suffix=commodity.suffix,
            commodity_description=commodity.description,
            commodity_validity_start=commodity.valid_between.lower,
            commodity_validity_end=commodity.valid_between.upper,
            parent_sid=parent_sid,
            parent_code=parent_code,
            parent_suffix=parent_suffix,
        )
