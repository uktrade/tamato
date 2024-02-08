from commodities.models import GoodsNomenclature
from geo_areas.models import GeographicalArea
from datetime import date

from commodities.models import GoodsNomenclature
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from reference_documents.models import PreferentialRate


class BaseCheck:
    def run_check(self):
        raise NotImplemented("Please implement on child classes")


class BasePreferentialRateCheck(BaseCheck):
    def __init__(self, preferential_rate: PreferentialRate):
        self.preferential_rate = preferential_rate

    def comm_code(self):
        goods = GoodsNomenclature.objects.latest_approved().filter(
            item_id=self.preferential_rate.commodity_code,
            valid_between__contains=self.ref_doc_version_eif_date(),
            suffix=80,
        )

        if len(goods) == 0:
            return None

        return goods.first()

    def geo_area(self):
        return (
            GeographicalArea.objects.latest_approved()
            .filter(
                area_id=self.preferential_rate.reference_document_version.reference_document.area_id,
            )
            .first()
        )

    def geo_area_description(self):
        geo_area_desc = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea=self.geo_area())
            .last()
        )
        return geo_area_desc.description

    def ref_doc_version_eif_date(self):
        eif_date = (
            self.preferential_rate.reference_document_version.entry_into_force_date
        )

        # todo : make sure EIf dates are all populated correctly - and remove this
        if eif_date is None:
            eif_date = date.today()

        return eif_date

    def related_measures(self):
        return (
            self.comm_code()
            .measures.latest_approved()
            .filter(
                geographical_area=self.geo_area(),
                valid_between__contains=self.ref_doc_version_eif_date(),
            )
        )

    def run_check(self):
        raise NotImplementedError("Please implement on child classes")


class CheckPreferentialRateCommCode(BasePreferentialRateCheck):
    def run_check(self):
        # comm code live on EIF date
        if not self.comm_code():
            print(
                "FAIL",
                self.preferential_rate.commodity_code,
                self.geo_area_description(),
                "comm code not live",
            )
            return False

        measures = self.related_measures()

        if len(measures) == 1:
            print("PASS", self.comm_code(), self.geo_area_description())
            return True

        if len(measures) == 0:
            print("FAIL", self.comm_code(), self.geo_area_description())
            return False

        if len(measures) > 1:
            print(
                "WARNING - multiple measures",
                self.comm_code(),
                self.geo_area_description(),
            )
            return True
