"""Custom path converters
https://docs.djangoproject.com/en/3.2/topics/http/urls/#registering-custom-path-
converters."""

from django.urls.converters import IntConverter


class NumericSIDConverter(IntConverter):
    regex = r"[0-9]{1,8}"
