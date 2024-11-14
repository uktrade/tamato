from django.urls import include
from django.urls import path

from tasks import views

app_name = "workflow"

task_ui_patterns = [
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

workflow_ui_patterns = [
    # TODO
]

workflow_template_ui_patterns = [
    path(
        "<int:pk>/",
        views.TaskWorkflowTemplateDetailView.as_view(),
        name="task-workflow-template-ui-detail",
    ),
    path(
        "task-templates/<int:pk>/",
        views.TaskTemplateDetailView.as_view(),
        name="task-template-ui-detail",
    ),
    path(
        "<int:workflow_template_pk>/task-templates/create/",
        views.TaskTemplateCreateView.as_view(),
        name="task-template-ui-create",
    ),
    path(
        "task-templates/confirm-create/<int:pk>/",
        views.TaskTemplateConfirmCreateView.as_view(),
        name="task-template-ui-confirm-create",
    ),
]

urlpatterns = [
    path("tasks/", include(task_ui_patterns)),
    path("workflows/", include(workflow_ui_patterns)),
    path("workflow-templates/", include(workflow_template_ui_patterns)),
]
