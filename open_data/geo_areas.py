from open_data.models import ReportGeographicalArea


def save_geo_areas():
    report_geo_areas = ReportGeographicalArea.objects.select_related(
        "trackedmodel_ptr",
    ).all()
    for report_geo_area in report_geo_areas:
        geo_area = report_geo_area.trackedmodel_ptr
        report_geo_area.is_single_region_or_country = (
            geo_area.is_single_region_or_country()
        )
        report_geo_area.is_all_countries = geo_area.is_all_countries()
        report_geo_area.is_group = geo_area.is_group()
        report_geo_area.is_all_countries = geo_area.is_all_countries()
        report_geo_area.save()
