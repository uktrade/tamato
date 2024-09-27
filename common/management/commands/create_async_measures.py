from datetime import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.transaction import atomic

from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.models import GoodsNomenclatureIndent
from commodities.models import GoodsNomenclatureOrigin
from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.validators import AreaCode
from measures.models import MeasureType
from measures.models.bulk_processing import MeasuresBulkCreator
from regulations.models import Regulation
from workbaskets.models import WorkBasket

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Creates new measures asynchronously in a newly created workbasket for "
        "perfomance testing purposes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user_name",
            required=True,
            help=(
                "Username of the person performing the test who will be the "
                "author of the workbasket."
            ),
        )
        parser.add_argument(
            "--wb-title",
            required=False,
            help=(
                "Title given to the workbasket being created for the "
                "performance test. If none is provided then a system timestamp "
                "will be used to form part of a unique title."
            ),
        )
        parser.add_argument(
            "--count",
            required=False,
            type=int,
            default=99,
            help=(
                "Number of measures to create (1-99). If no count is "
                "specified, then a default count of 99 is used."
            ),
        )

    def handle(self, *args, **options):
        username = options["user_name"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        count = options["count"]
        if count < 1:
            raise CommandError("count must be greater than zero.")

        title = self.get_title(options["wb_title"])
        workbasket = self.create_workbasket(user, title)
        measure_type = self.get_measure_type()
        start_date = self.get_start_date()

        commodities = self.create_commodities(
            workbasket,
            start_date,
            count,
        )
        geo_area = self.create_country(workbasket, start_date)

        form_data = self.generate_form_data(
            measure_type,
            start_date,
            commodities,
            geo_area,
        )
        form_kwargs = self.generate_form_kwargs(
            measure_type,
            start_date,
            len(commodities),
        )

        measures_bulk_creator = MeasuresBulkCreator.objects.create(
            form_data=form_data,
            form_kwargs=form_kwargs,
            workbasket=workbasket,
            user=user,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created MeasuresBulkCreator: ID "
                f"{measures_bulk_creator.id} - generating {count} measure(s).",
            ),
        )

        measures_bulk_creator.schedule_task()

    def create_workbasket(self, user, title: str = None) -> WorkBasket:
        workbasket = WorkBasket.objects.create(
            title=title,
            reason="Created for performance testing purposes.",
            author=user,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created worbasket: {workbasket} - {workbasket.title}",
            ),
        )
        return workbasket

    def get_title(self, title: str = None) -> str:
        if title:
            return title
        now = datetime.now().replace(microsecond=0).isoformat(" ")
        return f"Perf test {now}"

    def generate_form_data(
        self,
        measure_type: MeasureType,
        start_date: datetime,
        commodities: list[GoodsNomenclature],
        geo_area: GeographicalArea,
    ) -> dict:
        return {
            "footnotes": self.get_footnotes(),
            "conditions": self.get_conditions(),
            "commodities": self.get_commodities_and_duties(commodities),
            "regulation_id": self.get_regulation(),
            "additional_code": self.get_additional_code(),
            "measure_details": self.get_measure_details(
                measure_type,
                start_date,
                len(commodities),
            ),
            "geographical_area": self.get_geographical_areas(geo_area),
            "quota_order_number": self.get_order_number(),
        }

    def generate_form_kwargs(
        self,
        measure_type: MeasureType,
        start_date: datetime,
        commodity_count: int,
    ):
        return {
            "footnotes": {},
            "conditions": {
                "form_kwargs": {
                    "measure_type_pk": measure_type.pk,
                    "measure_start_date": start_date.strftime("%Y-%m-%d"),
                },
            },
            "commodities": {
                "form_kwargs": {
                    "measure_type_pk": measure_type.pk,
                },
                "measure_start_date": start_date.strftime("%Y-%m-%d"),
                "min_commodity_count": commodity_count,
            },
            "regulation_id": {},
            "additional_code": {},
            "measure_details": {},
            "geographical_area": {},
            "quota_order_number": {},
        }

    def get_measure_type(self) -> MeasureType:
        return MeasureType.objects.filter(sid=142).last()

    def get_start_date(self) -> datetime:
        return datetime.today()

    def get_footnotes(self) -> dict:
        return {}

    def get_conditions(self) -> dict:
        return {}

    def create_country(
        self,
        workbasket: WorkBasket,
        start_date: datetime,
    ) -> GeographicalArea:
        return GeographicalArea.create(
            area_code=AreaCode.COUNTRY,
            area_id="OO",
            description="Country created for perfomance testing purposes.",
            valid_between=TaricDateRange(lower=start_date.date(), upper=None),
            update_type=UpdateType.CREATE,
            transaction=workbasket.new_transaction(),
        )

    def create_commodities(
        self,
        workbasket: WorkBasket,
        start_date: datetime,
        commodities_count: int,
    ) -> list[GoodsNomenclature]:
        """
        Create and return new goods in workbasket.

        Note that a new chapter-level goods item will be created in addition to
        the goods returned by this function, adding one to the total created
        commodity count.
        """

        commodities = []

        # Create a new chapter-level commodity that can be used as the origin
        # for all new goods (start date must be at least the day before the
        # start date of the goods that use them).
        chapter_good = self.create_commodity(
            workbasket=workbasket,
            hs_chapter=99,
            taric_subheading=0,
            start_date=start_date - timedelta(days=1),
        )

        for i in range(1, commodities_count + 1):
            good = self.create_commodity(
                workbasket=workbasket,
                hs_chapter=99,
                taric_subheading=i,
                start_date=start_date,
                origin_good=chapter_good,
            )
            commodities.append(good)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {commodities_count + 1} new good(s).",
            ),
        )

        return commodities

    @atomic
    def create_commodity(
        self,
        workbasket: WorkBasket,
        hs_chapter: int,
        taric_subheading: int,
        start_date: datetime,
        origin_good: GoodsNomenclature = None,
    ) -> GoodsNomenclature:
        """
        Create and return a new commodity.

        If this is a new chapter-level
        commodity, then `origin_good` should be None, otherwise, `origin_good`
        should be a commodity higher in the goods hierarchy.
        """

        if hs_chapter > 99:
            raise Exception("hs_chapter must be 99 or less.")

        if taric_subheading > 99:
            raise Exception("hs_chapter must be 99 or less.")

        transaction = workbasket.new_transaction()
        common_kwargs = {
            "transaction": transaction,
            "update_type": UpdateType.CREATE.value,
        }

        good = GoodsNomenclature.objects.create(
            sid=900000 + taric_subheading,
            item_id=f"{hs_chapter:<06d}{taric_subheading:>04d}",
            suffix="80",
            statistical=False,
            valid_between=(start_date, None),
            **common_kwargs,
        )

        GoodsNomenclatureDescription.objects.create(
            sid=900000 + taric_subheading,
            described_goods_nomenclature=good,
            description=f"Performance test commodity {good.item_id}",
            validity_start=start_date,
            **common_kwargs,
        )

        GoodsNomenclatureIndent.objects.create(
            sid=900000 + taric_subheading,
            indent=0,
            indented_goods_nomenclature=good,
            validity_start=start_date,
            **common_kwargs,
        )

        if origin_good:
            GoodsNomenclatureOrigin.objects.create(
                new_goods_nomenclature=good,
                derived_from_goods_nomenclature=origin_good,
                **common_kwargs,
            )

        return good

    def get_commodities_and_duties(self, commodities: list[GoodsNomenclature]) -> dict:
        commodities_and_duties = {}
        for i, commodity in enumerate(commodities):
            commodities_and_duties[f"measure_commodities_duties_formset-{i}-duties"] = (
                "0%"
            )
            commodities_and_duties[
                f"measure_commodities_duties_formset-{i}-commodity"
            ] = f"{commodity.pk}"
        return commodities_and_duties

    def get_regulation(self) -> dict:
        regulation = Regulation.objects.filter(regulation_id="C2100001").last()
        return {
            "generating_regulation": str(regulation.pk),
        }

    def get_additional_code(self) -> dict:
        return {"additional_code": ""}

    def get_measure_details(self, measure_type, start_date, commodity_count) -> dict:
        return {
            "end_date_0": "",
            "end_date_1": "",
            "end_date_2": "",
            "measure_type": str(measure_type.pk),
            "start_date_0": start_date.day,
            "start_date_1": start_date.month,
            "start_date_2": start_date.year,
            "min_commodity_count": str(commodity_count),
        }

    def get_geographical_areas(self, geo_area: GeographicalArea) -> dict:
        return {
            "geographical_area-geo_area": "COUNTRY",
            "geographical_area-geographical_area_group": "",
            "country_region_formset-0-geographical_area_country_or_region": str(
                geo_area.pk,
            ),
        }

    def get_order_number(self) -> dict:
        return {"order_number": ""}
