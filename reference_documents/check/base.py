import abc
from datetime import date
from datetime import timedelta
from typing import Optional

from django.db.models import Q

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityCollectionLoader
from commodities.models.dc import CommodityTreeSnapshot
from commodities.models.dc import SnapshotMoment
from common.models import Transaction
from common.util import TaricDateRange
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from measures.models import Measure
from quotas.models import QuotaDefinition, QuotaAssociation, QuotaSuspension
from quotas.models import QuotaOrderNumber
from reference_documents.models import RefQuotaDefinition, RefQuotaSuspension, AlignmentReportCheckStatus
from reference_documents.models import RefOrderNumber
from reference_documents.models import RefRate


class BaseCheck(abc.ABC):
    """
    abstract Base class, only used to provide a common parent and behaviour to child classes
    that will be used as checks for all reference document objects

    This class contains shared functionality that is used by child classes throughout.
    """
    name = 'Base check'

    def tap_order_number(self, order_number: str):
        """
        Finds a TAP order number matching the provided order number string.

        args:
            order_number (str): The order number used to search for

        returns:
            QuotaOrderNumber or None
        """

        kwargs = {
            'order_number': order_number,
        }

        try:
            order_number = QuotaOrderNumber.objects.latest_approved().get(
                **kwargs
            )
            return order_number
        except QuotaOrderNumber.DoesNotExist:
            return None

    @abc.abstractmethod
    def run_check(self) -> (AlignmentReportCheckStatus, str):
        """
        Abstract method, required to be implemented on inheriting classes

        This method on inheriting classes will be called to execute the check that the
        class represents.
        """
        pass


