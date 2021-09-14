import random
from typing import Optional

import factory

from common.tests import factories
from measures.sheet_importers import MeasureSheetRow


class MeasureSheetRowFactory(factory.Factory):
    """
    A factory that produces a row that might be read from a sheet of measures as
    recognised by the :class:`measures.sheet_importers.MeasureSheetRow`
    importer.

    The factory references a MeasureFactory to do the production of an actual
    Measure, and then references the data produced by the MeasureFactory to
    build up a row of string values.

    The values are then built into a tuple in the order specified in the
    `MeasureSheetRow` importer.
    """

    class Meta:
        model = tuple
        exclude = ["measure"]

    measure = factory.SubFactory(factories.MeasureFactory)

    item_id = factory.SelfAttribute("measure.goods_nomenclature.item_id")
    measure_type_description = factory.SelfAttribute("measure.measure_type.description")
    duty_sentence = factory.sequence(lambda n: f"{n}.00%")
    origin_description = factory.LazyAttribute(
        lambda m: m.measure.geographical_area.get_description().description,
    )
    excluded_origin_descriptions = factory.LazyAttribute(
        lambda m: random.choice(MeasureSheetRow.separators).join(
            e.excluded_geographical_area.get_description().description
            for e in m.measure.exclusions.all()
        ),
    )
    quota_order_number = factory.LazyAttribute(
        lambda m: m.measure.order_number.order_number
        if m.measure.order_number
        else m.measure.dead_order_number,
    )
    additional_code_id = factory.LazyAttribute(
        lambda m: m.measure.additional_code.type.sid + m.measure.additional_code.code
        if m.measure.additional_code
        else m.measure.dead_additional_code,
    )
    validity_start_date = factory.SelfAttribute("measure.valid_between.lower")
    validity_end_date = factory.SelfAttribute("measure.valid_between.upper")
    regulation_id = factory.SelfAttribute("measure.generating_regulation.regulation_id")
    footnote_ids = factory.LazyAttribute(
        lambda m: random.choice(MeasureSheetRow.separators).join(
            f.footnote_type.footnote_type_id + f.footnote_id
            for f in m.measure.footnotes.all()
        ),
    )

    @factory.lazy_attribute
    def conditions(self) -> Optional[str]:
        """Returns a string that can be parsed by the
        :class:`measures.parsers.ConditionSentenceParser`."""
        if not self.measure.conditions.exists():
            return None

        parts = []
        for c in self.measure.conditions.all():
            part = []
            part.append(c.condition_code.code)
            if c.required_certificate:
                part.append("cert:")
                part.append(
                    f"{c.required_certificate.certificate_type.sid}-{c.required_certificate.sid}",
                )
            part.append(f"({c.action.code}):")
            parts.append(" ".join(part))
        return f"Cond: {'; '.join(parts)}"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        data = [kwargs[k] for k in MeasureSheetRow.columns]
        return super()._create(model_class, data)
