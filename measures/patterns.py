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
from typing import Type

from django.db import transaction
from django.db.models.aggregates import Max

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.models.trackedmodel import TrackedModel
from common.renderers import counter_generator
from common.util import TaricDateRange
from common.util import maybe_max
from common.util import maybe_min
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from geo_areas.patterns import ExclusionCreationPattern
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


def get_counter(model: Type[TrackedModel]):
    def counter(self):
        last_sid = model.objects.values("sid").order_by("sid").last()
        next_sid = 1 if last_sid is None else last_sid["sid"] + 1
        return counter_generator(next_sid)

    return cached_property(counter)


class CertificateControlPattern:
    """
    Implements patterns that add one or more ``MeasureCondition`` objects to a
    measure that model certificate requirements based on some policy criteria.

    Properties on the derived classes provide the objects that should be used to
    set up the conditions.

    For example, the "authorised use" pattern requires that a N990 certificate
    be provided for a commodity and prevents imports if not provided. This
    policy is always implemented using condition code "B", measure action "apply
    mentioned duty" when the certificate is provided, or measure action
    "subheading not allowed" if the certificate is not provided.
    """

    def __init__(self, workbasket: WorkBasket):
        self.workbasket = workbasket
        self.logger = logging.getLogger(type(self).__name__)

    condition_code: MeasureConditionCode
    with_certificate: MeasureAction
    without_certificate: MeasureAction

    sid_counter = get_counter(MeasureCondition)

    # TODO: in the future, it would be nice to power these from a database table.
    # That way, we could expose a UI for users to create and maintain these patterns,
    # as we expect new ones to appear over time as policies change.

    def _get_max_sequence_number(self, measure: Measure) -> int:
        """Returns the maximum sequence number for conditions."""
        return (
            measure.conditions.approved_up_to_transaction(
                self.workbasket.current_transaction,
            )
            .filter(condition_code=self.condition_code)
            .aggregate(max=Max("component_sequence_number"))["max"]
            or 0
        )

    def _create_conditions(self, measure: Measure, transaction=None):
        max_sequence_number = self._get_max_sequence_number(measure)
        certificates = self.get_certificates(measure)

        if any(certificates):
            for index, certificate in enumerate(
                certificates,
                start=max_sequence_number + 1,
            ):
                yield MeasureCondition(
                    sid=self.sid_counter(),
                    dependent_measure=measure,
                    component_sequence_number=index,
                    condition_code=self.condition_code,
                    required_certificate=certificate,
                    action=self.with_certificate,
                    update_type=UpdateType.CREATE,
                    transaction=transaction,
                )
            yield MeasureCondition(
                sid=self.sid_counter(),
                dependent_measure=measure,
                component_sequence_number=index + 1,
                condition_code=self.condition_code,
                action=self.without_certificate,
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )

    def applies_to(self, measure: Measure) -> bool:
        raise NotImplementedError(f"Subclass must implement {self.applies_to.__name__}")

    def get_certificates(self, measure: Measure) -> Sequence[Certificate]:
        raise NotImplementedError(
            f"Subclass must implement {self.get_certificates.__name__}",
        )

    def apply(self, measure: Measure, transaction=None) -> Sequence[MeasureCondition]:
        if not self.applies_to(measure):
            self.logger.warning(
                f"Tried to apply {type(self).__name__} to {measure} but it does not apply",
            )
            return []

        transaction = transaction or measure.transaction
        if transaction not in self.workbasket.transactions.all():
            raise ValueError(f"{transaction} is not in {self.workbasket}")

        conditions = []
        for condition in self._create_conditions(measure, transaction):
            condition.save()
            self.logger.debug("Created %s", condition)
            conditions.append(condition)

        return conditions


class AuthorisedUsePattern(CertificateControlPattern):
    """Implements a pattern that adds a N990 certificate requirement to a
    measure if the measure type has an authorised use measure type."""

    @cached_property
    def authorised_use_measure_types(self):
        return set(
            MeasureType.objects.approved_up_to_transaction(
                self.workbasket.current_transaction,
            ).filter(description__contains="authorised use"),
        )

    @cached_property
    def condition_code(self) -> MeasureConditionCode:
        return MeasureConditionCode.objects.get(code="B")

    @cached_property
    def certificates(self) -> Sequence[Certificate]:
        return [
            Certificate.objects.approved_up_to_transaction(
                self.workbasket.current_transaction,
            ).get(
                certificate_type__sid="N",
                sid="990",
            ),
        ]

    @cached_property
    def with_certificate(self) -> MeasureAction:
        return MeasureAction.objects.get(code="27")

    @cached_property
    def without_certificate(self) -> MeasureAction:
        return MeasureAction.objects.get(code="08")

    def applies_to(self, measure: Measure) -> bool:
        return measure.measure_type in self.authorised_use_measure_types

    def get_certificates(self, measure: Measure) -> Sequence[Certificate]:
        return self.certificates


