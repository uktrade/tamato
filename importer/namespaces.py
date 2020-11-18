import re
from typing import Tuple
from typing import TypeVar
from typing import Union


Namespace = Tuple[str, str]

ENVELOPE = "env"
SEED_MESSAGE = "ns2"  # this is the prefix used in the seed file
TARIC_MESSAGE = "oub"  # this is the prefix used in EU TARIC3 xml files

nsmap = {
    ENVELOPE: "urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0",
    SEED_MESSAGE: "urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0",
    TARIC_MESSAGE: "urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0",
}

T = TypeVar("T", bound="Tag")


class Tag:
    """An XML element tag with a namespace mapping prefix."""

    def __init__(self, name, prefix=SEED_MESSAGE):
        self.name = name
        self.prefix = prefix

    def __eq__(self, other: Union[str, T]) -> bool:
        if isinstance(other, Tag):
            return str(self) == str(other)

        return str(self) == other

    def __str__(self):
        return f"{{{nsmap[self.prefix]}}}{self.name}"


class RegexTag(Tag):
    def __init__(self, pattern, prefix=SEED_MESSAGE):
        super().__init__(pattern)
        self.name = pattern
        self.pattern = re.compile(re.escape(f"{{{nsmap[prefix]}}}") + pattern)

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.pattern.match(str(other))
        return self.pattern.match(other)
