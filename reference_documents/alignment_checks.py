from commodities.models import GoodsNomenclature
from geo_areas.models import GeographicalArea
from reference_documents.models import PreferentialRate


class BaseCheck:
    def run_check(self):
        raise NotImplemented("Please implement on child classes")


class BasePreferentialRateCheck(BaseCheck):
    def __init__(self, preferential_rate: PreferentialRate):
        self.preferential_rate = preferential_rate

    def comm_code(self):
        return GoodsNomenclature.objects.latest_approved().get(
            item_id=self.preferential_rate.commodity_code,
        )

    def geo_area(self):
        return GeographicalArea.objects.latest_approved().get(
            area_id=self.preferential_rate.reference_document_version.reference_document.area_id,
        )

    def run_check(self):
        raise NotImplementedError("Please implement on child classes")


class CheckPreferentialRateCommCode(BasePreferentialRateCheck):
    def run_check(self):
        measures = self.comm_code().measures.get(geographical_area=self.geo_area())

        return (
            len(measures) > 0,
            f"{len(measures)} measures matched required preferential rate",
        )
