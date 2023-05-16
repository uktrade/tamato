import pytest

from additional_codes.models import AdditionalCodeDescription
from additional_codes.models import FootnoteAssociationAdditionalCode
from additional_codes.new_import_parsers import *
from certificates.models import CertificateDescription
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
    ("handler_class", "model_class", "expected_xml_tag_name", "links_to"),
    (
        # Additional Codes
        (NewAdditionalCodeTypeParser, AdditionalCodeType, "additional.code.type", []),
        (
            NewAdditionalCodeTypeDescriptionParser,
            AdditionalCodeType,
            "additional.code.type.description",
            [],
        ),
        (
            NewAdditionalCodeParser,
            AdditionalCode,
            "additional.code",
            [AdditionalCodeType],
        ),
        (
            NewAdditionalCodeDescriptionPeriodParser,
            AdditionalCodeDescription,
            "additional.code.description.period",
            [AdditionalCodeDescription, AdditionalCodeType],
        ),
        (
            NewAdditionalCodeDescriptionParser,
            AdditionalCodeDescription,
            "additional.code.description",
            [AdditionalCode, AdditionalCodeType],
        ),
        (
            NewFootnoteAssociationAdditionalCodeParser,
            FootnoteAssociationAdditionalCode,
            "footnote.association.additional.code",
            [Footnote, AdditionalCodeType, AdditionalCode],
        ),
        # Certificates
        (NewCertificateTypeParser, CertificateType, "certificate.type", []),
        (
            NewCertificateTypeDescriptionParser,
            CertificateType,
            "certificate.type.description",
            [],
        ),
        (NewCertificateParser, Certificate, "certificate", [CertificateType]),
        (
            NewCertificateDescriptionParser,
            CertificateDescription,
            "certificate.description",
            [CertificateType, Certificate],
        ),
        (
            NewCertificateDescriptionPeriodParser,
            CertificateDescription,
            "certificate.description.period",
            [CertificateType, Certificate],
        ),
        # Commodities
        (NewGoodsNomenclatureParser, GoodsNomenclature, "goods.nomenclature", []),
        (
            NewGoodsNomenclatureOriginParser,
            GoodsNomenclatureOrigin,
            "goods.nomenclature.origin",
            [GoodsNomenclature],
        ),
        (
            NewGoodsNomenclatureSuccessorParser,
            GoodsNomenclatureSuccessor,
            "goods.nomenclature.successor",
            [GoodsNomenclature],
        ),
        (
            NewGoodsNomenclatureDescriptionParser,
            GoodsNomenclatureDescription,
            "goods.nomenclature.description",
            [GoodsNomenclature],
        ),
        (
            NewGoodsNomenclatureDescriptionPeriodParser,
            GoodsNomenclatureDescription,
            "goods.nomenclature.description.period",
            [GoodsNomenclature],
        ),
        (
            NewGoodsNomenclatureIndentParser,
            GoodsNomenclatureIndent,
            "goods.nomenclature.indents",
            [GoodsNomenclature],
        ),
        (
            NewFootnoteAssociationGoodsNomenclatureParser,
            FootnoteAssociationGoodsNomenclature,
            "footnote.association.goods.nomenclature",
            [GoodsNomenclature, FootnoteType, Footnote],
        ),
        # Footnotes
        (NewFootnoteTypeParser, FootnoteType, "footnote.type", []),
        (
            NewFootnoteTypeDescriptionParser,
            FootnoteType,
            "footnote.type.description",
            [FootnoteType],
        ),
        (NewFootnoteParser, Footnote, "footnote", [FootnoteType]),
        (
            NewFootnoteDescriptionParser,
            FootnoteDescription,
            "footnote.description",
            [Footnote, FootnoteType],
        ),
        (
            NewFootnoteDescriptionPeriodParser,
            FootnoteDescription,
            "footnote.description.period",
            [Footnote, FootnoteType],
        ),
        # Geo Areas
        (
            NewGeographicalAreaParser,
            GeographicalArea,
            "geographical.area",
            [GeographicalArea],
        ),
        (
            NewGeographicalAreaDescriptionParser,
            GeographicalAreaDescription,
            "geographical.area.description",
            [GeographicalArea],
        ),
        (
            NewGeographicalAreaDescriptionPeriodParser,
            GeographicalAreaDescription,
            "geographical.area.description.period",
            [GeographicalArea],
        ),
        (
            NewGeographicalMembershipParser,
            GeographicalMembership,
            "geographical.area.membership",
            [GeographicalArea],
        ),
        # Measures
        (NewMeasureTypeSeriesParser, MeasureTypeSeries, "measure.type.series", []),
        (
            NewMeasureTypeSeriesDescriptionParser,
            MeasureTypeSeries,
            "measure.type.series.description",
            [],
        ),
        (NewMeasurementUnitParser, MeasurementUnit, "measurement.unit", []),
        (
            NewMeasurementUnitDescriptionParser,
            MeasurementUnit,
            "measurement.unit.description",
            [],
        ),
        (
            NewMeasurementUnitQualifierParser,
            MeasurementUnitQualifier,
            "measurement.unit.qualifier",
            [],
        ),
        (
            NewMeasurementUnitQualifierDescriptionParser,
            MeasurementUnitQualifier,
            "measurement.unit.qualifier.description",
            [],
        ),
        (
            NewMeasurementParser,
            Measurement,
            "measurement",
            [MeasurementUnit, MeasurementUnitQualifier],
        ),
        (NewMonetaryUnitParser, MonetaryUnit, "monetary.unit", []),
        (
            NewMonetaryUnitDescriptionParser,
            MonetaryUnit,
            "monetary.unit.description",
            [],
        ),
        (NewDutyExpressionParser, DutyExpression, "duty.expression", []),
        (
            NewDutyExpressionDescriptionParser,
            DutyExpression,
            "duty.expression.description",
            [],
        ),
        (NewMeasureTypeParser, MeasureType, "measure.type", []),
        (NewMeasureTypeDescriptionParser, MeasureType, "measure.type.description", []),
        (
            NewAdditionalCodeTypeMeasureTypeParser,
            AdditionalCodeTypeMeasureType,
            "additional.code.type.measure.type",
            [MeasureType, AdditionalCodeType],
        ),
        (
            NewMeasureConditionCodeParser,
            MeasureConditionCode,
            "measure.condition.code",
            [],
        ),
        (
            NewMeasureConditionCodeDescriptionParser,
            MeasureConditionCode,
            "measure.condition.code.description",
            [],
        ),
        (NewMeasureActionParser, MeasureAction, "measure.action", []),
        (
            NewMeasureActionDescriptionParser,
            MeasureAction,
            "measure.action.description",
            [],
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
        ),
        (
            NewMeasureExcludedGeographicalAreaParser,
            MeasureExcludedGeographicalArea,
            "measure.excluded.geographical.area",
            [Measure, GeographicalArea],
        ),
        (
            NewFootnoteAssociationMeasureParser,
            FootnoteAssociationMeasure,
            "footnote.association.measure",
            [Measure, FootnoteType, Footnote],
        ),
        # Quotas
        (NewQuotaOrderNumberParser, QuotaOrderNumber, "quota.order.number", []),
        (
            NewQuotaOrderNumberOriginParser,
            QuotaOrderNumberOrigin,
            "quota.order.number.origin",
            [QuotaOrderNumber, GeographicalArea],
        ),
        (
            NewQuotaOrderNumberOriginExclusionParser,
            QuotaOrderNumberOriginExclusion,
            "quota.order.number.origin.exclusions",
            [QuotaOrderNumberOrigin, GeographicalArea],
        ),
        (
            NewQuotaDefinitionParser,
            QuotaDefinition,
            "quota.definition",
            [QuotaOrderNumber, MonetaryUnit, MeasurementUnit, MeasurementUnitQualifier],
        ),
        (
            NewQuotaAssociationParser,
            QuotaAssociation,
            "quota.association",
            [QuotaDefinition],
        ),
        (
            NewQuotaSuspensionParser,
            QuotaSuspension,
            "quota.suspension.period",
            [QuotaDefinition],
        ),
        (
            NewQuotaBlockingParser,
            QuotaBlocking,
            "quota.blocking.period",
            [QuotaDefinition],
        ),
        (NewQuotaEventParser, QuotaEvent, "quota.([a-z.]+).event", [QuotaDefinition]),
        # Regulations
        (NewRegulationGroupParser, Group, "regulation.group", []),
        (
            NewRegulationGroupDescriptionParser,
            Group,
            "regulation.group.description",
            [],
        ),
        (NewBaseRegulationParser, Regulation, "base.regulation", []),
        (NewModificationRegulationParser, Amendment, "modification.regulation", []),
        (
            NewFullTemporaryStopRegulationParser,
            Suspension,
            "full.temporary.stop.regulation",
            [],
        ),
        (NewFullTemporaryStopActionParser, Suspension, "fts.regulation.action", []),
        (NewRegulationReplacementParser, Replacement, "regulation.replacement", []),
    ),
)
def test_xml_tag_name(handler_class, model_class, expected_xml_tag_name, links_to):
    # verify xml tag name
    assert handler_class.xml_object_tag == expected_xml_tag_name

    assert handler_class.model == model_class

    # verify existence of link to other importer types
    if len(links_to):
        for klass in links_to:
            link_exists = False
            for link in handler_class.model_links:
                if link.model == klass:
                    link_exists = True

            assert link_exists
    else:
        assert links_to == []
