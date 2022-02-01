from dataclasses import dataclass
from typing import Iterator
from typing import Type

from common.models.trackedmodel import TrackedModel
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.util import materialise_geo_area
from workbaskets.models import WorkBasket


@dataclass
class ExclusionCreationPattern:
    """
    A generic pattern for creating geographical area exclusions on either
    measures or quotas.

    Only countries or regions, and not groups, can be excluded. Exclusions can
    only be created against groups. When there is a need to exclude a whole
    group, this has to be implemented as exclusions for each individual member
    of that group.

    It is not possible to create exclusions that exist across membership changes
    – if members are added or removed during the period of the exclusion (as
    defined by the model we are excluding from), this is a business rule error.
    Instead, the model we are excluding from needs to be created more than once
    to cover the different membership lists.
    """

    exclusion_type: Type[TrackedModel]
    """
    The type of object that should be created to represent an exclusion.
    
    It is assumed that it takes two attributes: 
    
    1) the model to be excluded from (e.g. a measure)
    2) the geographical area to exclude, with the name
       `excluded_geographical_area`
    """

    excluded_from_name: str
    """The name of the attribute on the `exclusion_type` that holds the object
    we are excluding from (e.g. `modified_measure`)."""

    workbasket: WorkBasket

    def create(
        self,
        excluded_from: TrackedModel,
        geo_area: GeographicalArea,
    ) -> Iterator[TrackedModel]:
        """
        Returns an iterator of exclusions that have been created to represent
        excluding the passed geographical area from the other passed model.

        Exclusions are created within the same transaction as the model excluded
        from if it is in the same workbasket, else exclusions are creating in a
        single new transaction.
        """

        origins = materialise_geo_area(
            excluded_from.geographical_area,
            date=excluded_from.valid_between.lower,
            transaction=self.workbasket.current_transaction,
        )

        exclusions = materialise_geo_area(
            geo_area,
            date=excluded_from.valid_between.lower,
            transaction=self.workbasket.current_transaction,
        )

        if excluded_from.transaction.workbasket == self.workbasket:
            transaction = excluded_from.transaction
        else:
            transaction = self.workbasket.new_transaction()

        for exclusion in exclusions:
            assert (
                exclusion in origins
            ), f"{exclusion.area_id} not in {list(x.area_id for x in origins)}"
            yield self.exclusion_type.objects.create(
                **{self.excluded_from_name: excluded_from},
                excluded_geographical_area=exclusion,
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )
