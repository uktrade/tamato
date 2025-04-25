from django.urls import reverse
from django.utils.safestring import mark_safe


def link_renderer_for_quotas(order_number, text, fragment=None):
    url = reverse("quota-ui-detail", args=[order_number.sid])
    href = url + fragment if fragment else url
    return mark_safe(
        f"<a class='govuk-link govuk-!-font-weight-bold' href='{href}'>{text}</a>",
    )


def link_renderer_for_quota_origin(origin):
    url = reverse("geo_area-ui-detail", args=[origin.sid])
    return mark_safe(
        f"<a class='govuk-link govuk-!-font-weight-bold' href='{url}'>{origin}</a>",
    )