class BaseQuotaDefinitionCheck(BaseCheck, abc.ABC):
    """
    abstract Base class, only used to provide a common parent and behaviour to child classes
    that will be used as checks for quota definitions.

    This class contains shared functionality that is used by child classes throughout.
    """
    name = 'Base quota definition check'

    def __init__(self, ref_quota_definition: RefQuotaDefinition):
        """
        Initialises the check class

        args:
            ref_quota_definition (RefQuotaDefinition): The reference document quota definition
            object we are checking against
        """
        super().__init__()
        self.ref_quota_definition = ref_quota_definition
        self.ref_order_number = (
            self.ref_quota_definition.ref_order_number
        )
        self.reference_document_version = (
            self.ref_order_number.reference_document_version
        )
        self.reference_document = self.reference_document_version.reference_document

    def tap_order_number(self, order_number: str = None):
        """
        Finds order number in TAP for a given preferential quota.

        args:
            order_number (str): The order number used to search for

        returns:
            QuotaOrderNumber or None
        """
        if order_number is None:
            order_number = self.ref_order_number.order_number

        return super().tap_order_number(order_number)

    def geo_area(self):
        """
        Finds the geo area in TAP for a given preferential quota using data
        from the associated reference document.

        returns:
            GeographicalArea
        """
        geo_area = (
            GeographicalArea.objects.latest_approved()
            .filter(
                area_id=self.reference_document_version.reference_document.area_id,
            )
            .first()
        )
        return geo_area

    def geo_area_description(self):
        """
        Gets the geo area description for a given preferential quota.

        returns:
            str: string associated with the GeographicalArea
        """
        geo_area_desc = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea=self.geo_area())
            .last()
        )
        return geo_area_desc.description

    def commodity_code(self):
        """
        Finds the latest approved version of a commodity code in TAP of a
        given preferential quota.

        returns:
            GoodsNomenclature or None
        """
        goods = GoodsNomenclature.objects.latest_approved().filter(
            Q(
                valid_between__contains=TaricDateRange(self.ref_quota_definition.valid_between.lower, self.ref_quota_definition.valid_between.upper)
            ) | Q(
                valid_between__startswith__lte=self.ref_quota_definition.valid_between.lower,
                valid_between__endswith=None,
            ),
            item_id=self.ref_quota_definition.commodity_code,
            suffix=80,
        )

        if len(goods) == 0:
            return None
        return goods.first()

    def quota_definition(self):
        """
        Searches for the quota definition period in TAP of a given
        preferential quota.

        returns:
            QuotaDefinition or None
        """
        order_number = self.tap_order_number()
        try:
            quota_definition = QuotaDefinition.objects.latest_approved().get(
                order_number=order_number,
                valid_between=self.ref_quota_definition.valid_between,
            )
        except QuotaDefinition.DoesNotExist:
            quota_definition = None
        return quota_definition

    def measures(self):
        """
        Looks for a measure(s) in TAP for a given preferential quota.

        It may find more than one if the original measure was end dated and a
        new one was created.

        returns:
            MeasuresQuerySet
        """
        measures = (
            Measure.objects.latest_approved()
            .filter(
                valid_between__startswith__lte=self.ref_quota_definition.valid_between.upper,
                valid_between__endswith__gte=self.ref_quota_definition.valid_between.lower,
                order_number=self.tap_order_number(),
                goods_nomenclature=self.commodity_code(),
                geographical_area=self.geo_area(),
                measure_type__sid=143,
            )
            .order_by("valid_between")
        )
        return measures

    def measures_cover_quota_definition_validity_period(self):
        """
        Checks the validity period of the measure(s).

        If there is more than one measure it checks that they are contiguous. It
        then checks that the validity period of the quota order number spans the
        validity period of the measure (ON9).

        returns:
            boolean:
                True: when complete coverage over quota definition period (1 or more measures)
                False: when not covered completely or not at all
        """
        measures = self.measures()

        if len(measures) == 0:
            return False
        if len(measures) == 1:
            start_date = measures[0].valid_between.lower
            end_date = measures[0].valid_between.upper
            measure_span_period = TaricDateRange(start_date, end_date)
            return measure_span_period.contains(self.ref_quota_definition.valid_between)
        else:
            measure_span_periods = []
            for index, measure in enumerate(measures):

                if len(measure_span_periods) == 0:
                    measure_span_periods.append(measure.valid_between)
                    continue

                # Check the dates are contiguous and when one measure ends the next one begins
                measure1_end_date = measure_span_periods[-1].upper
                measure2_start_date = measure.valid_between.lower
                if measure1_end_date + timedelta(days=1) != measure2_start_date:
                    measure_span_periods.append(measure.valid_between)
                else:
                    measure_span_periods[-1] = TaricDateRange(measure_span_periods[-1].lower, measure.valid_between.upper)

            for period in measure_span_periods:
                if period.contains(self.ref_quota_definition.valid_between):
                    return True

        return False

    def is_sub_quota(self):
        """
        Is the reference document quota being checked a sub quota

        Returns:
            boolean: True if reference document quota is a sub-quota of another
                quota in the reference data, else False

        """
        return self.ref_order_number.is_sub_quota()

    def get_tap_association(self) -> Optional[QuotaAssociation]:
        """
        Queries and returns the TAP association for a given preferential quota if available.

        Returns:
            QuotaAssociation (nullable):
                QuotaAssociation if matched in TAP data, else None

        """
        tap_sub_quota_definition = self.quota_definition()

        if not self.ref_order_number.main_order_number:
            return None

        tap_main_order_number = self.tap_order_number(
            self.ref_order_number.main_order_number.order_number
        )

        if not tap_main_order_number:
            return None

        try:
            # QA2 : The sub-quota’s validity period must be entirely enclosed within the validity period of the main quota
            tap_main_quota_definition = tap_main_order_number.definitions.latest_approved().get(
                valid_between__startswith__gte=self.ref_quota_definition.ref_order_number.main_order_number.valid_between.lower,
                valid_between__endswith__lte=self.ref_quota_definition.ref_order_number.main_order_number.valid_between.upper,
            )
        except QuotaDefinition.DoesNotExist:
            return None

        try:
            # There should be only one association
            tap_association = QuotaAssociation.objects.latest_approved().get(
                sub_quota=tap_sub_quota_definition,
                main_quota=tap_main_quota_definition,
            )
            return tap_association
        except QuotaAssociation.DoesNotExist:
            return None

    def tap_association_exists(self):
        """
        Queries the TAP association for a given preferential quota and returns boolean
        representing the presence of that association.

        Returns:
            boolean: True if TAP association exists, else False
        """
        tap_association = self.get_tap_association()

        if tap_association:
            return True
        return False

    def check_coefficient(self):
        """
        Checks the TAP coefficient against the reference document expected coefficient and compares

        Returns:
            boolean:
                True of coefficient matches, else False
        """
        if self.tap_association_exists():
            association = self.get_tap_association()

            return float(association.coefficient) == self.ref_order_number.coefficient

        return False

    def duty_rate_matches(self):
        """
        Checks the TAP duty rate against the reference document expected duty rate and compares

        Note: it's possible to have multiple duty rates on a measure, per condition, so if any
        match this check will pass.

        Note: this method is a simple string match but may need to be further improved to match
        numbers with different decimal formatting e.g. 10.000% will not match 10% currently but
        may need updating

        Returns:
            boolean:
                True of duty rate matches, else False
        """
        measure = self.measures()[0]

        duty_sentences = [measure.duty_sentence]

        for condition in measure.conditions.latest_approved():
            duty_sentences.append(condition.duty_sentence)

        if self.ref_quota_definition.duty_rate not in duty_sentences:
            return False

        return True


