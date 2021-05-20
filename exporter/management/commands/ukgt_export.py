"""
Command to output a "reference document"-style spreadsheet from current data.

Reference document sheets have the following requirements:

1. They are a list of all of the commodity codes alongside a the current value
   for a certain type of rate attached to that code. E.g. one reference document
   might show all the commodity codes alongside their current MFN rates.
2. If a rate is only available under authorised use, the rate is not shown and a
   note about authorised use is shown instead.
3. Ancestors of any code with a rate are also shown, but without any rate
   alongside them (because in principle their children have multiple rates).
4. Descendants of any code with a rate are not shown, because the rate cannot
   vary below them due to :class:`~measures.business_rules.ME32`.
5. The descriptions are indented with dashes up to the value of their current
   commodity code indent.
6. Commodity codes that are "intermediate lines" (i.e. suffix != 80) show their
   description but do not show their code.
"""

from datetime import date
from textwrap import dedent
from typing import Any
from typing import Optional

import xlsxwriter
from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from django.db.models.expressions import Case
from django.db.models.expressions import Col
from django.db.models.expressions import Expression
from django.db.models.expressions import F
from django.db.models.expressions import Func
from django.db.models.expressions import Value
from django.db.models.expressions import When
from django.db.models.fields import CharField
from django.db.models.fields import Field
from django.db.models.fields import TextField
from django.db.models.functions import Substr
from django.db.models.functions.text import Concat
from django.db.models.functions.text import Repeat
from django.db.models.lookups import StartsWith
from django.db.models.sql.where import WhereNode
from django_cte.cte import With

from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureIndentNode
from measures.models import Measure

AUTHORISED_USE_NOTE = (
    dedent(
        """
    Code reserved for authorised use; the duty rate is
    specified under regulations made under section 19 of
    the Taxation (Cross-border Trade) Act 2018
    """,
    )
    .replace("\n", " ")
    .strip()
)


class If(Case):
    """Convenience wrapper around Case/When."""

    def __init__(
        self,
        then: Any = None,
        otherwise: Any = Value(""),
        output_field: Optional[Field] = None,
        **tests: Any,
    ) -> None:
        super().__init__(
            When(
                **tests,
                then=then,
            ),
            default=otherwise,
            output_field=output_field,
        )


