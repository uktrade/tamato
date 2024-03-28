from datetime import date

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from common.models import Transaction
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from reference_documents.models import PreferentialQuota
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.models import PreferentialRate


class BaseCheck:
    def __init__(self):
        self.dependent_on_passing_check = None

    def run_check(self):
        raise NotImplemented("Please implement on child classes")


class BasePreferentialQuotaCheck(BaseCheck):
    def __init__(self, preferential_quota: PreferentialQuota):
        super().__init__()
        self.preferential_quota = preferential_quota


class BasePreferentialQuotaOrderNumberCheck(BaseCheck):
    def __init__(self, preferential_quota_order_number: PreferentialQuotaOrderNumber):
        super().__init__()
        self.preferential_quota_order_number = preferential_quota_order_number


class BasePreferentialRateCheck(BaseCheck):
    def __init__(self, preferential_rate: PreferentialRate):
        super().__init__()
        self.preferential_rate = preferential_rate

    def get_snapshot(self) -> CommodityTreeSnapshot:
        # not liking having to use CommodityTreeSnapshot, but it does to the job
        item_id = self.comm_code().item_id
        while item_id[-2:] == "00":
            item_id = item_id[0 : len(item_id) - 2]

        commodities_collection = CommodityCollectionLoader(
            prefix=item_id,
        ).load(current_only=True)

        latest_transaction = Transaction.objects.order_by("created_at").last()

        snapshot = CommodityTreeSnapshot(
            commodities=commodities_collection.commodities,
            moment=SnapshotMoment(transaction=latest_transaction),
        )

        return snapshot

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

    def related_measures(self, comm_code_item_id=None):
        if comm_code_item_id:
            good = GoodsNomenclature.objects.latest_approved().filter(
                item_id=comm_code_item_id,
                valid_between__contains=self.ref_doc_version_eif_date(),
                suffix=80,
            )

            if len(good) == 1:
                return (
                    good.first()
                    .measures.latest_approved()
                    .filter(
                        geographical_area=self.geo_area(),
                        valid_between__contains=self.ref_doc_version_eif_date(),
                        measure_type__sid__in=[
                            142,
                            143,
                        ],  # note : these are the measure types used to identify preferential tariffs
                    )
                )
            else:
                return []
        else:
            return (
                self.comm_code()
                .measures.latest_approved()
                .filter(
                    geographical_area=self.geo_area(),
                    valid_between__contains=self.ref_doc_version_eif_date(),
                    measure_type__sid__in=[
                        142,
                        143,
                    ],  # note : these are the measure types used to identify preferential tariffs
                )
            )

    def recursive_comm_code_check(
        self,
        snapshot: CommodityTreeSnapshot,
        parent_item_id,
        parent_item_suffix,
        level=1,
    ):
        # find comm code from snapshot
        child_commodities = []
        for commodity in snapshot.commodities:
            if (
                commodity.item_id == parent_item_id
                and commodity.suffix == parent_item_suffix
            ):
                child_commodities = snapshot.get_children(commodity)
                break

        if len(child_commodities) == 0:
            print(f'{"-" * level} no more children')
            return False

        results = []
        for child_commodity in child_commodities:
            related_measures = self.related_measures(child_commodity.item_id)

            if len(related_measures) == 0:
                print(f'{"-" * level} FAIL : {child_commodity.item_id}')
                results.append(
                    self.recursive_comm_code_check(
                        snapshot,
                        child_commodity.item_id,
                        child_commodity.suffix,
                        level + 1,
                    ),
                )
            elif len(related_measures) == 1:
                print(f'{"-" * level} PASS : {child_commodity.item_id}')
                results.append(True)
            else:
                # Multiple measures
                print(f'{"-" * level} PASS : multiple : {child_commodity.item_id}')
                results.append(True)

        return False in results

    def run_check(self):
        raise NotImplementedError("Please implement on child classes")