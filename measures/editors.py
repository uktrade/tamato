from typing import Dict
from typing import List
from typing import Type

from django.db.transaction import atomic

from common.models.utils import override_current_transaction
from common.util import TaricDateRange
from common.validators import UpdateType
from measures import models as measure_models
from measures.util import update_measure_components
from measures.util import update_measure_condition_components
from measures.util import update_measure_excluded_geographical_areas
from measures.util import update_measure_footnote_associations
from workbaskets import models as workbasket_models


class MeasuresEditor:
    """Utility class used to edit measures from measures wizard accumulated
    data."""

    workbasket: Type["workbasket_models.WorkBasket"]
    """The workbasket with which created measures will be associated."""

    selected_measures: List
    """The measures in which the edits will apply to."""

    data: Dict
    """Validated, cleaned and accumulated data created by the Form instances of
    `MeasureEditWizard`."""

    def __init__(
        self,
        workbasket: Type["workbasket_models.WorkBasket"],
        selected_measures: List,
        data: Dict,
    ):
        self.workbasket = workbasket
        self.selected_measures = selected_measures
        self.data = data

    @atomic
    def edit_measures(self) -> List["measure_models.Measure"]:
        """
        Returns a list of the edited measures.

        `data` must be a dictionary
        of the accumulated cleaned / validated data created from the
        `MeasureEditWizard`.
        """

        with override_current_transaction(
            transaction=self.workbasket.current_transaction,
        ):
            new_start_date = self.data.get("start_date", None)
            new_end_date = self.data.get("end_date", False)
            new_quota_order_number = self.data.get("order_number", None)
            new_generating_regulation = self.data.get("generating_regulation", None)
            new_duties = self.data.get("duties", None)
            new_exclusions = [
                e["excluded_area"]
                for e in self.data.get("formset-geographical_area_exclusions", [])
            ]

            edited_measures = []

            if self.selected_measures:
                for measure in self.selected_measures:
                    new_measure = measure.new_version(
                        workbasket=self.workbasket,
                        update_type=UpdateType.UPDATE,
                        valid_between=TaricDateRange(
                            lower=(
                                new_start_date
                                if new_start_date
                                else measure.valid_between.lower
                            ),
                            upper=(
                                new_end_date
                                if new_end_date
                                else measure.valid_between.upper
                            ),
                        ),
                        order_number=(
                            new_quota_order_number
                            if new_quota_order_number
                            else measure.order_number
                        ),
                        generating_regulation=(
                            new_generating_regulation
                            if new_generating_regulation
                            else measure.generating_regulation
                        ),
                    )
                    update_measure_components(
                        measure=new_measure,
                        duties=new_duties,
                        workbasket=self.workbasket,
                    )
                    update_measure_condition_components(
                        measure=new_measure,
                        workbasket=self.workbasket,
                    )
                    update_measure_excluded_geographical_areas(
                        edited="geographical_area_exclusions"
                        in self.data.get("fields_to_edit", []),
                        measure=new_measure,
                        exclusions=new_exclusions,
                        workbasket=self.workbasket,
                    )
                    update_measure_footnote_associations(
                        measure=new_measure,
                        workbasket=self.workbasket,
                    )

                    edited_measures.append(new_measure.id)

            return edited_measures
