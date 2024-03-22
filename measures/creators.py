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
    """Utility class used to create measures from measures wizard accumulated
    data."""

    workbasket: WorkBasket
    """The workbasket with which created measures will be associated."""

    data: Dict
    """Validated, cleaned and accumulated data created by the Form instances of
    `MeasureCreateWizard`."""

    def __init__(self, workbasket: WorkBasket, data: Dict):
        self.workbasket = workbasket
        self.data = data

    @property
    def measure_start_date(self):
        """Returns the start date, extracted from `MeasuresCreator.data`, that
        is used when creating Measure instances."""

        return self.data["valid_between"].lower

    @property
    def expected_measures_count(self) -> int:
        """Return the expected number of measures that are to be created from
        `MeasuresCreator.data` and associated with
        `MeasuresCreator.workbasket`."""

        return len(self.get_measures_data())

    def get_measures_data(self) -> List:
        """Get the measures data used to create Measure instances."""

        measures_data = []

        for commodity_data in self.data.get("formset-commodities", []):
            if not commodity_data.get("DELETE"):
                for geo_data in self.data["geo_areas_and_exclusions"]:
                    measure_data = {
                        "measure_type": self.data["measure_type"],
                        "geographical_area": geo_data["geo_area"],
                        "exclusions": geo_data.get("exclusions", []),
                        "goods_nomenclature": commodity_data["commodity"],
                        "additional_code": self.data["additional_code"],
                        "order_number": self.data["order_number"],
                        "validity_start": self.measure_start_date,
                        "validity_end": self.data["valid_between"].upper,
                        "footnotes": [
                            item["footnote"]
                            for item in self.data.get("formset-footnotes", [])
                            if not item.get("DELETE")
                        ],
                        # condition_sentence here, or handle separately and duty_sentence after?
                        "duty_sentence": commodity_data["duties"],
                    }

                    measures_data.append(measure_data)

        return measures_data

    @atomic
    def create_measures(self) -> List[Measure]:
        """
        Returns a list of the created measures.

        `data` must be a dictionary
        of the accumulated cleaned / validated data created from the
        `MeasureCreateWizard`.
        """

        measure_creation_pattern = MeasureCreationPattern(
            workbasket=self.workbasket,
            base_date=self.measure_start_date,
            defaults={
                "generating_regulation": self.data["generating_regulation"],
            },
        )
        measures_data = self.get_measures_data()
        parser = DutySentenceParser.create(
            self.measure_start_date,
            component_output=MeasureConditionComponent,
        )

        created_measures = []

        for measure_data in measures_data:


            # TODO: Remove when done.
            import logging
            import time

            logger = logging.getLogger(__name__)

            sleep_time = 15
            logger.info("*** Sleeping for {sleep_time} seconds...")
            time.sleep(sleep_time)
            logger.info("*** Awake!")


            # creates measure in DB
            measure = measure_creation_pattern.create(**measure_data)
            self.create_measure_conditions(
                measure,
                measure_creation_pattern,
                parser,
            )
            created_measures.append(measure)

        return created_measures

    def create_measure_conditions(
        self,
        measure: Measure,
        measure_creation_pattern: MeasureCreationPattern,
        parser: DutySentenceParser,
    ) -> None:
        """
        Create's measure conditions, components, and their corresponding negative actions
        Args:
            measure: Current created measure
            measure_creation_pattern: MeasureCreationPattern
            parser: DutySentenceParser
        Returns:
            None
        """

        # component number not tied to position in formset as negative conditions are auto generated
        component_sequence_number = 1
        for index, condition_data in enumerate(
            self.data.get("formset-conditions", []),
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
                    self.data["formset-conditions"][index + 1]["condition_code"]
                    if (index + 1 < len(self.data["formset-conditions"]))
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
                    and self.data["formset-conditions"][index]["condition_code"]
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
