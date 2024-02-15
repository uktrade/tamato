from typing import Dict
from typing import List

from django.db.transaction import atomic

from measures.models import Measure
from measures.models import MeasureActionPair
from measures.models import MeasureConditionComponent
from measures.parsers import DutySentenceParser
from measures.patterns import MeasureCreationPattern
from workbaskets.models import WorkBasket


class MeasuresCreator:
    def __init__(self, workbasket: WorkBasket):
        self.workbasket = workbasket

    @atomic
    def create_measures(self, data: Dict) -> List[Measure]:
        """Returns a list of the created measures."""
        measure_start_date = data["valid_between"].lower

        measure_creation_pattern = MeasureCreationPattern(
            workbasket=self.workbasket,
            base_date=measure_start_date,
            defaults={
                "generating_regulation": data["generating_regulation"],
            },
        )

        measures_data = []

        for commodity_data in data.get("formset-commodities", []):
            if not commodity_data.get("DELETE"):
                for geo_data in data["geo_areas_and_exclusions"]:
                    measure_data = {
                        "measure_type": data["measure_type"],
                        "geographical_area": geo_data["geo_area"],
                        "exclusions": geo_data.get("exclusions", []),
                        "goods_nomenclature": commodity_data["commodity"],
                        "additional_code": data["additional_code"],
                        "order_number": data["order_number"],
                        "validity_start": measure_start_date,
                        "validity_end": data["valid_between"].upper,
                        "footnotes": [
                            item["footnote"]
                            for item in data.get("formset-footnotes", [])
                            if not item.get("DELETE")
                        ],
                        # condition_sentence here, or handle separately and duty_sentence after?
                        "duty_sentence": commodity_data["duties"],
                    }

                    measures_data.append(measure_data)

        parser = DutySentenceParser.create(
            measure_start_date,
            component_output=MeasureConditionComponent,
        )

        created_measures = []

        for measure_data in measures_data:
            # creates measure in DB
            measure = measure_creation_pattern.create(**measure_data)
            self.create_measure_conditions(
                data,
                measure,
                measure_creation_pattern,
                parser,
            )

            created_measures.append(measure)

        return created_measures

    def create_measure_conditions(
        self,
        data: Dict,
        measure: Measure,
        measure_creation_pattern: MeasureCreationPattern,
        parser: DutySentenceParser,
    ) -> None:
        """
        Create's measure conditions, components, and their corresponding negative actions
        Args:
            data: object with the form wizards data
            measure: Current created measure
            measure_creation_pattern: MeasureCreationPattern
            parser: DutySentenceParser
        Returns:
            None
        """
        # component number not tied to position in formset as negative conditions are auto generated
        component_sequence_number = 1
        for index, condition_data in enumerate(
            data.get("formset-conditions", []),
        ):
            if not condition_data.get("DELETE"):
                # creates a list of tuples with condition and action code
                # this will be used to create the corresponding negative action
                measure_creation_pattern.create_condition_and_components(
                    condition_data,
                    component_sequence_number,
                    measure,
                    parser,
                    self.workbasket,
                )

                # set next code unless last item set None
                next_condition_code = (
                    data["formset-conditions"][index + 1]["condition_code"]
                    if (index + 1 < len(data["formset-conditions"]))
                    else None
                )
                # corresponding negative action to the postive one. None if the action code has no pair
                action_pair = MeasureActionPair.objects.filter(
                    positive_action__code=condition_data.get("action").code,
                ).first()

                negative_action = None

                if action_pair:
                    negative_action = action_pair.negative_action
                elif (
                    measure.measure_type
                    in measure_creation_pattern.autonomous_tariff_suspension_use_measure_types
                    and condition_data.get("action").code == "01"
                ):
                    """If measure type is an automatic suspension and an action
                    code 01 is selected then the negative action of code 07
                    (measure not applicable)is used."""
                    negative_action = measure_creation_pattern.measure_not_applicable

                # if the next condition code is different create the negative action for the current condition
                # only create a negative action if the action has a negative pair
                if (
                    negative_action
                    and data["formset-conditions"][index]["condition_code"]
                    != next_condition_code
                ):
                    component_sequence_number += 1
                    measure_creation_pattern.create_condition_and_components(
                        {
                            "condition_code": condition_data.get("condition_code"),
                            "duty_amount": None,
                            "required_certificate": None,
                            # corresponding negative action to the postive one.
                            "action": negative_action,
                            "DELETE": False,
                        },
                        component_sequence_number,
                        measure,
                        parser,
                        self.workbasket,
                    )

            # deletes also increment or well did when using the enumerated index
            component_sequence_number += 1