class OriginQuotaPattern(CertificateControlPattern):
    """Implements a pattern that adds required certificates to the measure if
    the measure references an origin quota."""

    @cached_property
    def with_certificate(self) -> MeasureAction:
        return MeasureAction.objects.get(code="27")

    @cached_property
    def without_certificate(self) -> MeasureAction:
        return MeasureAction.objects.get(code="07")

    @cached_property
    def condition_code(self) -> MeasureConditionCode:
        return MeasureConditionCode.objects.get(code="Q")

    def applies_to(self, measure: Measure) -> bool:
        return (
            measure.order_number and measure.order_number.required_certificates.exists()
        )

    def get_certificates(self, measure: Measure) -> Sequence[Certificate]:
        return measure.order_number.required_certificates.all()


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
        self.condition_patterns = (
            AuthorisedUsePattern(workbasket),
            OriginQuotaPattern(workbasket),
        )
        self.duty_sentence_parser = duty_sentence_parser or DutySentenceParser.get(
            base_date,
        )
        self.condition_sentence_parser = (
            condition_sentence_parser
            or ConditionSentenceParser.get(
                base_date,
                workbasket=workbasket,
            )
        )
        self.exclusion_pattern = ExclusionCreationPattern(
            exclusion_type=MeasureExcludedGeographicalArea,
            excluded_from_name="modified_measure",
            workbasket=workbasket,
        )

    measure_sid_counter = get_counter(Measure)
    measure_condition_sid_counter = get_counter(MeasureCondition)

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

    def create_condition_and_components(
        self,
        data,
        component_sequence_number,
        measure,
        parser,
    ):
        """
        Creates condition from data dict, component_sequence_number, and
        measure.

        If applicable_duty field is passed in data, uses parser to create
        measure condition components from newly created condition
        """
        condition = MeasureCondition(
            sid=self.measure_condition_sid_counter(),
            component_sequence_number=component_sequence_number,
            dependent_measure=measure,
            update_type=UpdateType.CREATE,
            transaction=measure.transaction,
            duty_amount=data.get("duty_amount"),
            condition_code=data["condition_code"],
            action=data.get("action"),
            required_certificate=data.get("required_certificate"),
            monetary_unit=data.get("monetary_unit"),
            condition_measurement=data.get(
                "condition_measurement",
            ),
        )
        condition.clean()
        condition.save()

        if data.get("applicable_duty"):
            components = parser.parse(data["applicable_duty"])
            for c in components:
                c.condition = condition
                c.transaction = condition.transaction
                c.update_type = UpdateType.CREATE
                c.save()

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

        new_measure = Measure.objects.create(**measure_data)
        yield new_measure

        # If there are any geographical exclusions, output them attached to
        # the measure. If a group is passed as an exclusion, the members of
        # that group will be excluded instead.
        # TODO: create multiple measures if memberships come to an end.
        for exclusion in exclusions:
            yield from self.exclusion_pattern.create(
                new_measure,
                exclusion,
            )

        # Output any footnote associations required.
        yield from self.create_measure_footnotes(new_measure, footnotes)

        # If we have a condition sentence, parse and add to the measure.
        if condition_sentence:
            yield from self.create_measure_conditions(new_measure, condition_sentence)

        # If any patterns apply to this measure, apply them now.
        for pattern in self.condition_patterns:
            if pattern.applies_to(new_measure):
                yield from pattern.apply(new_measure)

        # If there is a duty_sentence parse it and generate the duty components from the duty rate.
        if duty_sentence:
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
            Measure.objects.with_effective_valid_between()
            .approved_up_to_transaction(self.workbasket.current_transaction)
            .filter(
                goods_nomenclature__sid=code.sid,
                db_effective_valid_between__contains=as_at,
            )
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
            existing_measures = list(self.get_mfn_measures(code, validity_start))
            if not any(existing_measures):
                self.logger.error(
                    "No MFN found on code %s at %s.",
                    code,
                    validity_start,
                )
                return None

            # If the MFN measure does not have an additional code, remove it.
            # If not, keep it because the other suspension still needs it.
            if (
                len(existing_measures) == 1
                and existing_measures[0].additional_code is None
            ):
                deleted_mfn_measure = existing_measures[0].terminate(
                    self.workbasket,
                    validity_start - timedelta(days=1),
                )
                self._log("Terminated", deleted_mfn_measure)

        # Now create the new MFN measure.
        maybe_mfn = self.get_suspended_mfn_measure(code, validity_start)
        if not maybe_mfn.exists() and (copy_from or any(existing_measures)):
            mfn_measure = (copy_from or existing_measures[0]).copy(
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