class BaseOrderNumberCheck(BaseCheck, abc.ABC):
    """
    abstract Base class, only used to provide a common parent and behaviour to child classes
    that will be used as checks for order numbers.

    This class contains shared functionality that is used by child classes throughout.
    """
    name = 'Base preferential quota order number check'

    def __init__(self, ref_order_number: RefOrderNumber):
        """
        Initialises the check class

        args:
            ref_order_number (RefOrderNumber): The reference document order number
            object we are checking against
        """
        super().__init__()
        self.ref_order_number = ref_order_number

    def tap_order_number(self, order_number: str = None):
        """
        Finds a TAP order number matching the provided order number string.

        args:
            order_number (str): The order number used to search for

        returns:
            QuotaOrderNumber or None
        """
        if order_number is None:
            order_number = self.ref_order_number.order_number

        return super().tap_order_number(order_number)


class BaseQuotaSuspensionCheck(BaseCheck, abc.ABC):
    """
    abstract Base class, only used to provide a common parent and behaviour to child classes
    that will be used as checks for quota suspensions.

    This class contains shared functionality that is used by child classes throughout.
    """

    def __init__(self, ref_quota_suspension: RefQuotaSuspension):
        """
        Initialises the check class

        args:
            ref_quota_suspension (RefQuotaSuspension): The reference document quota suspension
            object we are checking against
        """
        super().__init__()
        self.ref_quota_suspension = ref_quota_suspension

    def tap_quota_definition(self):
        """
        Searches for the quota definition period in TAP of a given
        preferential quota.

        returns:
            Quota definition or None: matching TAP quota definition if there
                is a match, else None if no match.
        """
        order_number = self.ref_quota_suspension.ref_quota_definition.ref_order_number.order_number

        try:
            quota_definition = QuotaDefinition.objects.latest_approved().get(
                order_number__order_number=order_number,
                valid_between=self.ref_quota_suspension.ref_quota_definition.valid_between,
            )
        except QuotaDefinition.DoesNotExist:
            quota_definition = None

        return quota_definition

    def tap_order_number(self, order_number: str = None):
        """
        Finds order number in TAP for a given preferential quota.

        returns:
            QuotaOrderNumber or None: matching TAP order number or None if no match.

        """
        if order_number is None:
            order_number = self.ref_quota_suspension.ref_quota_definition.ref_order_number.order_number

        return super().tap_order_number(order_number)

    def tap_suspension(self):
        """
        Finds the TAP suspension if available

        Returns:
            QuotaSuspension or None: matching TAP suspension if available, or None if no match.
        """
        quota_definition = self.tap_quota_definition()

        try:
            suspension = quota_definition.quotasuspension_set.latest_approved().get(
                valid_between=self.ref_quota_suspension.valid_between
            )

        except QuotaSuspension.DoesNotExist:
            return None

        return suspension


