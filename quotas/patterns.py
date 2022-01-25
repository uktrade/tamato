from typing import Iterator

from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.util import materialise_geo_area
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.validators import AdministrationMechanism


class QuotaCreationPattern:
    def __init__(self, workbasket):
        self.workbasket = workbasket

    def create_exclusions(
        self,
        origin: QuotaOrderNumberOrigin,
        exclusion: GeographicalArea,
    ) -> Iterator[QuotaOrderNumberOriginExclusion]:
        quota_origins = materialise_geo_area(
            origin.geographical_area,
            date=origin.valid_between.lower,
            transaction=self.workbasket.current_transaction,
        )

        exclusions = materialise_geo_area(
            exclusion,
            date=origin.valid_between.lower,
            transaction=self.workbasket.current_transaction,
        )

        for exclusion in exclusions:
            assert (
                exclusion in quota_origins
            ), f"{exclusion.area_id} not in {list(x.area_id for x in quota_origins)}"
            yield QuotaOrderNumberOriginExclusion.objects.create(
                origin=origin,
                excluded_geographical_area=exclusion,
                update_type=UpdateType.CREATE,
                transaction=origin.transaction,
            )

    def create(
        self,
        valid_between: TaricDateRange,
        origins=frozenset(),
        exclusions=frozenset(),
        **data,
    ):
        txn = (
            self.workbasket.new_transaction()
            if "transaction" not in data
            else data["transaction"]
        )
        common = {}
        common.setdefault("update_type", UpdateType.CREATE)
        common.setdefault("transaction", txn)

        data.setdefault("mechanism", AdministrationMechanism.FCFS)

        quota = QuotaOrderNumber.objects.create(
            valid_between=valid_between, **common, **data
        )
        for geo_area in origins:
            origin = QuotaOrderNumberOrigin.objects.create(
                order_number=quota,
                geographical_area=geo_area,
                valid_between=valid_between,
                **common,
            )

            for exclusion in exclusions:
                list(self.create_exclusions(origin, exclusion))

        return quota

    def define_periods(self, quota: QuotaOrderNumber, *periods: TaricDateRange, **data):
        # Ensure that if only one of these is set, the other is the same
        data.setdefault("initial_volume", data.get("volume"))
        data.setdefault("volume", data.get("initial_volume"))
        data.setdefault("maximum_precision", 3)
        data.setdefault("quota_critical", False)
        data.setdefault("quota_critical_threshold", 90)
        data.setdefault("update_type", UpdateType.CREATE)

        defns = []
        for period in periods:
            data["transaction"] = (
                self.workbasket.new_transaction()
                if "transaction" not in data
                else data["transaction"]
            )
            defns.append(
                QuotaDefinition.objects.create(
                    order_number=quota,
                    valid_between=period,
                    **data,
                ),
            )

        return defns
