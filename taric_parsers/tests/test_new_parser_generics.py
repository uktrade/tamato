import pytest

from additional_codes.models import *
from commodities.models import *
from footnotes.models import *
from geo_areas.models import *
from measures.models import *
from quotas.models import *
from regulations.models import *
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.certificate_parser import *
from taric_parsers.parsers.commodity_parser import *
from taric_parsers.parsers.footnote_parser import *
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.measure_parser import *
from taric_parsers.parsers.quota_parser import *
from taric_parsers.parsers.regulation_parser import *

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
