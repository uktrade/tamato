from dataclasses import dataclass
from typing import Tuple
from typing import Union

from common.models import TrackedModel
from common.models.meta.base import BaseModel
from common.models.transactions import Transaction
from common.validators import UpdateType

DATE_FORMAT = "%Y-%m-%d"

TRACKEDMODEL_IDENTIFIER_KEYS = {
    "Additional_Codes.AdditionalCode": "code",
    "Commodities.GoodsNomenclature": "item_id",
    "Commodities.GoodsNomenclatureIndentNode": "depth",
    "Geo_Areas.GeographicalArea": "area_id",
    "Measures.MeasureAction": "code",
    "Measures.MeasureConditionCode": "code",
    "Measures.MeasurementUnit": "code",
    "Measures.MeasurementUnitQualifier": "code",
    "Measures.MonetaryUnit": "code",
    "Quotas.QuotaOrderNumber": "order_number",
    "Regulations.Group": "group_id",
}

TRACKEDMODEL_IDENTIFIER_FALLBACK_KEY = "sid"
TRACKEDMODEL_PRIMARY_KEY = "id"


@dataclass
class TrackedModelWrapper(BaseModel):
    """Provides a wrapper for TrackedModel with a range of convenience
    methods."""

    obj: TrackedModel

    @property
    def model(self) -> str:
        """Returns the model class for the wrapped object."""
        return self.obj._meta.model

    @property
    def record_type(self) -> str:
        """Returns the Taric3 record type for the wrapped model."""
        try:
            record_type = self.obj.record_code[0]
        except AttributeError:
            record_type = "0"

        return record_type

    @property
    def identifier_key(self) -> str:
        """
        Returns the preferred key name for the model, if defined.

        Many models in the Taric specification have a field
        that contains the identifier or descriptor for each object.
        Examples include:
        - item_id for GoodsNomenclature
        - area_id for GeographicalArea
        - sid for Measure (among others)
        - order_number for QuotaOrderNumber
        - code for MeasurementUnit (among others)

        This method will return the preferred key name
        where it has been specified, otherwise the primary key name.
        """
        key = TRACKEDMODEL_IDENTIFIER_KEYS.get(self.identifier)

        if key is None:
            model_field_names = self.obj._meta.fields

            if TRACKEDMODEL_IDENTIFIER_FALLBACK_KEY in model_field_names:
                key = TRACKEDMODEL_IDENTIFIER_FALLBACK_KEY
            else:
                key = TRACKEDMODEL_PRIMARY_KEY

        return key

    @property
    def identifier(self) -> Union[str, int]:
        """Returns the object identifier which is the value of the identifier
        field."""
        return getattr(self.obj, self.identifier_key)

    @property
    def envelope(self) -> str:
        """
        Returns the envelope with which the record was added.

        TODO: Apply a more robust logic to identifying the envelope.
        """
        workbasket = self.obj.transaction.workbasket
        envelope = workbasket.title.rsplit(" ", 1)[1]
        return envelope

    @property
    def validity(self) -> str:
        """
        Returns the validity period of the object.

        This method acts as a facade - some models set the vallidity
        under the valid_between field, others use a start_date field, etc.
        """
        try:
            v = self.obj.valid_between

            return " - ".join(
                (
                    v.lower.strftime(DATE_FORMAT),
                    "inf" if v.upper is None else v.upper.strftime(DATE_FORMAT),
                ),
            )
        except self.model.DoesNotExist:
            try:
                validity_start = self.obj.validity_start
                return f"{validity_start.strftime(DATE_FORMAT)} - inf"
            except self.model.DoesNotExist:
                return "n/a"

    @property
    def version(self) -> int:
        """
        Returns the version of the object.

        TrackedModel objects support version control.
        The version_group field holds pointers
        to all prior and current versions of a Taric record.

        The versions are ordered based on transaction id.
        This method returns the version number of the object
        based on the place of its transaction id
        in the version transaction ids sequence.
        """
        ids = self._get_transaction_ids()
        version = ids.index(self.obj.transaction.id) + 1
        return version

    @property
    def update_type(self) -> int:
        """Returns the UpdateType of the Taric record.""" ""
        return UpdateType(self.obj.update_type)

    @property
    def current_version(self) -> int:
        """Returns the current version of the Taric record."""
        return self.obj.version_group.versions.count()

    @property
    def latest_update_type(self) -> int:
        """Returns the update type of the current version of the Taric
        record."""
        return UpdateType(self.obj.current_version.update_type)

    @property
    def is_current_version(self) -> bool:
        """Returns True if this is the current version of the Taric record."""
        return self.obj == self.obj.current_version

    @property
    def label(self) -> str:
        """Returns a default node label for the record (e.g. for use in
        visualizations)."""
        app_name = self.obj._meta.app_config.verbose_name
        model_name = self.obj._meta.model.__name__

        return (
            f"{app_name}.{model_name}|{self.identifier_key}|{self.identifier}|"
            f"{self.envelope}|{self.validity}|{self.record_type}"
        )

    def get_current_version_as_of_transaction(self, transaction: Transaction) -> int:
        """Returns the current version of the record as of a given
        transaction."""
        return self.get_current_version_as_of_transaction_id(transaction.id)

    def is_current_as_of_transaction(self, transaction: Transaction) -> bool:
        """Returns True if this is the current version of the record as of a
        given transaction."""
        return self.is_current_as_of_transaction_id(transaction.id)

    def get_current_version_as_of_transaction_id(
        self,
        transaction_id: int = None,
    ) -> int:
        """Returns the current version of the record as of a given transaction
        id."""
        if transaction_id is None:
            return self.current_version

        ids = self._get_transaction_ids()
        return len([tid for tid in ids if tid <= transaction_id])

    def is_current_as_of_transaction_id(self, transaction_id: int = None) -> bool:
        """Returns True if this is the current version of the record as of a
        given transaction id."""
        if transaction_id is None:
            return self.is_current_version

        current_version = self.get_current_version_as_of_transaction_id(transaction_id)
        return self.version == current_version

    def _get_transaction_ids(self) -> Tuple[int]:
        """Returns the id-s of all transactions in the version group of the
        record."""
        transaction_ids = self.obj.version_group.versions.values_list(
            "transaction_id",
            flat=True,
        )
        return tuple(transaction_ids)
