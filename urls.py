"""
tamato URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include
from django.urls import path

import common

urlpatterns = [
    path("", include("common.urls")),
    path("", include("additional_codes.urls")),
    path("", include("certificates.urls")),
    path("", include("commodities.urls")),
    path("", include("exporter.urls")),
    path("", include("footnotes.urls")),
    path("", include("geo_areas.urls")),
    path("", include("importer.urls")),
    path("", include("measures.urls")),
    path("", include("quotas.urls")),
    path("", include("regulations.urls")),
    path("", include("reports.urls")),
    path("", include("workbaskets.urls", namespace="workbaskets")),
    path("admin/", admin.site.urls),
]

handler403 = "common.views.handler403"
handler500 = "common.views.handler500"

if settings.DEBUG:
    urlpatterns += [
        path("403/", common.views.handler403, name="handler403"),
        path("500/", common.views.handler500, name="handler500"),
    ]

if settings.SSO_ENABLED:
    urlpatterns = [
        path(
            "auth/",
            include(
                "authbroker_client.urls",
            ),
        ),
        *urlpatterns,
    ]

if "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *urlpatterns]
