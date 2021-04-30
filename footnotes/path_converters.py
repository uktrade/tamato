"""
Custom path converters for footnotes.

https://docs.djangoproject.com/en/3.2/topics/http/urls/#registering-custom-path-converters
"""


from django.urls.converters import StringConverter

from footnotes import validators


class FootnoteIdConverter(StringConverter):
    regex = validators.FOOTNOTE_ID_PATTERN


class FootnoteTypeIdConverter(StringConverter):
    regex = validators.FOOTNOTE_TYPE_ID_PATTERN
