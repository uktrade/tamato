from django.urls import path

from packaging import views

urlpatterns = [
    # TODO: Make all paths hang off /packaging/
    path(
        "packaging-queue/",
        views.WorkBasketPackagingQueue.as_view(),
        name="packaging-ui-packaging-queue",
    ),
]
