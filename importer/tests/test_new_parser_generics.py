import pytest

from additional_codes.models import AdditionalCodeDescription
from additional_codes.models import FootnoteAssociationAdditionalCode
from additional_codes.new_import_parsers import *
from certificates.new_import_parsers import *
from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureOrigin
from commodities.models import GoodsNomenclatureSuccessor
from commodities.new_import_parsers import *
from footnotes.models import FootnoteDescription
from footnotes.new_import_parsers import *
from geo_areas.models import GeographicalAreaDescription
from geo_areas.models import GeographicalMembership
from geo_areas.new_import_parsers import *
from importer.new_parsers import ParserHelper
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
from measures.models import MeasureType
from measures.models import MeasureTypeSeries
from measures.new_import_parsers import *
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaDefinition
from quotas.models import QuotaEvent
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.models import QuotaSuspension
from quotas.new_import_parsers import *
from regulations.models import Amendment
from regulations.models import Group
from regulations.models import Replacement
from regulations.models import Suspension
from regulations.new_import_parsers import *

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    (
        "parser_class",
        "model_class",
        "expected_xml_tag_name",
        "links_to",
        "should_append_to_parent",
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
            [AdditionalCode, AdditionalCodeType],
            True,
        ),
        (
            NewAdditionalCodeDescriptionParser,
            AdditionalCodeDescription,
            "additional.code.description",
            [AdditionalCode, AdditionalCodeType],
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
            [GoodsNomenclature, FootnoteType, Footnote],
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
            False,
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
            [Footnote, FootnoteType],
            False,
        ),
        (
            NewFootnoteDescriptionPeriodParser,
            FootnoteDescription,
            "footnote.description.period",
            [Footnote, FootnoteType],
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
            "geographical.area.membership",
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
                AdditionalCodeType,
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
                MeasurementUnit,
                MeasurementUnitQualifier,
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
                MeasurementUnit,
                MeasurementUnitQualifier,
                MeasureAction,
                Certificate,
                CertificateType,
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
                MeasurementUnit,
                MeasurementUnitQualifier,
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
            [Measure, FootnoteType, Footnote],
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
            "quota.([a-z.]+).event",
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
    should_append_to_parent,
):
    # verify xml tag name
    assert parser_class.xml_object_tag == expected_xml_tag_name

    if parser_class.model != model_class:
        print(f"for {parser_class} model {parser_class.model} is not {model_class}")

    assert parser_class.model == model_class
    assert should_append_to_parent == parser_class.append_to_parent

    # check that there is a direct link between parent model and child model when should_append_to_parent is True
    # this link can be on the parent or the child
    if should_append_to_parent:
        child_to_parent_link = False
        parent_to_child_link = False

        # check child
        for link in parser_class.model_links:
            if link.model == parser_class.model:
                child_to_parent_link = True

        # check parent
        parent_parser = ParserHelper.get_parser_by_model(parser_class.model)
        for link in parent_parser.model_links:
            if link.model == parser_class.model:
                parent_to_child_link = True

        assert child_to_parent_link or parent_to_child_link

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