class BaseRateCheck(BaseCheck, abc.ABC):
    """
    abstract Base class, only used to provide a common parent and behaviour to child classes
    that will be used as checks for preferential rates.

    This class contains shared functionality that is used by child classes throughout.
    """
    name = 'Base preferential rate check'

    def __init__(self, ref_rate: RefRate):
        """
        Initialises the check class

        args:
            ref_rate (RefRate): The reference document preferential rate
            object we are checking against
        """
        super().__init__()
        self.ref_rate = ref_rate

    def get_snapshot(self, comm_code=None) -> Optional[CommodityTreeSnapshot]:
        """
        Gets a commodity tree snapshot from the provided comm code item id, if an item_id is available

        Note: This query looks at the current live comm code structure, not historical. This seems
        logically correct but may need review in the future for certain edge cases.

        Args:
            comm_code: The string of a comm code (10 digits) to be used top load the snapshot.

        Returns:
            CommodityTreeSnapshot or None: CommodityTreeSnapshot if comm code is available,
            else None is returned
        """
        if comm_code:
            item_id = comm_code
        elif self.tap_comm_code():
            item_id = self.tap_comm_code().item_id
        else:
            return None

        while item_id[-2:] == "00":
            item_id = item_id[0: len(item_id) - 2]

        commodities_collection = CommodityCollectionLoader(
            prefix=item_id,
        ).load(current_only=True)

        latest_transaction = Transaction.objects.order_by("created_at").last()

        snapshot = CommodityTreeSnapshot(
            commodities=commodities_collection.commodities,
            moment=SnapshotMoment(transaction=latest_transaction),
        )

        return snapshot

    def tap_comm_code(self):
        """
        Finds the latest approved version of a commodity code in TAP of a
        given a preferential rate.

        returns:
            GoodsNomenclature or None
        """
        goods = GoodsNomenclature.objects.latest_approved().filter(
            (
                    Q(valid_between__contains=self.ref_rate.valid_between.lower) &
                    Q(valid_between__contains=self.ref_rate.valid_between.upper)
            ),
            item_id=self.ref_rate.commodity_code,
            suffix=80,
        )

        if len(goods) == 0:
            return None

        return goods.first()

    def tap_geo_area(self):
        """
        Finds the latest approved version of a geographical area in TAP for a
        given a preferential rate.

        returns:
            GeographicalArea or None
        """
        try:
            return GeographicalArea.objects.latest_approved().get(
                area_id=self.ref_rate.reference_document_version.reference_document.area_id,
            )

        except GeographicalArea.DoesNotExist:
            return None

    def tap_geo_area_description(self) -> Optional[str]:
        """
        Finds the latest approved version of a geographical area description in TAP for the
        related geographical area.

        returns:
            string (the description of a geographical area) or None
        """
        geo_area = (
            GeographicalAreaDescription.objects
            .latest_approved()
            .filter(described_geographicalarea=self.tap_geo_area())
            .last()
        )

        if geo_area:
            return geo_area.description
        else:
            return None

    def ref_doc_version_eif_date(self):
        """
        Returns the EIF (Entry into force) date for a reference document version

        Returns:
            date or None: if available, the EIF date else none
        """
        eif_date = (
            self.ref_rate.reference_document_version.entry_into_force_date
        )

        if eif_date is None:
            eif_date = date.today()

        return eif_date

    def tap_related_measures(self, comm_code_item_id: str =None):
        """
        queries and returns measures related to a given comm code item id limited to
        measures that have a valid between that overlaps the required period defined
        by the reference document rate

        Args:
            comm_code_item_id: string or None, 10 digit item id for a comm code

        Returns:
            TrackedModelQuerySet or [], matching results to the query or an empty list
            depending on query results
        """
        if comm_code_item_id:
            good = GoodsNomenclature.objects.latest_approved().filter(
                (
                        Q(
                            valid_between__contains=self.ref_rate.valid_between.lower,
                        ) &
                        Q(
                            valid_between__contains=self.ref_rate.valid_between.upper,
                        )
                ),
                item_id=comm_code_item_id,
                suffix=80,
            )

            if len(good) == 1:
                return (
                    good.first()
                    .measures.latest_approved()
                    .filter(
                        (
                                Q(
                                    valid_between__contains=self.ref_rate.valid_between.lower,
                                ) &
                                Q(
                                    valid_between__contains=self.ref_rate.valid_between.upper,
                                )
                        ),
                        geographical_area=self.tap_geo_area(),
                        measure_type__sid__in=[
                            142,
                        ],  # note : these are the measure types used to identify preferential tariffs
                    )
                )
            else:
                return []
        else:
            tap_comm_code = self.tap_comm_code()

            if tap_comm_code:
                return (
                    self.tap_comm_code()
                    .measures.latest_approved()
                    .filter(
                        (
                                Q(
                                    valid_between__contains=self.ref_rate.valid_between.lower,
                                ) &
                                Q(
                                    valid_between__contains=self.ref_rate.valid_between.upper,
                                )
                        ),
                        geographical_area=self.tap_geo_area(),
                        measure_type__sid__in=[
                            142,
                        ],  # note : these are the measure types used to identify preferential tariffs
                    )
                )
            else:
                return []

    def tap_recursive_comm_code_check(
            self,
            snapshot: CommodityTreeSnapshot,
            parent_item_id: str,
            level: int = 1,
    ):
        """
        this function checks the coverage for a rate against children of a comm code.

        In circumstances where coverage for a rate is not applied to the specified comm code
        but to its children this function will check for coverage and if covered, wil return true
        otherwise it will return false

        This is a recursive function and will check the entire tree down to the 10 digit comm code level

        Args:
            snapshot: CommodityTreeSnapshot, A snapshot from self.ref_rate.comm_code and children
            parent_item_id: str, The parent comm code item_id to check
            level: int, the numeric level below the parent comm code that
            is currently being performed at

        Returns: bool, representing the presence or absence of coverage for the rate by children / grandchildren etc

        """

        # find comm code from snapshot
        child_commodities = []
        for commodity in snapshot.commodities:
            if (
                    commodity.item_id == parent_item_id
                    and commodity.suffix == '80'
            ):
                child_commodities = snapshot.get_children(commodity)
                break

        if len(child_commodities) == 0:
            print(f'{"-" * level} no more children')
            return False

        results = []
        for child_commodity in child_commodities:
            related_measures = self.tap_related_measures(child_commodity.item_id)

            if len(related_measures) == 0:
                print(f'{"-" * level} FAIL : {child_commodity.item_id}')
                results.append(
                    self.tap_recursive_comm_code_check(
                        snapshot,
                        child_commodity.item_id,
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

        return False not in results
