"""Provides a base model for all dataclasses used in the project."""
import types
from dataclasses import Field
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import is_dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import _GenericAlias
from typing import get_args


class ModelPostProcessor:
    """A post processor class for transforming dict inputs into nested
    dataclasses."""

    def _post_process_item(self, item: Any, dc: dataclass) -> Any:
        """Returns a dataclass instance of a dict."""
        if isinstance(item, dict):
            item = dc(**item)
        return item

    def _post_process_value(self, value: Any, dc: dataclass, attr: str) -> None:
        """Converts dataclass-type attribute value to a dataclass."""
        value = self._post_process_item(value, dc)
        setattr(self.model, attr, value)

    def _post_process_list(self, values: List[Any], dc: dataclass, attr: str) -> None:
        """Returns the elements of a List-type attribute value as
        dataclasses."""
        new_values = []

        for value in values:
            value = self._post_process_item(value, dc)
            new_values.append(value)
        setattr(self.model, attr, new_values)

    def _post_process_tuple(self, values: Tuple, args: List[Any], attr: str) -> None:
        """Converts a relevant elements of a Tuple-type attribute value to
        dataclasses."""
        new_values = []

        for i, arg in enumerate(args):
            if is_dataclass(arg):
                value = self._post_process_item(values[i], arg)
            new_values.append(value)

        setattr(self.model, attr, tuple(new_values))

    def _post_process_dict(
        self,
        values: Dict[str, Any],
        dc: dataclass,
        attr: str,
    ) -> None:
        """Converts the values of a Dict-type attribute value to dataclasses."""
        new_values = {}

        for key, value in values.items():
            new_values[key] = self._post_process_item(value, dc)

        setattr(self.model, attr, new_values)

    def _post_process_union(self, value: Any, args: List[Any], attr) -> None:
        """Converts the value of a Union-type attribute value to a dataclass, if
        applicable."""
        dc_args = [arg for arg in args if is_dataclass(arg)]

        if isinstance(value, dict):
            for dc in dc_args:
                try:
                    value = self._post_process_item(value, dc)
                    setattr(self.model, attr, value)
                    return
                except TypeError:
                    continue

    def __init__(self, model: dataclass):
        """Instantiates the processor."""
        self.model = model

    def post_process(self):
        """Triggers post-processes on all fields in the model."""
        for dc_field in fields(self.model):
            self.post_process_field(dc_field)

    def post_process_field(self, dc_field: Field):
        """Post-processes an individual field in the model."""
        value = getattr(self.model, dc_field.name)

        if is_dataclass(dc_field.type):
            self._post_process_value(value, dc_field.type, dc_field.name)

        try:
            mro = dc_field.type.__class__.__mro__
        except AttributeError:
            return

        if _GenericAlias not in mro:
            return

        args = get_args(dc_field.type)
        has_dcs = sum([is_dataclass(arg) for arg in args]) != 0

        if type(dc_field.type) == _GenericAlias:
            if has_dcs:
                if isinstance(value, list):
                    self._post_process_list(value, args[0], dc_field.name)

                if isinstance(value, tuple):
                    self._post_process_tuple(value, args, dc_field.name)

                if isinstance(value, dict):
                    self._post_process_dict(value, args[1], dc_field.name)

        # if type(dc_field.type) == _UnionGenericAlias:
        #     self._post_process_union(value, args, dc_field.name)


@dataclass
class BaseModel:
    """Base class for all dataclass based models in the lab."""

    def __post_init__(self):
        """Postprocess the fields of the model."""
        processor = ModelPostProcessor(self)
        processor.post_process()

    @property
    def __identifier__(self):
        """Returns a unique identifier of the model class."""
        return f"{__name__}.{self.__class__.__name__}"

    @classmethod
    def __help__(cls):
        """Returns a dictionary with names and docs for methods attached to the
        dataclass."""
        help_types = (types.FunctionType, types.MethodType)

        d = {}

        for attr_name in dir(cls):
            if attr_name[:1] == "_":
                continue

            attr = getattr(cls, attr_name)
            attr_type = type(attr)

            if attr_type not in help_types:
                continue

            attr_doc = (attr.__doc__ or "").strip()

            d[attr_name] = attr_doc

        return d

    def _get_repr(self, extra: str) -> str:
        """Returns a string representation of the model instance."""
        return f"{self.__identifier__}: {extra}"