def format_commodity_code(field_name: str) -> Expression:
    """
    Output a field containing a 10 digit item id formatted with spaces between
    pairs of digits and trim off any trailing pairs that are just 00, except the
    first four digits which aren't modified.

        E.g. '2100000010' -> '2100 00 00 10'
             '2100010000' -> '2100 00 01'
             '2100000000' -> '2100'
    """

    return Func(
        Func(
            Value(" "),
            Substr(f"{field_name}__item_id", 1, 4),
            Substr(f"{field_name}__item_id", 5, 2),
            Substr(f"{field_name}__item_id", 7, 2),
            Substr(f"{field_name}__item_id", 9, 2),
            function="CONCAT_WS",
        ),
        Value("( 00)+$"),
        Value(""),
        function="REGEXP_REPLACE",
    )


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "output",
            type=str,
            nargs="?",
            default=f"UKGT-ref-doc-{date.today().isoformat()}.xlsx",
        )
        super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        """
        We are going to create three seperate tables as CTEs.

        1. A table of measures, including duty rates and comm code SIDs, that
           apply in this regime (e.g. 103 and 105).
        2. A table of the current commodity codes descriptions
        3. A table of current comm code paths, joined to #2
        4. A table of comm code paths, joined to #1 and #3, but filtered such
           that only paths that have measures on them are present
        5. The final query made out of #4 and #3, so that any path in #4 or that
           is a *prefix* of a path in #4 is present showing comm code, duty
           rate/AU, notes, and description, for all codes that have MFN rates or
           their ancestors
        """
        type_sids = ("103", "105")
        authorised_use_type_sids = ("105",)

        # A table of approved, live measures as of today. Include their duty
        # expression, except where the measure type denotes authorised use,
        # where instead we just print "AU".
        mfn_measures = With(
            Measure.objects.with_effective_valid_between()
            .with_duty_sentence()
            .latest_approved()
            .filter(
                db_effective_valid_between__contains=date.today(),
                measure_type__sid__in=type_sids,
            )
            .annotate(
                duty_expression=If(
                    measure_type__sid__in=authorised_use_type_sids,
                    then=Value("AU"),
                    otherwise=F("duty_sentence"),
                    output_field=CharField(),
                ),
                notes=If(
                    measure_type__sid__in=authorised_use_type_sids,
                    then=Value(AUTHORISED_USE_NOTE),
                    output_field=TextField(),
                ),
            ),
            name="mfn_measures",
        )

        # A table of approved, live indents as of today. We have to build a
        # table of these because the end dates are computed on demand and we
        # can't cause that to happen just with a foreign key relation. The order
        # seems to be very important for performance... I'm not quite sure why.
        indents_now = With(
            GoodsNomenclatureIndent.objects.with_end_date()
            .filter(valid_between__contains=date.today())
            .order_by(
                "indented_goods_nomenclature__item_id",
                "indented_goods_nomenclature__suffix",
            ),
            name="indents_now",
        )

        # A table of approved, live commodity code descriptions.
        descriptions = With(
            GoodsNomenclatureDescription.objects.latest_approved()
            .with_end_date()
            .as_at(date.today()),
            name="description",
        )

        # Now to join all of the tables together. We start with a table of
        # approved, live tree nodes, and join it to the indents table to filter
        # it down to only nodes that are attached to an approved, live indent.
        # Then we join that to the descriptions table to get the current
        # description.
        #
        # This gives us a table of all of the current commodity codes and most
        # importantly their paths. We also attach some other data we will need
        # later, such as the item id and suffix.
        current_codes = (
            descriptions.join(
                indents_now.join(
                    GoodsNomenclatureIndentNode.objects.filter(
                        valid_between__contains=date.today(),
                    ),
                    indent=indents_now.col.pk,
                ),
                indent__indented_goods_nomenclature=descriptions.col.described_goods_nomenclature_id,
            )
            .with_cte(indents_now)
            .with_cte(descriptions)
            .order_by(
                "indent__indented_goods_nomenclature__item_id",
                "indent__indented_goods_nomenclature__suffix",
            )
            .annotate(
                item_id=F("indent__indented_goods_nomenclature__item_id"),
                suffix=F("indent__indented_goods_nomenclature__suffix"),
                description=descriptions.col.description,
            )
        )

        # Now we join the measures table onto the current codes table which
        # leaves us with only the current commodity codes and their tree paths
        # that actually have an interesting measure defined on them.
        mfn_path_table = With(
            mfn_measures.join(
                current_codes,
                indent__indented_goods_nomenclature=mfn_measures.col.goods_nomenclature_id,
            )
            .with_cte(mfn_measures)
            .annotate(
                duty_expression=mfn_measures.col.duty_expression,
                notes=mfn_measures.col.notes,
            ),
            name="mfn_paths",
        )

        # What we want now is to find any commodity code that is an ancestor of
        # any of the codes in the previous table. We can do this by asking for
        # any tree path that is a prefix of any of the paths in our table.
        #
        # Unfortunately there is no easy way to express this join using the
        # highest-level Django API so we have to manually construct the join
        # using low-level components, and then attach it to the query.
        path = GoodsNomenclatureIndentNode._meta.get_field("path")
        q = WhereNode(
            children=[
                StartsWith(
                    Col(mfn_path_table.name, path),
                    Col(GoodsNomenclatureIndentNode._meta.db_table, path),
                ),
            ],
        )

        mfn_paths = current_codes.distinct()
        mfn_paths.query.add_extra(
            select=None,
            select_params=None,
            tables=[mfn_path_table.name],
            where=None,
            params=None,
            order_by=None,
        )
        mfn_paths.query.where.add(q, conn_type="AND")

        # We now have any code that has an interesting measure defined on it and
        # any ancestor of those codes, but not any descendants. All that is left
        # is to order the table correctly and format the output fields to be how
        # we want them.
        qs = (
            mfn_paths.with_cte(mfn_path_table)
            .order_by(
                "indent__indented_goods_nomenclature__item_id",
                "indent__indented_goods_nomenclature__suffix",
            )
            .annotate(
                # Commodity codes are only shown if they are not "intermediate".
                commodity_code=If(
                    indent__indented_goods_nomenclature__suffix="80",
                    then=format_commodity_code("indent__indented_goods_nomenclature"),
                ),
                # Only show the duty expression where the measure actually is,
                # not on ancestors.
                duty_expression=If(
                    path=mfn_path_table.col.path,
                    then=mfn_path_table.col.duty_expression,
                ),
                # As above with duty expressions, but for notes.
                notes=If(
                    path=mfn_path_table.col.path,
                    then=mfn_path_table.col.notes,
                ),
                # Pad the description out with dashes depending on the depth of
                # the code. The top two levels of the hierarchy are not
                # indented. Also replace any rogue HTML tags with newlines.
                description=Concat(
                    Repeat(Value("- "), F("depth") - 2),
                    Func(
                        descriptions.col.description,
                        Value("(<br>)+"),
                        Value("\n"),
                        function="REGEXP_REPLACE",
                    ),
                    output_field=TextField(),
                ),
            )
            .values("commodity_code", "duty_expression", "notes", "description")
        )

        with xlsxwriter.Workbook(options["output"]) as workbook:
            name = "UKGT Reference Document"
            sheet = workbook.add_worksheet(name=name)
            sheet.write_row(
                0,
                0,
                ["Commodity code", "Duty expression", "Notes", "Description"],
            )

            print("Querying... ", end="", flush=True)
            for row, object in enumerate(qs.iterator(), start=1):
                if row == 1:
                    print("done\nOutputting...", end="", flush=True)
                sheet.write_row(
                    row,
                    0,
                    [
                        object["commodity_code"],
                        object["duty_expression"],
                        object["notes"],
                        object["description"],
                    ],
                )
            print("done")
