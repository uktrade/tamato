import logging
from datetime import datetime
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
from common.models.records import TrackedModel
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
from measures.parsers import DutySentenceParser
from quotas.models import QuotaOrderNumber
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


def clonable_data(obj: TrackedModel) -> Dict:
    return {
        field.name: getattr(obj, field.name)
        for field in obj._meta.fields
        if field.name
        not in (
            obj._meta.pk.name,
            "polymorphic_ctype",
            "trackedmodel_ptr",
            "id",
            *obj.identifying_fields,
        )
    }


def copy_measure(measure: Measure, **overrides) -> Measure:
    """Create a copy of the passed measure (applying any overrides) and attach
    copies of all of the original measure's duties, conditions, exclusions and
    footnotes."""

    new_object_kwargs = clonable_data(measure)

    next_sid = Measure.objects.order_by("sid").last().sid
    new_object_kwargs["sid"] = next_sid

    new_object_kwargs.update(overrides)
    new_measure = Measure(**new_object_kwargs)

    # for component in measure.components:

    return new_measure


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
        base_date: datetime,
        defaults: Dict[str, Any] = {},
        duty_sentence_parser: DutySentenceParser = None,
    ) -> None:
        self.workbasket = workbasket
        self.defaults = defaults
        self.duty_sentence_parser = duty_sentence_parser or DutySentenceParser.get(
            base_date,
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

    def get_authorised_use_measure_conditions(
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

    def get_proof_of_origin_condition(
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

    def get_measure_components_from_duty_rate(
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

    def get_measure_excluded_geographical_areas(
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

    def get_measure_footnotes(
        self,
        measure: Measure,
        footnotes: Sequence[Footnote],
    ) -> Sequence[FootnoteAssociationMeasure]:
        footnote_measures = []
        for footnote in footnotes:
            footnote_measures.append(
                FootnoteAssociationMeasure.objects.create(
                    footnoted_measure=measure,
                    associated_footnote=footnote,
                    update_type=UpdateType.CREATE,
                    transaction=measure.transaction,
                ),
            )
        return footnote_measures

    @transaction.atomic
    def create(
        self,
        duty_sentence: str,
        geographical_area: GeographicalArea,
        goods_nomenclature: GoodsNomenclature,
        measure_type: MeasureType,
        validity_start: datetime,
        validity_end: datetime,
        exclusions: Sequence[GeographicalArea] = [],
        order_number: Optional[QuotaOrderNumber] = None,
        authorised_use: bool = False,
        additional_code: AdditionalCode = None,
        footnotes: Sequence[Footnote] = [],
        proofs_of_origin: Sequence[Certificate] = [],
    ) -> Iterator[TrackedModel]:
        """
        Create a new measure linking the passed data and any defaults. The
        measure is saved as part of a single transaction.

        If `exclusions` are passed, measure exclusions will be created for those
        geographical areas on the created measures. If a group is passed as an
        exclusion, all of its members at of the start date of the measure will
        be excluded.

        If `authorised_use` is `True`, measure conditions requiring the N990
        authorised use certificate will be added to the measure.

        If `footnotes` are passed, footnote associations will be added to the
        measure.

        If `proofs_of_origin` are passed, measure conditions requiring the
        proofs will be added to the measure.
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
                "measure_type": measure_type,
                "geographical_area": geographical_area,
                "goods_nomenclature": goods_nomenclature,
                "order_number": order_number or self.defaults.get("order_number"),
                "additional_code": additional_code
                or self.defaults.get("additional_code"),
                "valid_between": TaricDateRange(actual_start, actual_end),
            },
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
            yield from self.get_measure_excluded_geographical_areas(
                new_measure,
                exclusion,
            )

        # Output any footnote associations required.
        yield from self.get_measure_footnotes(new_measure, footnotes)

        # If this is a measure under authorised use, we need to add
        # some measure conditions with the N990 certificate.
        if authorised_use:
            yield from self.get_authorised_use_measure_conditions(new_measure)

        # If this is a measure for an origin quota, we need to add
        # some measure conditions with the passed proof of origin.
        if any(proofs_of_origin):
            yield from self.get_proof_of_origin_condition(new_measure, proofs_of_origin)

        # Now generate the duty components for the passed duty rate.
        yield from self.get_measure_components_from_duty_rate(
            new_measure,
            duty_sentence,
        )
