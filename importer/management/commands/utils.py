import logging
import re
from datetime import datetime
from datetime import timedelta
from itertools import combinations
from typing import Any
from typing import Callable
from typing import cast
from typing import Dict
from typing import Generic
from typing import IO
from typing import Iterable
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import TypeVar
from typing import Union

from django.template.loader import render_to_string

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from measures.models import MeasureType

Row = TypeVar("Row")
NewRow = TypeVar("NewRow")
OldRow = TypeVar("OldRow")
ItemIdGetter = Callable[[Row], GoodsNomenclature]

logger = logging.getLogger(__name__)


def maybe_min(*objs: Optional[TypeVar("T")]) -> Optional[TypeVar("T")]:
    present = [d for d in objs if d is not None]
    if any(present):
        return min(present)
    else:
        return None


def blank(value: Any, convert: Callable[[Any], TypeVar("T")]) -> Optional[TypeVar("T")]:
    return None if value == "" else convert(value)


def col(label: str) -> int:
    """Return the correct index given an Excel column letter."""
    assert len(label) == 1
    return ord(label) - ord("A")


class NomenclatureTreeCollector(Generic[Row]):
    """Consumes rows until the passed row no longer
    links to a child commodity code of the first row."""

    def __init__(self, key: ItemIdGetter, date: datetime) -> None:
        self.reset()
        self.key = key
        self.date = date

    def reset(self) -> None:
        self.buffer = cast(List[Row], [])
        self.subtree = None
        self.prefix = None

    def maybe_push(self, row: Row) -> bool:
        """Works out whether the passed row links to a commodity code
        that is within the current tree of the others. Returns a bool
        to represent this. Only pushes the row to the buffer if True."""
        row_key = self.key(row)

        if self.prefix is None:
            descendants = row_key.indents.as_at(self.date).get().get_descendants()
            self.prefix = row_key
            self.subtree = list(
                map(lambda r: r.indented_goods_nomenclature, descendants)
            )

        if row_key == self.prefix or row_key in self.subtree:
            self.buffer.append(row)
            return True
        else:
            return False


class MeasureTypeSlicer(Generic[OldRow, NewRow]):
    """Detect which measure types are in the old rows and if many
    measure types are present, generate new measures for each old row.
    If only one measure type is present, generate one measure for it.
    We may have duplicate entries due to Entry Price System but
    we only want one new measure per item id, hence use of sets."""

    def __init__(
        self,
        get_old_measure_type: Callable[[OldRow], MeasureType],
        get_goods_nomenclature: Callable[[Union[OldRow, NewRow]], GoodsNomenclature],
    ) -> None:
        self.get_old_measure_type = get_old_measure_type
        self.get_goods_nomenclature = get_goods_nomenclature

    def sliced_new_rows(
        self, old_rows: List[OldRow], new_rows: List[NewRow]
    ) -> Iterable[Tuple[MeasureType, NewRow, GoodsNomenclature]]:
        measure_types = set(self.get_old_measure_type(row) for row in old_rows)
        item_ids = cast(Dict[MeasureType, Set[GoodsNomenclature]], {})
        for measure_type in measure_types:
            item_ids[measure_type] = set(
                self.get_goods_nomenclature(r)
                for r in old_rows
                if self.get_old_measure_type(r) == measure_type
            )

        # We should not have the same item ID appearing in two sets
        for a, b in combinations(item_ids.values(), 2):
            assert a.isdisjoint(b), f"Repeated comm code: {a} and {b}"

        num_ids = sum(len(item_ids[measure_type]) for measure_type in measure_types)
        single_type = max(item_ids.keys(), key=lambda k: len(item_ids[k]))
        if len(item_ids[single_type]) == num_ids:
            # All the old rows are of a single measure type
            # Just create the new rows as desired
            for measure_type in (t for t in measure_types if t != single_type):
                assert len(item_ids[measure_type]) == 0

            for row in new_rows:
                yield single_type, row, self.get_goods_nomenclature(row)
        else:
            # There is a split of measure types across the old rows
            # Mirror the split in the new measures by using the old item ids
            parent_new = new_rows[0]
            if parent_new is not None:
                for measure_type in measure_types:
                    for old_gn in item_ids[measure_type]:
                        matching_new = next(
                            (
                                r
                                for r in new_rows
                                if self.get_goods_nomenclature(r) == old_gn
                            ),
                            parent_new,
                        )
                        yield measure_type, matching_new, old_gn
            else:
                assert len(new_rows) == 0


class SeasonalRateParser:
    SEASONAL_RATE = re.compile(r"([\d\.]+%) \((\d\d [A-Z]{3}) - (\d\d [A-Z]{3})\)")

    def __init__(self, base_date: datetime, timezone) -> None:
        assert base_date.day == 1
        assert base_date.month == 1
        self.base = base_date
        self.timezone = timezone

    def detect_seasonal_rates(self, duty_exp: str) -> Iterable:
        if SeasonalRateParser.SEASONAL_RATE.search(duty_exp):
            for match in SeasonalRateParser.SEASONAL_RATE.finditer(duty_exp):
                rate, start, end = match.groups()
                validity_start = self.timezone.localize(
                    datetime.strptime(start, r"%d %b")
                )
                validity_end = self.timezone.localize(datetime.strptime(end, r"%d %b"))
                if validity_start.month > validity_end.month:
                    # This straddles a year boundary so
                    # we need to make one measure for BREXIT to end
                    # and then another for start to BREXIT+1
                    yield (rate, self.base, validity_end.replace(year=self.base.year))
                    yield (
                        rate,
                        validity_start.replace(year=self.base.year),
                        self.base.replace(year=self.base.year + 1) + timedelta(days=-1),
                    )
                else:
                    # Both months are in one year, hence make them 2021
                    yield (
                        rate,
                        validity_start.replace(year=self.base.year),
                        validity_end.replace(year=self.base.year),
                    )
        else:
            # Non-seasonal rate!
            yield (duty_exp, self.base, None)


Counter = Callable[[], int]


class EnvelopeSerializer:
    """A performant envelope serializer. It does not need to keep
    everything in memory to generate an envelope, instead using
    a streaming approach. Also keeps track of transaction and message IDs."""

    def __init__(
        self,
        output: IO,
        envelope_id: int,
        transaction_counter: Counter = counter_generator(),
        message_counter: Counter = counter_generator(),
    ) -> None:
        self.output = output
        self.transaction_counter = transaction_counter
        self.message_counter = message_counter
        self.envelope_id = envelope_id
        self.serializer = TrackedModelSerializer(context={"format": "xml"})

    def __enter__(self):
        self.output.write(
            render_to_string(
                template_name="common/taric/start_envelope.xml",
                context={"envelope_id": self.envelope_id},
            )
        )
        return self

    def __exit__(self, *_) -> None:
        self.output.write(
            render_to_string(template_name="common/taric/end_envelope.xml")
        )

    def render_transaction(self, models: List[TrackedModel]) -> None:
        if any(models):
            self.output.write(
                render_to_string(
                    template_name="workbaskets/taric/transaction.xml",
                    context={
                        "tracked_models": map(
                            self.serializer.to_representation, models
                        ),
                        "transaction_id": self.transaction_counter(),
                        "counter_generator": counter_generator,
                        "message_counter": self.message_counter,
                    },
                )
            )
