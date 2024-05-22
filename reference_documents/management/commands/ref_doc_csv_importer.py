import os
from datetime import date

import pandas as pd
from django.core.management import BaseCommand

from common.util import TaricDateRange
from reference_documents.models import PreferentialQuota
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.models import PreferentialRate
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.models import ReferenceDocumentVersionStatus


class Command(BaseCommand):
    help = "Import reference document data from a CSV file"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "duties_csv_path",
            type=str,
            required=True,
            help="The absolute path to the duties csv file to import",
        )
        parser.add_argument(
            "quotas_csv_path",
            type=str,
            help="The absolute path to the quotas csv file to import",
        )

        return super().add_arguments(parser)

    def handle(self, *args, **options):
        # verify each file exists
        if not os.path.isfile(options["duties_csv_path"]):
            raise FileNotFoundError(options["duties_csv_path"])

        if not os.path.isfile(options["quotas_csv_path"]):
            raise FileNotFoundError(options["duties_csv_path"])

        self.duties_csv_path = options["duties_csv_path"]
        self.quotas_csv_path = options["quotas_csv_path"]

        self.quotas_df = self.load_quotas_csv()
        self.duties_df = self.load_duties_csv()

        self.create_ref_docs_and_versions()

    def load_duties_csv(self):
        df = pd.read_csv(
            self.duties_csv_path,
            dtype={
                "Standardised Commodity Code": "object",
                "Valid From": "object",
                "Valid To": "object",
            },
        )
        return df

    def load_quotas_csv(self):
        df = pd.read_csv(
            self.quotas_csv_path,
            dtype={
                "Standardised Commodity Code": "object",
            },
        )
        return df

    def add_pt_quota_if_no_exists(
            self,
            df_row,
            order_number,
            reference_document_version,
    ):
        if len(order_number) != 6:
            print(f"skipping wonky order number : -{order_number}-")
            return

        comm_code = df_row["Standardised Commodity Code"]
        comm_code = comm_code + ("0" * (len(comm_code) - 10))
        quota_duty_rate = df_row["Quota Duty Rate"]
        volume = df_row["Quota Volume"].replace(",", "")
        units = df_row["Units"]

        # no data contains valid dates, just create a single record - can be edited later in UI
        quota_definition_valid_between = None

        if reference_document_version.entry_into_force_date:
            order_number_valid_between = TaricDateRange(
                reference_document_version.entry_into_force_date,
            )
        else:
            order_number_valid_between = None

        # add a new one
        order_number_record, created = PreferentialQuotaOrderNumber.objects.get_or_create(
            quota_order_number=order_number,
            reference_document_version_id=reference_document_version.id,
            valid_between=order_number_valid_between,
            coefficient=None,
            main_order_number=None,
        )

        if created:
            order_number_record.save()

        # add a new one
        quota, created = PreferentialQuota.objects.get_or_create(
            commodity_code=comm_code,
            preferential_quota_order_number=order_number_record,
            quota_duty_rate=quota_duty_rate,
            volume=volume,
            valid_between=quota_definition_valid_between,
            measurement=units,
        )

        if created:
            quota.save()

    def add_pt_duty_if_no_exist(self, df_row, reference_document_version):
        # check for existing entry for comm code
        comm_code = df_row["Standardised Commodity Code"]
        comm_code = comm_code + ("0" * (len(comm_code) - 10))

        # add a new one
        pref_rate, created = PreferentialRate.objects.get_or_create(
            commodity_code=comm_code,
            duty_rate=df_row["Preferential Duty Rate"],
            reference_document_version=reference_document_version,
            valid_between=None,
        )

        if created:
            pref_rate.save()

    # Create base documents
    # Load duties, get unique countries and create base document for each

    def create_ref_docs_and_versions(self):
        areas = pd.unique(self.duties_df["area_id"].values)

        for area in areas:
            # Create records
            ref_doc, created = ReferenceDocument.objects.get_or_create(
                title=f"Reference document for {area}",
                area_id=area,
            )
            if created:
                ref_doc.save()

            versions = pd.unique(
                self.duties_df[self.duties_df["area_id"] == area][
                    "Document Version"
                ].values,
            )

            for version in versions:
                if (
                        self.duties_df[self.duties_df["area_id"] == area][
                            "Document Date"
                        ].values[0]
                        == "empty_cell"
                ):
                    document_publish_date = None
                else:
                    doc_date_string = str(
                        self.duties_df[self.duties_df["area_id"] == area][
                            "Document Date"
                        ].values[0],
                    )
                    document_publish_date = date(
                        int(doc_date_string[:4]),
                        int(doc_date_string[4:6]),
                        int(doc_date_string[6:]),
                    )

                # Create version
                ref_doc_version, created = (
                    ReferenceDocumentVersion.objects.get_or_create(
                        reference_document=ref_doc,
                        version=float(version),
                        published_date=document_publish_date,
                        entry_into_force_date=None,
                        status=ReferenceDocumentVersionStatus.EDITING,
                    )
                )

                if created:
                    ref_doc_version.save()

                # Add duties

                # get duties for area
                df_area_duties = self.duties_df.loc[self.duties_df["area_id"] == area]
                for index, row in df_area_duties.iterrows():
                    print(f' -- -- {row["Standardised Commodity Code"]}')
                    self.add_pt_duty_if_no_exist(row, ref_doc_version)

                # Quotas

                # Filter by area_id and document version
                quotas_df = self.quotas_df[self.quotas_df["area_id"] == area]
                quotas_df = self.quotas_df[
                    self.quotas_df["Document Version"] == version
                    ]

                add_to_index = 1
                for index, row in quotas_df.iterrows():
                    # split order numbers
                    order_number = row["Quota Number"]
                    order_number = order_number.replace(".", "")

                    if len(order_number) > 6:
                        order_numbers = order_number.split(" ")
                    else:
                        order_numbers = [order_number]

                    for on in order_numbers:
                        print(f' -- -- {on} - {row["Standardised Commodity Code"]}')
                        self.add_pt_quota_if_no_exists(
                            row,
                            on,
                            ref_doc_version,
                        )
