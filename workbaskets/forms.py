from django import forms


class SelectableModelObjectField(forms.BooleanField):
    def __init__(self, *args, **kwargs):
        self.obj = kwargs.pop("obj")
        super().__init__(*args, **kwargs)


class SelectableWorkBasketItemsForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.workbasket = kwargs.pop("workbasket")
        super().__init__(*args, **kwargs)
        for tracked_model in self.workbasket.tracked_models:
            self.fields[
                f"tracked_model_{tracked_model.pk}"
            ] = SelectableModelObjectField(
                required=False,
                obj=tracked_model,
            )
