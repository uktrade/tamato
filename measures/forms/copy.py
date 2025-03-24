from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Layout
from crispy_forms_gds.layout import Size
from crispy_forms_gds.layout import Submit
from dateutil.relativedelta import relativedelta
from django import forms

from commodities.models import GoodsNomenclature
from common.fields import AutoCompleteField
from common.forms import ValidityPeriodForm
from measures import models


class MeasureCopyForm(ValidityPeriodForm, forms.ModelForm):

    class Meta:
        model = models.Measure
        fields = (
            "valid_between",
            "goods_nomenclature",
        )

    goods_nomenclature = AutoCompleteField(
        label="Code and description",
        help_text="Select the 10 digit commodity code to which the measure applies.",
        queryset=GoodsNomenclature.objects.all(),
        required=False,
        attrs={"min_length": 3},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        prev_end_date = self.instance.valid_between.upper
        if prev_end_date is not None:
            self.fields["start_date"].initial = prev_end_date + relativedelta(days=+1)
            self.fields["start_date"].help_text = (
                "Start date has been automatically updated to one day after the end date of the original measure"
            )
        else:
            self.fields["start_date"].initial = None

        self.fields["end_date"].initial = None

        self.helper = FormHelper(self)
        self.helper.label_size = Size.SMALL
        self.helper.legend_size = Size.SMALL

        self.helper.layout = Layout(
            "start_date",
            "end_date",
            "goods_nomenclature",
            Submit(
                "submit",
                "Copy",
                data_module="govuk-button",
                data_prevent_double_click="true",
            ),
        )
