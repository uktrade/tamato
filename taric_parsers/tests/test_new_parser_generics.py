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
    NewAdditionalCodeDescriptionParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeDescriptionPeriodParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeTypeDescriptionParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeTypeParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewFootnoteAssociationAdditionalCodeParser,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateDescriptionParser,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateDescriptionPeriodParser,
)
from taric_parsers.parsers.certificate_parser import NewCertificateParser  # noqa
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateTypeDescriptionParser,
)
from taric_parsers.parsers.certificate_parser import NewCertificateTypeParser  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewFootnoteAssociationGoodsNomenclatureParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureDescriptionParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureDescriptionPeriodParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureIndentParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureOriginParser,
)
from taric_parsers.parsers.commodity_parser import NewGoodsNomenclatureParser  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureSuccessorParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteDescriptionParser  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    NewFootnoteDescriptionPeriodParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteParser  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    NewFootnoteTypeDescriptionParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteTypeParser  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalAreaDescriptionParser,
)
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalAreaDescriptionPeriodParser,
)
from taric_parsers.parsers.geo_area_parser import NewGeographicalAreaParser  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalMembershipParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewAdditionalCodeTypeMeasureTypeParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewDutyExpressionDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewDutyExpressionParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewFootnoteAssociationMeasureParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureActionDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureActionParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureComponentParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureConditionCodeDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureConditionCodeParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureConditionComponentParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureConditionParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureExcludedGeographicalAreaParser,
)
from taric_parsers.parsers.measure_parser import NewMeasurementParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasurementUnitParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitQualifierDescriptionParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitQualifierParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureTypeDescriptionParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureTypeParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureTypeSeriesDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureTypeSeriesParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMonetaryUnitDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMonetaryUnitParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaAssociationParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaBalanceEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaBlockingParser  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    NewQuotaClosedAndTransferredEventParser,
)
from taric_parsers.parsers.quota_parser import NewQuotaCriticalEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaDefinitionParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaExhaustionEventParser  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    NewQuotaOrderNumberOriginExclusionParser,
)
from taric_parsers.parsers.quota_parser import NewQuotaOrderNumberOriginParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaOrderNumberParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaReopeningEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaSuspensionParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaUnblockingEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaUnsuspensionEventParser  # noqa
from taric_parsers.parsers.regulation_parser import NewBaseRegulationParser  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewFullTemporaryStopActionParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewFullTemporaryStopRegulationParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewModificationRegulationParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewRegulationGroupDescriptionParser,
)
from taric_parsers.parsers.regulation_parser import NewRegulationGroupParser  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewRegulationReplacementParser,
)

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
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
            NewAdditionalCodeTypeParser,
            AdditionalCodeType,
            "additional.code.type",
            [],
            False,
        ),
        (
            NewAdditionalCodeTypeDescriptionParser,
            AdditionalCodeType,
            "additional.code.type.description",
            [],
            True,
        ),
        (
            NewAdditionalCodeParser,
            AdditionalCode,
            "additional.code",
            [AdditionalCodeType],
            False,
        ),
        (
            NewAdditionalCodeDescriptionPeriodParser,
            AdditionalCodeDescription,
            "additional.code.description.period",
            [AdditionalCode],
            True,
        ),
        (
            NewAdditionalCodeDescriptionParser,
            AdditionalCodeDescription,
            "additional.code.description",
            [AdditionalCode],
            False,
        ),
        (
            NewFootnoteAssociationAdditionalCodeParser,
            FootnoteAssociationAdditionalCode,
            "footnote.association.additional.code",
            [Footnote, AdditionalCodeType, AdditionalCode],
            False,
        ),
        # Certificates
        (
            NewCertificateTypeParser,
            CertificateType,
            "certificate.type",
            [],
            False,
        ),
        (
            NewCertificateTypeDescriptionParser,
            CertificateType,
            "certificate.type.description",
            [],
            True,
        ),
        (
            NewCertificateParser,
            Certificate,
            "certificate",
            [CertificateType],
            False,
        ),
        (
            NewCertificateDescriptionParser,
            CertificateDescription,
            "certificate.description",
            [CertificateType, Certificate],
            False,
        ),
        (
            NewCertificateDescriptionPeriodParser,
            CertificateDescription,
            "certificate.description.period",
            [CertificateType, Certificate],
            True,
        ),
        # Commodities
        (
            NewGoodsNomenclatureParser,
            GoodsNomenclature,
            "goods.nomenclature",
            [],
            False,
        ),
        (
            NewGoodsNomenclatureOriginParser,
            GoodsNomenclatureOrigin,
            "goods.nomenclature.origin",
            [GoodsNomenclature],
            False,
        ),
        (
            NewGoodsNomenclatureSuccessorParser,
            GoodsNomenclatureSuccessor,
            "goods.nomenclature.successor",
            [GoodsNomenclature],
            False,
        ),
        (
            NewGoodsNomenclatureDescriptionParser,
            GoodsNomenclatureDescription,
            "goods.nomenclature.description",
            [GoodsNomenclature],
            False,
        ),
        (
            NewGoodsNomenclatureDescriptionPeriodParser,
            GoodsNomenclatureDescription,
            "goods.nomenclature.description.period",
            [GoodsNomenclature],
            True,
        ),
        (
            NewGoodsNomenclatureIndentParser,
            GoodsNomenclatureIndent,
            "goods.nomenclature.indents",
            [GoodsNomenclature],
            False,
        ),
        (
            NewFootnoteAssociationGoodsNomenclatureParser,
            FootnoteAssociationGoodsNomenclature,
            "footnote.association.goods.nomenclature",
            [GoodsNomenclature, Footnote],
            False,
        ),
        # Footnotes
        (
            NewFootnoteTypeParser,
            FootnoteType,
            "footnote.type",
            [],
            False,
        ),
        (
            NewFootnoteTypeDescriptionParser,
            FootnoteType,
            "footnote.type.description",
            [FootnoteType],
            True,
        ),
        (
            NewFootnoteParser,
            Footnote,
            "footnote",
            [FootnoteType],
            False,
        ),
        (
            NewFootnoteDescriptionParser,
            FootnoteDescription,
            "footnote.description",
            [Footnote],
            False,
        ),
        (
            NewFootnoteDescriptionPeriodParser,
            FootnoteDescription,
            "footnote.description.period",
            [Footnote],
            True,
        ),
        # Geo Areas
        (
            NewGeographicalAreaParser,
            GeographicalArea,
            "geographical.area",
            [GeographicalArea],
            False,
        ),
        (
            NewGeographicalAreaDescriptionParser,
            GeographicalAreaDescription,
            "geographical.area.description",
            [GeographicalArea],
            False,
        ),
        (
            NewGeographicalAreaDescriptionPeriodParser,
            GeographicalAreaDescription,
            "geographical.area.description.period",
            [GeographicalArea],
            True,
        ),
        (
            NewGeographicalMembershipParser,
            GeographicalMembership,
            "geographical.membership",
            [GeographicalArea],
            False,
        ),
        # Measures
        (
            NewMeasureTypeSeriesParser,
            MeasureTypeSeries,
            "measure.type.series",
            [],
            False,
        ),
        (
            NewMeasureTypeSeriesDescriptionParser,
            MeasureTypeSeries,
            "measure.type.series.description",
            [],
            True,
        ),
        (
            NewMeasurementUnitParser,
            MeasurementUnit,
            "measurement.unit",
            [],
            False,
        ),
        (
            NewMeasurementUnitDescriptionParser,
            MeasurementUnit,
            "measurement.unit.description",
            [],
            True,
        ),
        (
            NewMeasurementUnitQualifierParser,
            MeasurementUnitQualifier,
            "measurement.unit.qualifier",
            [],
            False,
        ),
        (
            NewMeasurementUnitQualifierDescriptionParser,
            MeasurementUnitQualifier,
            "measurement.unit.qualifier.description",
            [],
            True,
        ),
        (
            NewMeasurementParser,
            Measurement,
            "measurement",
            [MeasurementUnit, MeasurementUnitQualifier],
            False,
        ),
        (
            NewMonetaryUnitParser,
            MonetaryUnit,
            "monetary.unit",
            [],
            False,
        ),
        (
            NewMonetaryUnitDescriptionParser,
            MonetaryUnit,
            "monetary.unit.description",
            [],
            True,
        ),
        (
            NewDutyExpressionParser,
            DutyExpression,
            "duty.expression",
            [],
            False,
        ),
        (
            NewDutyExpressionDescriptionParser,
            DutyExpression,
            "duty.expression.description",
            [],
            True,
        ),
        (
            NewMeasureTypeParser,
            MeasureType,
            "measure.type",
            [],
            False,
        ),
        (
            NewMeasureTypeDescriptionParser,
            MeasureType,
            "measure.type.description",
            [],
            True,
        ),
        (
            NewAdditionalCodeTypeMeasureTypeParser,
            AdditionalCodeTypeMeasureType,
            "additional.code.type.measure.type",
            [MeasureType, AdditionalCodeType],
            False,
        ),
        (
            NewMeasureConditionCodeParser,
            MeasureConditionCode,
            "measure.condition.code",
            [],
            False,
        ),
        (
            NewMeasureConditionCodeDescriptionParser,
            MeasureConditionCode,
            "measure.condition.code.description",
            [],
            True,
        ),
        (
            NewMeasureActionParser,
            MeasureAction,
            "measure.action",
            [],
            False,
        ),
        (
            NewMeasureActionDescriptionParser,
            MeasureAction,
            "measure.action.description",
            [],
            True,
        ),
        (
            NewMeasureParser,
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
            NewMeasureComponentParser,
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
            NewMeasureConditionParser,
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
            NewMeasureConditionComponentParser,
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
            NewMeasureExcludedGeographicalAreaParser,
            MeasureExcludedGeographicalArea,
            "measure.excluded.geographical.area",
            [Measure, GeographicalArea],
            False,
        ),
        (
            NewFootnoteAssociationMeasureParser,
            FootnoteAssociationMeasure,
            "footnote.association.measure",
            [Measure, Footnote],
            False,
        ),
        # Quotas
        (
            NewQuotaOrderNumberParser,
            QuotaOrderNumber,
            "quota.order.number",
            [],
            False,
        ),
        (
            NewQuotaOrderNumberOriginParser,
            QuotaOrderNumberOrigin,
            "quota.order.number.origin",
            [QuotaOrderNumber, GeographicalArea],
            False,
        ),
        (
            NewQuotaOrderNumberOriginExclusionParser,
            QuotaOrderNumberOriginExclusion,
            "quota.order.number.origin.exclusions",
            [QuotaOrderNumberOrigin, GeographicalArea],
            False,
        ),
        (
            NewQuotaDefinitionParser,
            QuotaDefinition,
            "quota.definition",
            [QuotaOrderNumber, MonetaryUnit, MeasurementUnit, MeasurementUnitQualifier],
            False,
        ),
        (
            NewQuotaAssociationParser,
            QuotaAssociation,
            "quota.association",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaSuspensionParser,
            QuotaSuspension,
            "quota.suspension.period",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaBlockingParser,
            QuotaBlocking,
            "quota.blocking.period",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaEventParser,
            QuotaEvent,
            "parent.quota.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaBalanceEventParser,
            QuotaEvent,
            "quota.balance.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaClosedAndTransferredEventParser,
            QuotaEvent,
            "quota.closed.and.transferred.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaCriticalEventParser,
            QuotaEvent,
            "quota.critical.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaExhaustionEventParser,
            QuotaEvent,
            "quota.exhaustion.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaReopeningEventParser,
            QuotaEvent,
            "quota.reopening.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaUnblockingEventParser,
            QuotaEvent,
            "quota.unblocking.event",
            [QuotaDefinition],
            False,
        ),
        (
            NewQuotaUnsuspensionEventParser,
            QuotaEvent,
            "quota.unsuspension.event",
            [QuotaDefinition],
            False,
        ),
        # Regulations
        (
            NewRegulationGroupParser,
            Group,
            "regulation.group",
            [],
            False,
        ),
        (
            NewRegulationGroupDescriptionParser,
            Group,
            "regulation.group.description",
            [],
            True,
        ),
        (
            NewBaseRegulationParser,
            Regulation,
            "base.regulation",
            [],
            False,
        ),
        (
            NewModificationRegulationParser,
            Amendment,
            "modification.regulation",
            [],
            False,
        ),
        (
            NewFullTemporaryStopRegulationParser,
            Suspension,
            "full.temporary.stop.regulation",
            [],
            False,
        ),
        (
            NewFullTemporaryStopActionParser,
            Suspension,
            "fts.regulation.action",
            [],
            False,
        ),
        (
            NewRegulationReplacementParser,
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
