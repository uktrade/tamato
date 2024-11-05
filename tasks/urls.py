from django.urls import include
from django.urls import path

from tasks import views

app_name = "workflow"

ui_patterns = [
    path("", views.TaskListView.as_view(), name="task-ui-list"),
    path("<int:pk>/", views.TaskDetailView.as_view(), name="task-ui-detail"),
    path("create/", views.TaskCreateView.as_view(), name="task-ui-create"),
    path(
        "<int:pk>/confirm-create",
        views.TaskConfirmCreateView.as_view(),
        name="task-ui-confirm-create",
    ),
    path("<int:pk>/update/", views.TaskUpdateView.as_view(), name="task-ui-update"),
    path(
        "<int:pk>/confirm-update",
        views.TaskConfirmUpdateView.as_view(),
        name="task-ui-confirm-update",
    ),
    path("<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task-ui-delete"),
    path(
        "<int:pk>/confirm-delete",
        views.TaskConfirmDeleteView.as_view(),
        name="task-ui-confirm-delete",
    ),
    path(
        "<int:pk>/sub-tasks/create",
        views.SubTaskCreateView.as_view(),
        name="subtask-ui-create",
    ),
]

urlpatterns = [
    path("tasks/", include(ui_patterns)),
]
