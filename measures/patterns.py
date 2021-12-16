import logging
from dataclasses import dataclass
from datetime import date
from datetime import timedelta
from functools import cached_property
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Sequence

from django.db import transaction

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from certificates.models import CertificateType
from commodities.models import GoodsNomenclature
from common.models.trackedmodel import TrackedModel
from common.renderers import Counter
from common.renderers import counter_generator
from common.util import TaricDateRange
from common.util import maybe_max
from common.util import maybe_min
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from geo_areas.validators import AreaCode
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureExcludedGeographicalArea
from measures.models import MeasureType
from measures.parsers import ConditionSentenceParser
from measures.parsers import DutySentenceParser
from quotas.models import QuotaOrderNumber
from regulations.models import Regulation
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


cases = """\
20154305,3402310000,All third countries,751,20099372
20154306,3402310000,ERGA OMNES,755,20100041
20154311,3402391000,All third countries,751,20099372
20154313,3402391000,ERGA OMNES,755,20100041
20154316,3402399000,All third countries,751,20099373
20154317,3402399000,ERGA OMNES,755,20100042
20154321,3402399010,All third countries,751,20099373
20154322,3402399010,ERGA OMNES,755,20100042
20154328,3402399090,All third countries,751,20099373
20154329,3402399090,ERGA OMNES,755,20100042
20154334,3402410000,All third countries,751,20099374
20154337,3402410000,ERGA OMNES,755,20100043
20154341,3402420000,All third countries,751,20099375
20154342,3402420000,ERGA OMNES,755,20100044
20154350,3402490000,All third countries,751,20099376
20154352,3402490000,ERGA OMNES,755,20100045
20154368,3907210000,All third countries,751,20099518
20154369,3907210000,ERGA OMNES,755,20100189
20154384,3907291100,All third countries,751,20099517
20154385,3907291100,ERGA OMNES,755,20100188
20154393,3907292000,All third countries,751,20099518
20154394,3907292000,ERGA OMNES,755,20100189
20154421,3907299100,All third countries,751,20099519
20154422,3907299100,ERGA OMNES,755,20100190
20154435,3907299900,All third countries,751,20099520
20154436,3907299900,ERGA OMNES,755,20100191
20154469,3911200000,All third countries,751,20099547
20154470,3911200000,ERGA OMNES,755,20100218
20154582,8112610000,All third countries,751,20099748
20154583,8112610000,ERGA OMNES,755,20100419
20154594,8103910000,All third countries,751,20099743
20154595,8103910000,ERGA OMNES,755,20100414
20154604,8103991000,All third countries,751,20099742
20154605,8103991000,ERGA OMNES,755,20100413
20154615,8103999000,All third countries,751,20099743
20154616,8103999000,ERGA OMNES,755,20100414
20154622,8106101000,All third countries,751,20099746
20154623,8106101000,ERGA OMNES,755,20100417
20154636,8106901000,All third countries,751,20099746
20154637,8106901000,ERGA OMNES,755,20100417
20154679,8109310000,All third countries,751,20099754
20154680,8109310000,ERGA OMNES,755,20100425
20154693,8109390000,All third countries,751,20099754
20154694,8109390000,ERGA OMNES,755,20100425
20154734,8112310000,All third countries,751,20099764
20154735,8112310000,ERGA OMNES,755,20100435
20154750,8112411000,All third countries,751,20099765
20154751,8112411000,ERGA OMNES,755,20100436
20154756,8112419000,All third countries,751,20099765
20154757,8112419000,ERGA OMNES,755,20100436
20154772,8112691000,All third countries,751,20099747
20154773,8112691000,ERGA OMNES,755,20100418
20154781,8112699000,All third countries,751,20099749
20154782,8112699000,ERGA OMNES,755,20100420
20154794,8112924000,All third countries,751,20099766
20154795,8112924000,ERGA OMNES,755,20100437
20154825,8701219000,All third countries,751,20099800
20154826,8701219000,ERGA OMNES,755,20100471
20154837,8701229000,All third countries,751,20099800
20154838,8701229000,ERGA OMNES,755,20100471
20154849,8701239000,All third countries,751,20099800
20154850,8701239000,ERGA OMNES,755,20100471
20154860,8701249000,All third countries,751,20099800
20154861,8701249000,ERGA OMNES,755,20100471
20154867,8701290000,All third countries,751,20099800
20154868,8701290000,ERGA OMNES,755,20100471
20154889,8704413900,All third countries,751,20099829
20154890,8704413900,ERGA OMNES,755,20100500
20154907,8704419900,All third countries,751,20099830
20154908,8704419900,ERGA OMNES,755,20100501
20154940,8704429900,All third countries,751,20099831
20154941,8704429900,ERGA OMNES,755,20100502
20154973,8704439900,All third countries,751,20099832
20154974,8704439900,ERGA OMNES,755,20100503
20154999,8704513900,All third countries,751,20099833
20155000,8704513900,ERGA OMNES,755,20100504
20155017,8704519900,All third countries,751,20099834
20155018,8704519900,ERGA OMNES,755,20100505
20155049,8704529900,All third countries,751,20099835
20155050,8704529900,ERGA OMNES,755,20100506
20155059,8704600000,All third countries,751,20099836
20155060,8704600000,ERGA OMNES,755,20100507\
"""
cases = {
    (line[1], line[2], line[3]): line
    for line in map(lambda x: x.split(","), cases.split("\n"))
}


