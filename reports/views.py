import csv
import pandas as pd

from datetime import datetime
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from io import StringIO
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference

import reports.reports.index as index_model

import reports.utils as utils

from reports.forms import UploadCSVForm
from reports.models import EUDataModel


@permission_required("reports.view_report_index")
def index(request):
    context = {
        "report": index_model.IndexTable(),
    }

    return render(request, "reports/index.jinja", context)


@permission_required("reports.view_report")
def report(request):
    report_class = utils.get_report_by_slug(request.resolver_match.url_name)

    context = {
        "report": report_class(),
    }

    return render(
        request,
        utils.get_template_by_type(report_class.report_template),
        context,
    )


def export_report_to_csv(request, report_slug, current_tab=None):
    report_class = utils.get_report_by_slug(report_slug)
    report_instance = report_class()

    response = HttpResponse(content_type="text/csv")

    if current_tab:
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{report_slug + "_for_" + current_tab}_report.csv"'
        formatted_current_tab = current_tab.capitalize().replace("_", " ")

        # Define a dictionary to map current_tab values to methods
        tab_mapping = {
            report_instance.tab_name: (
                report_instance.headers(),
                report_instance.rows(),
            ),
            report_instance.tab_name2: (
                report_instance.headers2(),
                report_instance.rows2(),
            ),
            report_instance.tab_name3: (
                report_instance.headers3(),
                report_instance.rows3(),
            ),
            report_instance.tab_name4: (
                report_instance.headers4(),
                report_instance.rows4(),
            ),
        }

        # Use the dictionary to get the methods based on current_tab
        methods = tab_mapping.get(formatted_current_tab)

        if methods:
            headers, rows = methods
        else:
            # Raise an exception if current_tab doesn't match any expected values
            raise ValueError(f"Invalid current_tab value: {formatted_current_tab}")
    else:
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{report_slug}_report.csv"'
        headers = (
            report_instance.headers() if hasattr(report_instance, "headers") else None
        )
        rows = report_instance.rows() if hasattr(report_instance, "rows") else None

    writer = csv.writer(response)

    # For ag grid reports
    if hasattr(report_instance, "headers_list"):
        header_row = [
            header.replace("_", " ").capitalize()
            for header in report_instance.headers_list
        ]
        writer.writerow(header_row)
        for row in report_instance.rows():
            data_row = [
                str(row[header.replace("_", " ").capitalize()])
                for header in report_instance.headers_list
            ]
            writer.writerow(data_row)

    # For govuk table reports
    elif hasattr(report_instance, "headers"):
        writer.writerow([header.get("text", None) for header in headers])
        for row in rows:
            writer.writerow([column["text"] for column in row])

    # For charts
    else:
        writer.writerow(["Date", "Data"])

        for item in report_instance.data():
            writer.writerow([item["x"], item["y"]])

            # Add an additional row with empty values because Excel needs this for data recognition
            writer.writerow(["", ""])

    return response


def export_report_to_excel(request, report_slug):
    report_class = utils.get_report_by_slug(report_slug)
    report_instance = report_class()

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="{report_slug}_report.xlsx"'

    workbook = Workbook()
    sheet = workbook.active

    sheet.append(["Date", "Data"])

    for item in report_instance.data():
        sheet.append([item["x"], item["y"]])

        # Add an additional row with empty values because Excel needs this for data recognition
        sheet.append(["", ""])

    chart = BarChart()
    data = Reference(sheet, min_col=2, min_row=1, max_col=2, max_row=sheet.max_row)
    categories = Reference(sheet, min_col=1, min_row=2, max_row=sheet.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)
    chart.title = report_instance.name
    chart.x_axis.title = "Date"
    chart.y_axis.title = "Data"

    chart.width = 40
    chart.height = 20

    sheet.add_chart(chart, "E5")

    workbook.save(response)

    return response


def upload_report_csv(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]

            if is_eu_data_file(uploaded_file):
                content = read_excel_as_csv(uploaded_file)

                # Clear existing data in EUDataTable
                EUDataModel.objects.all().delete()

                save_eu_data(content)
                return redirect("reports:table_report_of_eu_data")

    else:
        form = UploadCSVForm()

    return render(request, "reports/upload_report_csv.jinja", {"form": form})


def is_eu_data_file(uploaded_file):
    try:
        content = read_excel_as_csv(uploaded_file)
        csv_reader = csv.DictReader(StringIO(content))
        file_columns = set(csv_reader.fieldnames) if csv_reader.fieldnames else set()

        print(f"File Columns: {file_columns}")
        return True
    except Exception as e:
        print(f"Error reading CSV content: {e}")
        return False


def read_excel_as_csv(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        csv_data = df.to_csv(index=False, encoding="utf-8")
        return csv_data
    except Exception as e:
        print(f"Error converting Excel to CSV: {e}")
        return ""


def save_eu_data(content):
    try:
        csv_reader = csv.DictReader(StringIO(content))
        for row in csv_reader:
            print(f"Row: {row}")
            try:
                start_date_str = row.get("Start date", None)
                end_date_str = row.get("End date", None)

                # Convert date strings to the correct format "YYYY-MM-DD"
                start_date = (
                    datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S").strftime(
                        "%Y-%m-%d"
                    )
                    if start_date_str
                    else None
                )
                end_date = (
                    datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S").strftime(
                        "%Y-%m-%d"
                    )
                    if end_date_str
                    else None
                )

                instance = EUDataModel(
                    goods_code=row.get("Goods code", None),
                    add_code=row.get("Add code", None),
                    order_no=row.get("Order No.", None),
                    start_date=start_date,
                    end_date=end_date,
                    red_ind=row.get("RED_IND", None),
                    origin=row.get("Origin", None),
                    measure_type=row.get(" Measure type", None),
                    legal_base=row.get("Legal base", None),
                    duty=row.get("Duty", None),
                    origin_code=row.get("Origin code", None),
                    meas_type_code=row.get(" Meas. type code", None),
                    goods_nomenclature_exists=row.get(
                        "Goods Nomenclature Exists in TAP", None
                    ),
                    geographical_area_exists=row.get(
                        "Geographical Area Exists in TAP", None
                    ),
                    measure_type_exists=row.get("Measure Type Exists in TAP", None),
                    measure_exists=row.get("Measure Exists in TAP", None),
                )

                print(f"Instance to be saved: {instance}")
                instance.save()

                print(f"Instance saved: {instance}")
            except Exception as e:
                print(f"Error saving row {row}: {e}")

    except Exception as e:
        print(f"Error reading CSV content: {e}")
        pass
