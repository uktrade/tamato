from open_data.models import ReportGoodsNomenclature
from open_data.models.report_models import ReportCommodityReport


def create_commodities_report():
    """
    Produces data for the commodity report, stored in an open_data table.

    Returns:
        None: Operations performed and stored within the NamedTemporaryFile
    """
    commodities = ReportGoodsNomenclature.objects.all().select_related(
        "parent_trackedmodel_ptr",
    )
    id = 0
    for commodity in commodities:
        id += 1
        if commodity.parent_trackedmodel_ptr:
            parent_sid = commodity.parent_trackedmodel_ptr.sid
            parent_code = commodity.parent_trackedmodel_ptr.item_id
            parent_suffix = commodity.parent_trackedmodel_ptr.suffix
        else:
            parent_sid = ""
            parent_code = ""
            parent_suffix = ""

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
