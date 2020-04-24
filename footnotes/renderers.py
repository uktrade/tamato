from rest_framework import renderers


class FootnotesAPIRenderer(renderers.JSONRenderer):
    media_type = "application/vnd.uktrade.tamato+json"
