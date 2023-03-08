import re
from unittest import mock
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.test.html import parse_html
from django.urls import reverse

from common.tests import factories
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_celery_task():
    with mock.patch("exporter.tasks.upload_workbaskets.delay") as task:
        yield task


@pytest.mark.parametrize(
    "user",
    [
        "staff_user",
        "valid_user",
    ],
)
def test_upload(client, request, mock_celery_task, user):
    upload_url = reverse("admin:upload")

    client.force_login(request.getfixturevalue(user))
    response = client.post(upload_url)
    assert response.status_code == 302

    if user == "staff_user":
        assert response.url == reverse("admin:workbaskets_workbasket_changelist")
        mock_celery_task.assert_called_once()

    else:
        login_url = reverse("admin:login")
        assert response.url == f"{login_url}?next={upload_url}"
        mock_celery_task.assert_not_called()


@pytest.fixture
def superadmin():
    return factories.UserFactory.create(is_superuser=True, is_staff=True)


@patch("exporter.tasks.upload_workbaskets")
def test_change_workbasket_status_options(upload, client, superadmin, workbasket):
    detail_url = reverse("admin:workbaskets_workbasket_change", args=[workbasket.id])

    client.force_login(superadmin)
    response = client.get(detail_url, follow=True)

    select = re.search(
        r'<select name="transition".*select>',
        response.content.decode(),
        re.DOTALL,
    )
    if not select:
        pytest.fail("Workbasket transition select field not found")

    options = parse_html(select[0]).children
    option_values = [
        attr[1] for opt in options for attr in opt.attributes if attr[0] == "value"
    ]

    assert option_values == [""] + [
        t.name for t in workbasket.get_available_status_transitions()
    ]


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPOGATES=True)
@patch("exporter.tasks.upload_workbaskets")
def test_change_workbasket_status(upload, client, superadmin, workbasket, transition):
    """Test submitting all combinations of workbasket status and transition
    (including impossible submissions)"""

    change_url = reverse("admin:workbaskets_workbasket_change", args=[workbasket.id])

    client.force_login(superadmin)

    response = client.post(
        change_url,
        data={
            "transition": transition.name,
            "reason": workbasket.reason,
            "title": workbasket.title,
        },
    )

    allowed_transitions = [
        t.name for t in workbasket.get_available_status_transitions()
    ]
    if allowed_transitions:
        if transition.name in allowed_transitions:
            assert response.status_code == 302
            workbasket.refresh_from_db()
            assert workbasket.status == transition.target.value
        else:
            # only possible to submit by editing the HTTP POST data
            assert response.status_code == 200
            error = re.search(
                r'<ul class="errorlist".*ul>',
                response.content.decode(),
                re.DOTALL,
            )
            if not error:
                pytest.fail("Error message not found")

    else:
        # transition field is ignored
        pass


@pytest.mark.skip(reason="Requires approach to testing Celery task management.")
def test_terminate_workbasket_rule_check(client, superadmin):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.rule_check_task_id = "aa97eb5a-0bb9-411f-995d-6724e326e9f7"

    change_url = reverse(
        "admin:workbaskets_workbasket_change",
        args=[workbasket.id],
    )
    # TODO: mock celery.result.AsyncResult
    client.force_login(superadmin)
    response = client.post(
        change_url,
        data={
            "transition": "",
            "reason": workbasket.reason,
            "title": workbasket.title,
            "terminate_rule_check": "on",
        },
    )

    assert response.status_code == 302
    workbasket.refresh_from_db()
    assert not workbasket.rule_check_task_id


# https://uktrade.atlassian.net/browse/TP2000-556
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_workbasket_empty_rule_check_task_id_value(client, superadmin):
    """Test that admin change view saves workbasket rule_check_task_id as a null
    value, rather than an empty string, avoiding duplicate value errors."""

    factories.WorkBasketFactory.create(rule_check_task_id="")
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
        rule_check_task_id=None,
    )
    change_url = reverse(
        "admin:workbaskets_workbasket_change",
        args=[workbasket.id],
    )
    client.force_login(superadmin)
    response = client.post(
        change_url,
        data={
            "transition": "queue",
            "reason": workbasket.reason,
            "title": workbasket.title,
        },
    )

    assert response.status_code == 302
    workbasket.refresh_from_db()

    assert workbasket.rule_check_task_status == None
