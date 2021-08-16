"""Provides dataclasses and config classes for xml elements and the taric schema."""

from collections.abc import Iterator
from dataclasses import dataclass, field
import re
from typing import Dict, TypeVar, Union
import xml.etree.ElementTree as ET

from common.xml.namespaces import SEED_MESSAGE
from common.xml.namespaces import nsmap

TTag = TypeVar("TTag", bound="Tag")

RE_PATTERN_TEST = re.compile(r"[^A-Za-z\.\_]")


@dataclass
class Tag:
    """A dataclass for xml element tags."""
    name: str
    prefix: str = field(default=SEED_MESSAGE)
    nsmap: Dict[str, str] = field(default_factory=lambda: nsmap)

    @property
    def namespace(self) -> str:
        """Returns the namespace for the tag."""
        return self.nsmap.get(self.prefix)

    @property
    def qualified_name(self) -> str:
        """Returns a fully qualified element tag."""
        ns = self.namespace

        if ns is None:
            return self.name

        return f"{{{ns}}}{self.name}"

    @property
    def prefixed_name(self) -> str:
        """Returns the prefixed element tag."""
        if self.prefix is None:
            return self.name

        return f"{self.prefix}:{self.name}"

    @property
    def is_pattern(self) -> bool:
        """Returns true if the tag name is a regex pattern."""
        return RE_PATTERN_TEST.match(self.name) is not None

    @property
    def pattern(self):
        """Returns a compiled regex pattern """
        if self.is_pattern is False:
            return self.qualified_name

        return re.compile(re.escape(f"{{{self.namespace}}}") + self.name)

    def iter(self, parent: ET.Element) -> Iterator[ET.Element]:
        """Returns an iterator of descendants of the parent matching this tag's name."""
        qname = self.qualified_name
        return (el for el in parent.iter() if el.tag == qname)

    def first(self, parent: ET.Element) -> ET.Element:
        """Returns the first descendant of the parent matching this tag's name."""
        try:
            return next(self.iter(parent))
        except StopIteration:
            return

    def __eq__(self, tag: Union[str, TTag]) -> bool:
        """Returns true if the qualified names of the two tags are equal."""
        is_pattern = self.is_pattern

        if isinstance(tag, Tag):
            tag_qualified_name = tag.qualified_name
        else:
            tag_qualified_name = tag

        if is_pattern is True:
            return self.pattern.match(tag_qualified_name)
        else:
            return self.qualified_name == tag_qualified_name

    def __str__(self):
        """Returns a string representation of the tag."""
        return self.qualified_name
