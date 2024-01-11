import pytest

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeDescription
from additional_codes.models import AdditionalCodeType
from additional_codes.models import FootnoteAssociationAdditionalCode
from certificates.models import Certificate
from certificates.models import CertificateDescription
from certificates.models import CertificateType
from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureOrigin
from commodities.models import GoodsNomenclatureSuccessor
from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from footnotes.models import FootnoteType
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from measures.models import AdditionalCodeTypeMeasureType
from measures.models import DutyExpression
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureComponent
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureConditionComponent
from measures.models import MeasureExcludedGeographicalArea
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MeasureType
from measures.models import MeasureTypeSeries
from measures.models import MonetaryUnit
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaDefinition
from quotas.models import QuotaEvent
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.models import QuotaSuspension
from regulations.models import Amendment
from regulations.models import Group
from regulations.models import Regulation
from regulations.models import Replacement
from regulations.models import Suspension
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeDescriptionParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeDescriptionPeriodParserV2,
)
from taric_parsers.parsers.additional_code_parsers import AdditionalCodeParserV2  # noqa
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeTypeDescriptionParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeTypeParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    FootnoteAssociationAdditionalCodeParserV2,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    CertificateDescriptionParserV2,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    CertificateDescriptionPeriodParserV2,
)
from taric_parsers.parsers.certificate_parser import CertificateParserV2  # noqa
from taric_parsers.parsers.certificate_parser import (  # noqa
    CertificateTypeDescriptionParserV2,
)
from taric_parsers.parsers.certificate_parser import CertificateTypeParserV2  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    FootnoteAssociationGoodsNomenclatureParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureDescriptionParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureDescriptionPeriodParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureIndentParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureOriginParserV2,
)
from taric_parsers.parsers.commodity_parser import GoodsNomenclatureParserV2  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureSuccessorParserV2,
)
from taric_parsers.parsers.footnote_parser import FootnoteDescriptionParserV2  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    FootnoteDescriptionPeriodParserV2,
)
from taric_parsers.parsers.footnote_parser import FootnoteParserV2  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    FootnoteTypeDescriptionParserV2,
)
from taric_parsers.parsers.footnote_parser import FootnoteTypeParserV2  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    GeographicalAreaDescriptionParserV2,
)
from taric_parsers.parsers.geo_area_parser import (  # noqa
    GeographicalAreaDescriptionPeriodParserV2,
)
from taric_parsers.parsers.geo_area_parser import GeographicalAreaParserV2  # noqa
from taric_parsers.parsers.geo_area_parser import GeographicalMembershipParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    AdditionalCodeTypeMeasureTypeParserV2,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    DutyExpressionDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import DutyExpressionParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    FootnoteAssociationMeasureParserV2,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureActionDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureActionParserV2  # noqa
from taric_parsers.parsers.measure_parser import MeasureComponentParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureConditionCodeDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureConditionCodeParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureConditionComponentParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureConditionParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureExcludedGeographicalAreaParserV2,
)
from taric_parsers.parsers.measure_parser import MeasurementParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasurementUnitDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasurementUnitParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasurementUnitQualifierDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasurementUnitQualifierParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureParserV2  # noqa
from taric_parsers.parsers.measure_parser import MeasureTypeDescriptionParserV2  # noqa
from taric_parsers.parsers.measure_parser import MeasureTypeParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureTypeSeriesDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureTypeSeriesParserV2  # noqa
from taric_parsers.parsers.measure_parser import MonetaryUnitDescriptionParserV2  # noqa
from taric_parsers.parsers.measure_parser import MonetaryUnitParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaAssociationParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaBalanceEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaBlockingParserV2  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    QuotaClosedAndTransferredEventParserV2,
)
from taric_parsers.parsers.quota_parser import QuotaCriticalEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaDefinitionParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaExhaustionEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    QuotaOrderNumberOriginExclusionParserV2,
)
from taric_parsers.parsers.quota_parser import QuotaOrderNumberOriginParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaOrderNumberParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaReopeningEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaSuspensionParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaUnblockingEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaUnsuspensionEventParserV2  # noqa
from taric_parsers.parsers.regulation_parser import BaseRegulationParserV2  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    FullTemporaryStopActionParserV2,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    FullTemporaryStopRegulationParserV2,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    ModificationRegulationParserV2,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    RegulationGroupDescriptionParserV2,
)
from taric_parsers.parsers.regulation_parser import RegulationGroupParserV2  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    RegulationReplacementParserV2,
)

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
@pytest.mark.parametrize(
    (
        "parser_class",
        "model_class",
        "expected_xml_tag_name",
        "links_to",
        "child_to_other_parser",
    ),
    (
        # Additional Codes
        (
            AdditionalCodeTypeParserV2,
            AdditionalCodeType,
            "additional.code.type",
            [],
            False,
        ),
        (
            AdditionalCodeTypeDescriptionParserV2,
            AdditionalCodeType,
            "additional.code.type.description",
            [],
            True,
        ),
        (
            AdditionalCodeParserV2,
            AdditionalCode,
            "additional.code",
            [AdditionalCodeType],
            False,
        ),
        (
            AdditionalCodeDescriptionPeriodParserV2,
            AdditionalCodeDescription,
            "additional.code.description.period",
            [AdditionalCode],
            True,
        ),
        (
            AdditionalCodeDescriptionParserV2,
            AdditionalCodeDescription,
            "additional.code.description",
            [AdditionalCode],
            False,
        ),
        (
            FootnoteAssociationAdditionalCodeParserV2,
            FootnoteAssociationAdditionalCode,
            "footnote.association.additional.code",
            [Footnote, AdditionalCodeType, AdditionalCode],
            False,
        ),
        # Certificates
        (
            CertificateTypeParserV2,
            CertificateType,
            "certificate.type",
            [],
            False,
        ),
        (
            CertificateTypeDescriptionParserV2,
            CertificateType,
            "certificate.type.description",
            [],
            True,
        ),
        (
            CertificateParserV2,
            Certificate,
            "certificate",
            [CertificateType],
            False,
        ),
        (
            CertificateDescriptionParserV2,
            CertificateDescription,
            "certificate.description",
            [CertificateType, Certificate],
            False,
        ),
        (
            CertificateDescriptionPeriodParserV2,
            CertificateDescription,
            "certificate.description.period",
            [CertificateType, Certificate],
            True,
        ),
        # Commodities
        (
            GoodsNomenclatureParserV2,
            GoodsNomenclature,
            "goods.nomenclature",
            [],
            False,
        ),
        (
            GoodsNomenclatureOriginParserV2,
            GoodsNomenclatureOrigin,
            "goods.nomenclature.origin",
            [GoodsNomenclature],
            False,
        ),
        (
            GoodsNomenclatureSuccessorParserV2,
            GoodsNomenclatureSuccessor,
            "goods.nomenclature.successor",
            [GoodsNomenclature],
            False,
        ),
        (
            GoodsNomenclatureDescriptionParserV2,
            GoodsNomenclatureDescription,
            "goods.nomenclature.description",
            [GoodsNomenclature],
            False,
        ),
        (
            GoodsNomenclatureDescriptionPeriodParserV2,
            GoodsNomenclatureDescription,
            "goods.nomenclature.description.period",
            [GoodsNomenclature],
            True,
        ),
        (
            GoodsNomenclatureIndentParserV2,
            GoodsNomenclatureIndent,
            "goods.nomenclature.indents",
            [GoodsNomenclature],
            False,
        ),
        (
            FootnoteAssociationGoodsNomenclatureParserV2,
            FootnoteAssociationGoodsNomenclature,
            "footnote.association.goods.nomenclature",
            [GoodsNomenclature, Footnote],
            False,
        ),
        # Footnotes
        (
            FootnoteTypeParserV2,
            FootnoteType,
            "footnote.type",
            [],
            False,
        ),
        (
            FootnoteTypeDescriptionParserV2,
            FootnoteType,
            "footnote.type.description",
            [FootnoteType],
            True,
        ),
        (
            FootnoteParserV2,
            Footnote,
            "footnote",
            [FootnoteType],
            False,
        ),
        (
            FootnoteDescriptionParserV2,
            FootnoteDescription,
            "footnote.description",
            [Footnote],
            False,
        ),
        (
            FootnoteDescriptionPeriodParserV2,
            FootnoteDescription,
            "footnote.description.period",
            [Footnote],
            True,
        ),
        # Geo Areas
        (
            GeographicalAreaParserV2,
            GeographicalArea,
            "geographical.area",
            [GeographicalArea],
            False,
        ),
        (
            GeographicalAreaDescriptionParserV2,
            GeographicalAreaDescription,
            "geographical.area.description",
            [GeographicalArea],
            False,
        ),
        (
            GeographicalAreaDescriptionPeriodParserV2,
            GeographicalAreaDescription,
            "geographical.area.description.period",
            [GeographicalArea],
            True,
        ),
        (
            GeographicalMembershipParserV2,
            GeographicalMembership,
            "geographical.membership",
            [GeographicalArea],
            False,
        ),
        # Measures
        (
            MeasureTypeSeriesParserV2,
            MeasureTypeSeries,
            "measure.type.series",
            [],
            False,
        ),
        (
            MeasureTypeSeriesDescriptionParserV2,
            MeasureTypeSeries,
            "measure.type.series.description",
            [],
            True,
        ),
        (
            MeasurementUnitParserV2,
            MeasurementUnit,
            "measurement.unit",
            [],
            False,
        ),
        (
            MeasurementUnitDescriptionParserV2,
            MeasurementUnit,
            "measurement.unit.description",
            [],
            True,
        ),
        (
            MeasurementUnitQualifierParserV2,
            MeasurementUnitQualifier,
            "measurement.unit.qualifier",
            [],
            False,
        ),
        (
            MeasurementUnitQualifierDescriptionParserV2,
            MeasurementUnitQualifier,
            "measurement.unit.qualifier.description",
            [],
            True,
        ),
        (
            MeasurementParserV2,
            Measurement,
            "measurement",
            [MeasurementUnit, MeasurementUnitQualifier],
            False,
        ),
        (
            MonetaryUnitParserV2,
            MonetaryUnit,
            "monetary.unit",
            [],
            False,
        ),
        (
            MonetaryUnitDescriptionParserV2,
            MonetaryUnit,
            "monetary.unit.description",
            [],
            True,
        ),
        (
            DutyExpressionParserV2,
            DutyExpression,
            "duty.expression",
            [],
            False,
        ),
        (
            DutyExpressionDescriptionParserV2,
            DutyExpression,
            "duty.expression.description",
            [],
            True,
        ),
        (
            MeasureTypeParserV2,
            MeasureType,
            "measure.type",
            [],
            False,
        ),
        (
            MeasureTypeDescriptionParserV2,
            MeasureType,
            "measure.type.description",
            [],
            True,
        ),
        (
            AdditionalCodeTypeMeasureTypeParserV2,
            AdditionalCodeTypeMeasureType,
            "additional.code.type.measure.type",
            [MeasureType, AdditionalCodeType],
            False,
        ),
        (
            MeasureConditionCodeParserV2,
            MeasureConditionCode,
            "measure.condition.code",
            [],
            False,
        ),
        (
            MeasureConditionCodeDescriptionParserV2,
            MeasureConditionCode,
            "measure.condition.code.description",
            [],
            True,
        ),
        (
            MeasureActionParserV2,
            MeasureAction,
            "measure.action",
            [],
            False,
        ),
        (
            MeasureActionDescriptionParserV2,
            MeasureAction,
            "measure.action.description",
            [],
            True,
        ),
        (
            MeasureParserV2,
            Measure,
            "measure",
            [
                MeasureType,
                GeographicalArea,
                GoodsNomenclature,
                AdditionalCode,
                QuotaOrderNumber,
                Regulation,
            ],
            False,
        ),
        (
            MeasureComponentParserV2,
            MeasureComponent,
            "measure.component",
            [
                Measure,
                DutyExpression,
                MonetaryUnit,
                Measurement,
            ],
            False,
        ),
        (
            MeasureConditionParserV2,
            MeasureCondition,
            "measure.condition",
            [
                Measure,
                MeasureConditionCode,
                MonetaryUnit,
                Measurement,
                MeasureAction,
                Certificate,
            ],
            False,
        ),
        (
            MeasureConditionComponentParserV2,
            MeasureConditionComponent,
            "measure.condition.component",
            [
                MeasureCondition,
                DutyExpression,
                MonetaryUnit,
                Measurement,
            ],
            False,
        ),
        (
            MeasureExcludedGeographicalAreaParserV2,
            MeasureExcludedGeographicalArea,
            "measure.excluded.geographical.area",
            [Measure, GeographicalArea],
            False,
        ),
        (
            FootnoteAssociationMeasureParserV2,
            FootnoteAssociationMeasure,
            "footnote.association.measure",
            [Measure, Footnote],
            False,
        ),
        # Quotas
        (
            QuotaOrderNumberParserV2,
            QuotaOrderNumber,
            "quota.order.number",
            [],
            False,
        ),
        (
            QuotaOrderNumberOriginParserV2,
            QuotaOrderNumberOrigin,
            "quota.order.number.origin",
            [QuotaOrderNumber, GeographicalArea],
            False,
        ),
        (
            QuotaOrderNumberOriginExclusionParserV2,
            QuotaOrderNumberOriginExclusion,
            "quota.order.number.origin.exclusions",
            [QuotaOrderNumberOrigin, GeographicalArea],
            False,
        ),
        (
            QuotaDefinitionParserV2,
            QuotaDefinition,
            "quota.definition",
            [QuotaOrderNumber, MonetaryUnit, MeasurementUnit, MeasurementUnitQualifier],
            False,
        ),
        (
            QuotaAssociationParserV2,
            QuotaAssociation,
            "quota.association",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaSuspensionParserV2,
            QuotaSuspension,
            "quota.suspension.period",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaBlockingParserV2,
            QuotaBlocking,
            "quota.blocking.period",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaEventParserV2,
            QuotaEvent,
            "parent.quota.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaBalanceEventParserV2,
            QuotaEvent,
            "quota.balance.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaClosedAndTransferredEventParserV2,
            QuotaEvent,
            "quota.closed.and.transferred.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaCriticalEventParserV2,
            QuotaEvent,
            "quota.critical.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaExhaustionEventParserV2,
            QuotaEvent,
            "quota.exhaustion.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaReopeningEventParserV2,
            QuotaEvent,
            "quota.reopening.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaUnblockingEventParserV2,
            QuotaEvent,
            "quota.unblocking.event",
            [QuotaDefinition],
            False,
        ),
        (
            QuotaUnsuspensionEventParserV2,
            QuotaEvent,
            "quota.unsuspension.event",
            [QuotaDefinition],
            False,
        ),
        # Regulations
        (
            RegulationGroupParserV2,
            Group,
            "regulation.group",
            [],
            False,
        ),
        (
            RegulationGroupDescriptionParserV2,
            Group,
            "regulation.group.description",
            [],
            True,
        ),
        (
            BaseRegulationParserV2,
            Regulation,
            "base.regulation",
            [],
            False,
        ),
        (
            ModificationRegulationParserV2,
            Amendment,
            "modification.regulation",
            [],
            False,
        ),
        (
            FullTemporaryStopRegulationParserV2,
            Suspension,
            "full.temporary.stop.regulation",
            [],
            False,
        ),
        (
            FullTemporaryStopActionParserV2,
            Suspension,
            "fts.regulation.action",
            [],
            False,
        ),
        (
            RegulationReplacementParserV2,
            Replacement,
            "regulation.replacement",
            [],
            False,
        ),
    ),
)
def test_importer_generics(
    parser_class,
    model_class,
    expected_xml_tag_name,
    links_to,
    child_to_other_parser,
):
    # verify xml tag name
    assert parser_class.xml_object_tag == expected_xml_tag_name

    if parser_class.model != model_class:
        print(f"for {parser_class} model {parser_class.model} is not {model_class}")

    # check we have the right model class for the parser
    assert parser_class.model == model_class

    # check that we parent parsers for all parsers that should append to a parent parser
    if child_to_other_parser:
        assert parser_class.parent_parser is not None
    else:
        assert parser_class.parent_parser is None

    # check properties exist on target model
    excluded_variable_names = [
        "__annotations__",
        "__doc__",
        "__module__",
        "issues",
        "model",
        "model_links",
        "parent_parser",
        "value_mapping",
        "xml_object_tag",
        "valid_between_lower",
        "valid_between_upper",
        "record_code",
        "identity_fields",
        "non_taric_additional_fields",
        "data_fields",
        "last_published_description_with_period",
        "allow_update_without_children",
        "updates_allowed",
        "deletes_allowed",
        "skip_identity_check",
    ]

    for variable_name in vars(parser_class).keys():
        if variable_name not in excluded_variable_names:
            # Skip fields that are defined in data_fields - these are collected and appended to a data column
            if variable_name in parser_class.data_fields:
                continue
            # where a variable name contains '__' it defines a related object and its properties, we only need to check
            # that the part preceding the '__' exists
            variable_first_part = variable_name.split("__")[0]
            assert hasattr(parser_class.model, variable_first_part), (
                f"(Testing {parser_class.__name__})"
                f"for {parser_class.model.__name__} no "
                f"property named {variable_first_part} found."
            )

        # Check that each parser has a populated identity field, used to identify the record on updates
        assert len(parser_class.identity_fields) > 0

    # check that there is a direct link between parent model and child model when should_append_to_parent is True
    # this link can be on the parent or the child
    if child_to_other_parser:
        child_to_parent_link = False
        parent_to_child_link = False

        # check child
        if parser_class.model_links:
            for link in parser_class.model_links:
                if link.model == parser_class.model:
                    child_to_parent_link = True

        # check parent
        parent_parser = parser_class.parent_parser

        if parent_parser.model_links:
            for link in parent_parser.model_links:
                if link.model == parser_class.model:
                    parent_to_child_link = True

        # check that one exists
        assert child_to_parent_link or parent_to_child_link

        # check both do not exist
        assert child_to_parent_link is not parent_to_child_link

    # verify existence of link to other importer types
    if len(links_to):
        for klass in links_to:
            link_exists = False
            for link in parser_class.model_links:
                if link.model == klass:
                    link_exists = True

            assert link_exists
    else:
        assert links_to == []