class MeasureCreationPattern:
    """
    A pattern used for creating measures. This pattern will create new measures
    to implement the passed duty sentence along with any associatied models such
    as conditions, exclusions or associations.

    Each measure and its associated models will be created in a single new
    transaction in the passed workbasket. All measures will be created no
    earlier than the `base_date` and the pattern assumes that reference data
    (such as measurements) do not change over the lifetime of the measures
    created. Any `defaults` passed will be used unless overriden by the call to
    `create()`.
    """

    def __init__(
        self,
        workbasket: WorkBasket,
        base_date: date,
        defaults: Dict[str, Any] = {},
        duty_sentence_parser: DutySentenceParser = None,
        condition_sentence_parser: ConditionSentenceParser = None,
    ) -> None:
        self.workbasket = workbasket
        self.defaults = defaults
        self.duty_sentence_parser = duty_sentence_parser or DutySentenceParser.get(
            base_date,
        )
        self.condition_sentence_parser = (
            condition_sentence_parser
            or ConditionSentenceParser.get(
                base_date,
            )
        )

    @cached_property
    def measure_sid_counter(self) -> Counter:
        last_sid = Measure.objects.values("sid").order_by("sid").last()
        next_sid = 1 if last_sid is None else last_sid["sid"] + 1
        return counter_generator(next_sid)

    @cached_property
    def measure_condition_sid_counter(self) -> Counter:
        last_sid = MeasureCondition.objects.values("sid").order_by("sid").last()
        next_sid = 1 if last_sid is None else last_sid["sid"] + 1
        return counter_generator(next_sid)

    @cached_property
    def authorised_use_measure_types(self):
        return set(MeasureType.objects.filter(description__contains="authorised use"))

    @cached_property
    def presentation_of_certificate(self) -> MeasureConditionCode:
        return MeasureConditionCode.objects.get(code="B")

    @cached_property
    def presentation_of_endorsed_certificate(self) -> MeasureConditionCode:
        return MeasureConditionCode.objects.get(code="Q")

    @cached_property
    def end_use_certificate(self) -> Certificate:
        return Certificate.objects.get(
            sid="990",
            certificate_type=CertificateType.objects.get(sid="N"),
        )

    @cached_property
    def apply_mentioned_duty(self) -> MeasureAction:
        return MeasureAction.objects.get(code="27")

    @cached_property
    def subheading_not_allowed(self) -> MeasureAction:
        return MeasureAction.objects.get(code="08")

    @cached_property
    def measure_not_applicable(self) -> MeasureAction:
        return MeasureAction.objects.get(code="07")

    def create_measure_authorised_use_measure_conditions(
        self,
        measure: Measure,
    ) -> Sequence[MeasureCondition]:
        return [
            MeasureCondition.objects.create(
                sid=self.measure_condition_sid_counter(),
                dependent_measure=measure,
                component_sequence_number=1,
                condition_code=self.presentation_of_certificate,
                required_certificate=self.end_use_certificate,
                action=self.apply_mentioned_duty,
                update_type=UpdateType.CREATE,
                transaction=measure.transaction,
            ),
            MeasureCondition.objects.create(
                sid=self.measure_condition_sid_counter(),
                dependent_measure=measure,
                component_sequence_number=2,
                condition_code=self.presentation_of_certificate,
                action=self.subheading_not_allowed,
                update_type=UpdateType.CREATE,
                transaction=measure.transaction,
            ),
        ]

    def create_measure_origin_quota_conditions(
        self,
        measure: Measure,
        certificates: Sequence[Certificate],
    ) -> Iterator[MeasureCondition]:
        if any(certificates):
            for index, certificate in enumerate(certificates, start=1):
                yield MeasureCondition.objects.create(
                    sid=self.measure_condition_sid_counter(),
                    dependent_measure=measure,
                    component_sequence_number=index,
                    condition_code=self.presentation_of_endorsed_certificate,
                    required_certificate=certificate,
                    action=self.apply_mentioned_duty,
                    update_type=UpdateType.CREATE,
                    transaction=measure.transaction,
                )
            yield MeasureCondition.objects.create(
                sid=self.measure_condition_sid_counter(),
                dependent_measure=measure,
                component_sequence_number=index + 1,
                condition_code=self.presentation_of_endorsed_certificate,
                action=self.measure_not_applicable,
                update_type=UpdateType.CREATE,
                transaction=measure.transaction,
            )

    def create_measure_components_from_duty_rate(
        self,
        measure: Measure,
        rate: str,
    ) -> Iterator[MeasureComponent]:
        try:
            for component in self.duty_sentence_parser.parse(rate):
                component.component_measure = measure
                component.update_type = UpdateType.CREATE
                component.transaction = measure.transaction
                component.save()
                yield component
        except RuntimeError as ex:
            logger.error(f"Explosion parsing {rate}")
            raise ex

    def create_measure_conditions(
        self,
        measure: Measure,
        conditions: str,
    ) -> Iterator[MeasureCondition]:
        for index, (condition, component) in enumerate(
            self.condition_sentence_parser.parse(conditions),
            start=1,
        ):
            if not condition:
                raise ValueError(f"Expected to parse a condition from '{conditions}'")

            if condition.required_certificate is None:
                description = (
                    measure.geographical_area.descriptions.order_by(
                        "transaction__order",
                    )
                    .last()
                    .description
                )

                key = (
                    measure.goods_nomenclature.item_id,
                    description,
                    measure.measure_type.sid,
                )

                if key in cases:
                    sid = int(cases[key][-1])

                    prior_condition = (
                        MeasureCondition.objects.approved_up_to_transaction(
                            measure.transaction,
                        )
                        .filter(
                            dependent_measure__sid=sid,
                            required_certificate=condition.required_certificate,
                            condition_code__code=condition.condition_code.code,
                            action__code=condition.action.code,
                        )
                        .order_by(
                            "transaction__partition",
                            "transaction__order",
                        )
                        .last()
                    )

                    if prior_condition and prior_condition.duty_amount:
                        condition.duty_amount = prior_condition.duty_amount
                        try:
                            condition.condition_measurement = (
                                prior_condition.condition_measurement
                            )
                        except Exception:
                            pass
                        try:
                            condition.monetary_unit = prior_condition.monetary_unit
                        except Exception:
                            pass

            condition.sid = self.measure_condition_sid_counter()
            condition.component_sequence_number = index
            condition.dependent_measure = measure
            condition.update_type = UpdateType.CREATE
            condition.transaction = measure.transaction
            condition.save()

            if component:
                component.condition = condition
                component.update_type = UpdateType.CREATE
                component.transaction = condition.transaction
                component.save()

            yield condition

    def create_measure_excluded_geographical_areas(
        self,
        measure: Measure,
        exclusion: GeographicalArea,
    ) -> Iterator[MeasureExcludedGeographicalArea]:
        if exclusion.area_code == AreaCode.GROUP:
            measure_origins = set(
                m.member
                for m in GeographicalMembership.objects.as_at(
                    measure.valid_between.lower,
                )
                .filter(
                    geo_group=measure.geographical_area,
                )
                .all()
            )
            for membership in (
                GeographicalMembership.objects.as_at(measure.valid_between.lower)
                .filter(geo_group=exclusion)
                .all()
            ):
                member = membership.member
                assert (
                    member in measure_origins
                ), f"{member.area_id} not in {list(x.area_id for x in measure_origins)}"
                yield MeasureExcludedGeographicalArea.objects.create(
                    modified_measure=measure,
                    excluded_geographical_area=member,
                    update_type=UpdateType.CREATE,
                    transaction=measure.transaction,
                )
        else:
            yield MeasureExcludedGeographicalArea.objects.create(
                modified_measure=measure,
                excluded_geographical_area=exclusion,
                update_type=UpdateType.CREATE,
                transaction=measure.transaction,
            )

    def create_measure_footnotes(
        self,
        measure: Measure,
        footnotes: Sequence[Footnote],
    ) -> Sequence[FootnoteAssociationMeasure]:
        return [
            FootnoteAssociationMeasure.objects.create(
                footnoted_measure=measure,
                associated_footnote=footnote,
                update_type=UpdateType.CREATE,
                transaction=measure.transaction,
            )
            for footnote in footnotes
        ]

    @transaction.atomic
    def create_measure_tracked_models(
        self,
        duty_sentence: str,
        goods_nomenclature: GoodsNomenclature,
        validity_start: date,
        validity_end: date,
        exclusions: Sequence[GeographicalArea] = [],
        order_number: Optional[QuotaOrderNumber] = None,
        footnotes: Sequence[Footnote] = [],
        condition_sentence: Optional[str] = None,
        **data,
    ) -> Iterator[TrackedModel]:
        """
        Create a new measure linking the passed data and any defaults. The
        measure is saved as part of a single transaction.

        If `exclusions` are passed, measure exclusions will be created for those
        geographical areas on the created measures. If a group is passed as an
        exclusion, all of its members at of the start date of the measure will
        be excluded.

        If the measure type is one of the `self.authorised_use_measure_types`,
        measure conditions requiring the N990 authorised use certificate will be
        added to the measure.

        If `footnotes` are passed, footnote associations will be added to the
        measure.

        If an `order_number` with `required_conditions` is passed, measure
        conditions requiring the certificates will be added to the measure.

        Return an Iterator over all the TrackedModels created, starting with the
        Measure.
        """

        assert goods_nomenclature.suffix == "80", "ME7 – must be declarable"

        actual_start = maybe_max(validity_start, goods_nomenclature.valid_between.lower)
        actual_end = maybe_min(goods_nomenclature.valid_between.upper, validity_end)

        new_measure_sid = self.measure_sid_counter()

        if actual_end != validity_end:
            logger.warning(
                "Measure {} end date capped by {} end date: {:%Y-%m-%d}".format(
                    new_measure_sid,
                    goods_nomenclature.item_id,
                    actual_end,
                ),
            )

        measure_data: Dict[str, Any] = {
            "update_type": UpdateType.CREATE,
            "transaction": self.workbasket.new_transaction(),
            **self.defaults,
            **{
                "sid": new_measure_sid,
                "goods_nomenclature": goods_nomenclature,
                "order_number": order_number or self.defaults.get("order_number"),
                "valid_between": TaricDateRange(actual_start, actual_end),
            },
            **data,
        }

        if actual_end is not None:
            measure_data["terminating_regulation"] = measure_data[
                "generating_regulation"
            ]

        new_measure = Measure.objects.create(**measure_data)
        yield new_measure

        # If there are any geographical exclusions, output them attached to
        # the measure. If a group is passed as an exclusion, the members of
        # that group will be excluded instead.
        # TODO: create multiple measures if memberships come to an end.
        for exclusion in exclusions:
            yield from self.create_measure_excluded_geographical_areas(
                new_measure,
                exclusion,
            )

        # Output any footnote associations required.
        yield from self.create_measure_footnotes(new_measure, footnotes)

        # If this is a measure under authorised use, we need to add
        # some measure conditions with the N990 certificate.
        if new_measure.measure_type in self.authorised_use_measure_types:
            yield from self.create_measure_authorised_use_measure_conditions(
                new_measure,
            )

        # If this is a measure for an origin quota, we need to add
        # some measure conditions with the origin quota required certificates.
        if order_number and order_number.required_certificates.exists():
            yield from self.create_measure_origin_quota_conditions(
                new_measure,
                order_number.required_certificates.all(),
            )

        # If we have a condition sentence, parse and add to the measure.
        if condition_sentence:
            yield from self.create_measure_conditions(new_measure, condition_sentence)

        # Now generate the duty components for the passed duty rate.
        yield from self.create_measure_components_from_duty_rate(
            new_measure,
            duty_sentence,
        )

    def create(self, *args, **kwargs) -> Measure:
        """
        Create a new measure linking the passed data and any defaults and return
        it.

        This is a wrapper around create_measure_tracked_models(). See
        create_measure_tracked_models for in-depth information, including
        accepted arguments.
        """
        measure, *measure_data = (
            tracked_model
            for tracked_model in self.create_measure_tracked_models(*args, **kwargs)
        )
        return measure


