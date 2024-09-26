from datetime import datetime
from time import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from commodities.models import GoodsNomenclature
from measures.models import MeasureType
from measures.models.bulk_processing import MeasuresBulkCreator
from regulations.models import Regulation
from workbaskets.models import WorkBasket

User = get_user_model()


class Command(BaseCommand):
    help = "Creates new measures in a newly created workbasket asynchronously for perfomance testing purposes."

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
            "--measures-count",
            required=False,
            type=int,
            default=2,
            help="Number of measures to create (1-99).",
        )

    def handle(self, *args, **options):
        username = options["user_name"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        try:
            wb_title = (
                options["wb_title"]
                if options["wb_title"]
                else f"Perf test {str(time()).split(".")[0]}"
            )
            workbasket = WorkBasket.objects.create(
                title=wb_title,
                reason="Created for performance testing purposes.",
                author=user,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created worbasket: {workbasket}"),
            )
        except Exception as e:
            raise CommandError(f"Error creating workbasket: {str(e)}")

        measure_type = self.get_measure_type()
        start_date = self.get_start_date()
        commodity_count = options["measures_count"]

        form_data = self.generate_form_data(measure_type, start_date, commodity_count)
        form_kwargs = self.generate_form_kwargs(
            measure_type,
            start_date,
            commodity_count,
        )

        try:
            measures_bulk_creator = MeasuresBulkCreator.objects.create(
                form_data=form_data,
                form_kwargs=form_kwargs,
                workbasket=workbasket,
                user=user,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created MeasuresBulkCreator: ID {measures_bulk_creator.id}",
                ),
            )
        except Exception as e:
            raise CommandError(f"Error creating MeasuresBulkCreator: {str(e)}")

        measures_bulk_creator.schedule_task()

    def generate_form_data(self, measure_type, start_date, commodity_count):
        return {
            "footnotes": self.get_footnotes(),
            "conditions": self.get_conditions(),
            "commodities": self.get_commodities_and_duties(commodity_count),
            "regulation_id": self.get_regulation(),
            "additional_code": self.get_additional_code(),
            "measure_details": self.get_measure_details(
                measure_type,
                start_date,
                commodity_count,
            ),
            "geographical_area": self.get_geographical_areas(),
            "quota_order_number": self.get_order_number(),
        }

    def generate_form_kwargs(self, measure_type, start_date, commodity_count):
        return {
            "footnotes": {},
            "conditions": {
                "form_kwargs": {
                    "measure_type_pk": measure_type,
                    "measure_start_date": start_date.strftime("%Y-%m-%d"),
                },
            },
            "commodities": {
                "form_kwargs": {
                    "measure_type_pk": measure_type,
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

    def get_measure_type(self) -> int:
        return MeasureType.objects.filter(sid=142).last().pk

    def get_start_date(self) -> datetime:
        return datetime.today()

    def get_footnotes(self) -> dict:
        return {}

    def get_conditions(self) -> dict:
        return {}

    def get_commodities_and_duties(self, commodity_count) -> dict:
        commodities_and_duties = {}
        commodities = GoodsNomenclature.objects.filter(suffix=80)[:commodity_count]
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
            "measure_type": str(measure_type),
            "start_date_0": start_date.day,
            "start_date_1": start_date.month,
            "start_date_2": start_date.year,
            "min_commodity_count": str(commodity_count),
        }

    def get_geographical_areas(self) -> dict:
        return {
            "geographical_area-geo_area": "ERGA_OMNES",
            "geographical_area-geographical_area_group": "",
        }

    def get_order_number(self) -> dict:
        return {"order_number": ""}
