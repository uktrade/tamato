import time

from geo_areas.models import GeographicalArea
from open_data.models import ReportGeographicalArea


def save_geo_areas(verbose):
    report_geo_areas = ReportGeographicalArea.objects.select_related(
        "trackedmodel_ptr",
    ).all()
    start = time.time()
    for report_geo_area in report_geo_areas:
        geo_area = report_geo_area.trackedmodel_ptr
        report_geo_area.is_single_region_or_country = (
            geo_area.is_single_region_or_country()
        )
        report_geo_area.is_all_countries = geo_area.is_all_countries()
        report_geo_area.is_group = geo_area.is_group()
        report_geo_area.is_all_countries = geo_area.is_all_countries()

        description = (
            GeographicalArea.objects.get(pk=report_geo_area.trackedmodel_ptr_id)
            .get_description()
            .description
        )
        report_geo_area.description = description
        report_geo_area.save()
    if verbose:
        print(f"Save GEO AREA Elapsed time {time.time() - start}")