@dataclass
class SuspensionViaAdditionalCodePattern:
    """
    A pattern that implements suspensions by using an additional code to
    distinguish between the normal MFN rate and the suspended rate.

    A code that is suspended using this pattern will therefore have two (or
    more) MFN-type measures.

    When the pattern implements the suspension on top of a normal single-measure
    MFN rate, it will terminate the existing measure and replace it with two new
    measures. The pattern can also unsuspend the rate by terminating the two
    additional code measures and replacing them with a single measure.

    If multiple suspensions of this type are applied to the same code, they all
    have an associated MFN measure even though this means duplicating the MFN
    rate.

    If there are multiple patterns of this type applied to the same code,
    different logic applies: adding a new suspension will not terminate the
    existing MFN, and removing the suspension will not restore it. Only the
    first or last suspensions will trigger this behaviour. This means that
    suspensions can be added or removed independently of one another.
    """

    workbasket: WorkBasket
    """The workbasket into which all modified data will be added."""

    mfn_additional_code: AdditionalCode
    """The additional code used on the measure which has the normal MFN rate."""

    full_suspension_additional_code: AdditionalCode
    """The additional code used on the measure which has the suspended rate."""

    mfn_regulation: Regulation
    """The regulation used on the measure which has the normal MFN rate."""

    suspension_regulation: Regulation
    """The regulation used on the measure which has the suspended rate."""

    mfn_measure_type__sids = ("103", "105")

    def __post_init__(self):
        self.logger = logging.getLogger(__name__)

    def _log(self, message: str, measure: Measure):
        self.logger.info(
            message + "".join([" %s"] * 8),
            measure.sid,
            measure.goods_nomenclature,
            measure.valid_between,
            measure.measure_type,
            measure.additional_code,
            list(measure.conditions.all()),
            list(measure.footnotes.all()),
            measure.update_type,
        )

    def get_measures(self, code: GoodsNomenclature, as_at: date):
        """Returns the measures applicable to the passed code on the given
        date."""
        return (
            Measure.objects_with_validity_field()
            .with_duty_sentence()
            .approved_up_to_transaction(self.workbasket.transactions.last())
            .as_at(as_at)
            .filter(goods_nomenclature__sid=code.sid)
        )

    def get_mfn_measures(self, code: GoodsNomenclature, as_at: date):
        """Returns any regular MFN measures applicable to the passed code on the
        given date."""
        return self.get_measures(code, as_at).filter(
            measure_type__sid__in=self.mfn_measure_type__sids,
        )

    def get_suspension_measure(self, code: GoodsNomenclature, as_at: date):
        """Returns any suspension measures applicable to the passed code on the
        given date implemented using this pattern's additional code."""
        return self.get_measures(code, as_at).filter(
            additional_code=self.full_suspension_additional_code,
        )

    def get_suspended_mfn_measure(self, code: GoodsNomenclature, as_at: date):
        """Returns any MFN measures applicable to the passed code on the given
        date implemented using this pattern's additional code."""
        return self.get_mfn_measures(code, as_at).filter(
            additional_code=self.mfn_additional_code,
        )

    def create_suspension(
        self,
        code: GoodsNomenclature,
        duty: str,
        validity_start: date,
        validity_end: Optional[date],
        footnotes=frozenset(),
    ):
        """Create a new measure which will suspend tariffs on the passed code
        down to the given duty rate between the two validity dates."""
        mfn_measure = self.get_suspended_mfn_measure(code, validity_start).get()
        creator = MeasureCreationPattern(self.workbasket, base_date=validity_start)
        suspension_measure = creator.create(
            duty_sentence=duty,
            goods_nomenclature=code,
            validity_start=validity_start,
            validity_end=validity_end,
            geographical_area=mfn_measure.geographical_area,
            measure_type=mfn_measure.measure_type,
            additional_code=self.full_suspension_additional_code,
            generating_regulation=self.suspension_regulation,
            footnotes=footnotes,
        )
        self._log("Created suspension measure", suspension_measure)
        return suspension_measure

    def suspend(
        self,
        code: GoodsNomenclature,
        duty: str,
        validity_start: date,
        validity_end: Optional[date],
        footnotes=frozenset(),
        copy_from: Optional[Measure] = None,
    ):
        """Implement a new suspension on tariffs on the passed code down to the
        given duty rate between the two validity dates."""
        if not copy_from:
            # If there is no MFN measure we have a problem because we don't know what
            # rate to use on the subsequent measure, so just skip that.
            existing_measures = self.get_mfn_measures(code, validity_start)
            if not existing_measures.exists():
                self.logger.warning(
                    "No MFN found on code %s at %s. Resulting suspension will not have MFN rate.",
                    code,
                    validity_start,
                )

            # If the MFN measure does not have an additional code, remove it.
            # If not, keep it because the other suspension still needs it.
            if (
                existing_measures.count() == 1
                and existing_measures.get().additional_code is None
            ):
                deleted_mfn_measure = existing_measures.get().terminate(
                    self.workbasket,
                    validity_start - timedelta(days=1),
                )
                self._log("Terminated", deleted_mfn_measure)

        # Now create the new MFN measure.
        maybe_mfn = self.get_suspended_mfn_measure(code, validity_start)
        if not maybe_mfn.exists():
            mfn_measure = (copy_from or existing_measures.last()).copy(
                goods_nomenclature=code,
                additional_code=self.mfn_additional_code,
                generating_regulation=self.mfn_regulation,
                valid_between=TaricDateRange(validity_start, validity_end),
                transaction=self.workbasket.new_transaction(),
            )
            self._log("Created MFN measure", mfn_measure)

        # Now create the suspended measure.
        return self.create_suspension(
            code,
            duty,
            validity_start,
            validity_end,
            footnotes,
        )

    def unsuspend(
        self,
        code: GoodsNomenclature,
        validity_start: date,
        validity_end: Optional[date],
        replace_onto: Optional[GoodsNomenclature] = None,
    ):
        """End the suspension on tariffs on the passed code as of the passed
        validity dates."""
        if not replace_onto:
            replace_onto = code

        # Find the existing suspension measures and terminate them.
        terminated_suspension = self.get_suspension_measure(code, validity_start).get()
        self._log(
            "Terminated",
            terminated_suspension.terminate(
                self.workbasket,
                validity_start - timedelta(days=1),
            ),
        )

        terminated_mfn = self.get_suspended_mfn_measure(code, validity_start).get()
        self._log(
            "Terminated",
            terminated_mfn.terminate(
                self.workbasket,
                validity_start - timedelta(days=1),
            ),
        )

        # If there are any other codes left, we don't need to recreate the MFN
        # Else, set up a new MFN measure
        if not self.get_mfn_measures(code, validity_start).exists():
            new_mfn = terminated_mfn.copy(
                goods_nomenclature=replace_onto,
                generating_regulation=self.mfn_regulation,
                additional_code=None,
                valid_between=TaricDateRange(validity_start, validity_end),
                transaction=self.workbasket.new_transaction(),  # TODO footnotes
            )
            self._log("Created plain MFN", new_mfn)
