"""
Custom path converters for regulations.

https://docs.djangoproject.com/en/3.2/topics/http/urls/#registering-custom-path-converters
"""

from django.urls.converters import IntConverter
from django.urls.converters import StringConverter

from regulations import validators


class RegulationRoleTypeConverter(IntConverter):
    regex = fr"({'|'.join(str(i) for i in validators.RoleType.values)})"


class RegulationIdConverter(StringConverter):
    regex = validators.REGULATION_ID_REGEX
