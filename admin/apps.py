from django.contrib.admin.apps import AdminConfig


class TamatoAdminConfig(AdminConfig):
    default_site = "admin.site.TamatoAdminSite"
