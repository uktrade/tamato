from django.urls import path
from rest_framework import routers

import reference_documents.views as views

app_name = "reference_documents"

api_router = routers.DefaultRouter()

urlpatterns = [
    path("reference_documents/", views.ReferenceDocumentList.as_view(), name="index"),
]
