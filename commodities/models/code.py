from dataclasses import dataclass


@dataclass(frozen=True)
class CommodityCode:
    """A dataclass for commodity codes with a range of convenience
    properties."""

    code: str

    @property
    def chapter(self) -> str:
        """Returns the HS chapter for the commodity code."""
        return self.code[:2]

    @property
    def heading(self) -> str:
        """Returns the HS heading for the commodity code."""
        return self.code[:4]

    @property
    def subheading(self) -> str:
        """Returns the HS subheading for the commodity code."""
        return self.code[:6]

    @property
    def cn_subheading(self) -> str:
        """Returns the CN subheading for the commodity code."""
        return self.code[:8]

    @property
    def dot_code(self) -> str:
        """Returns the commodity code in dot format."""
        code = self.code
        return f"{code[:4]}.{code[4:6]}.{code[6:8]}.{code[8:]}"

    @property
    def trimmed_dot_code(self) -> str:
        """Returns the commodity code in dot format, without trailing zero
        pairs."""
        parts = self.dot_code.split(".")

        for i, part in enumerate(parts[::-1]):
            if part != "00":
                return ".".join(parts[: len(parts) - i])

    @property
    def trimmed_code(self) -> str:
        """Returns the commodity code without trailing zero pairs."""
        return self.trimmed_dot_code.replace(".", "")

    @property
    def is_chapter(self) -> bool:
        """Returns true if the commodity code represents a HS chapter."""
        return self.trimmed_code.rstrip("0") == self.chapter

    @property
    def is_heading(self) -> bool:
        """Returns true if the commodity code represents a HS heading."""
        return self.trimmed_code == self.heading and not self.is_chapter

    @property
    def is_subheading(self) -> bool:
        """Returns true if the commodity code represents a HS subheading."""
        return self.trimmed_code == self.subheading

    @property
    def is_cn_subheading(self) -> bool:
        """Returns true if the commodity code represents a CN subheading."""
        return self.trimmed_code == self.cn_subheading

    @property
    def is_taric_subheading(self) -> bool:
        """Returns true if the commodity code represents a Taric subheading."""
        return self.trimmed_code == self.code

    @property
    def is_taric_code(self) -> bool:
        return self.code[8:] != "00"

    def __str__(self):
        """Returns a string representation of the dataclass instance."""
        return self.code
