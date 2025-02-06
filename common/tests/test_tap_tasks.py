import unittest

import pytest

from common.inspect_tap_tasks import CeleryTask
from common.inspect_tap_tasks import TAPTasks
from common.tasks_constants import *
from common.tests import factories


@pytest.fixture
def celery_dict():
    return {
        "celery@1": [
            {
                "id": "task1_id",
                "name": "workbaskets.tasks.call_check_workbasket_sync",
                "args": [1591],
                "kwargs": {},
                "type": "workbaskets.tasks.call_check_workbasket_sync",
                "hostname": "celery@1",
                "time_start": None,
                "acknowledged": False,
                "delivery_info": {"routing_key": "rule-check"},
                "worker_pid": None,
            },
            {
                "id": "task2_id",
                "name": "workbaskets.tasks.call_check_workbasket_sync",
                "args": [1587],
                "kwargs": {},
                "type": "workbaskets.tasks.call_check_workbasket_sync",
                "hostname": "celery@1",
                "time_start": None,
                "acknowledged": False,
                "delivery_info": {"routing_key": "rule-check"},
                "worker_pid": None,
            },
        ],
        "celery@2": [
            {
                "id": "task2_id",
                "name": "workbaskets.tasks.some_other_task_name",
                "args": [1587],
                "kwargs": {},
                "type": "workbaskets.tasks.some_other_task_name",
                "hostname": "celery@1",
                "time_start": None,
                "acknowledged": False,
                "delivery_info": {"routing_key": "standard"},
                "worker_pid": None,
            },
        ],
        "celery@3": [],
    }


@pytest.mark.parametrize(
    "args,kwargs,exp",
    [
        ([{}], {}, []),
        ([{"1": [None, None, None]}], {}, []),
        (
            [{"1": [{"status": "Active"}]}],
            {"routing_key": "", "task_status": "Active"},
            [{"status": "Active"}],
        ),
        (
            [
                {
                    "1": [
                        {
                            "status": "Active",
                            "delivery_info": {"routing_key": "rule-check"},
                        },
                    ],
                },
            ],
            {"routing_key": "rule-check", "task_status": "Active"},
            [{"status": "Active", "delivery_info": {"routing_key": "rule-check"}}],
        ),
    ],
)
def test_tap_tasks_clean_tasks(args, kwargs, exp):
    tap_tasks = TAPTasks()
    cleaned = tap_tasks.clean_tasks(*args, **kwargs)
    assert cleaned == exp


@pytest.mark.parametrize(
    "name,exp",
    [
        (MISSING_MEASURES_CHECK_NAME, "0 out of 2"),
        (RULE_CHECK_NAME, "0 out of 3"),
    ],
)
def test_tap_tasks_get_progress(name, exp, user_workbasket):
    # user_workbasket/assigned_workbasket by default already has one TrackedModel in it (FootnoteType)
    factories.GoodsNomenclatureFactory.create(
        transaction=user_workbasket.new_transaction(),
        item_id="9900000000",
    )
    # factory creates a comm code and an origin so total num in workbasket will be 2
    tap_tasks = TAPTasks()
    progress = tap_tasks.get_task_progress(user_workbasket.id, name)
    assert progress == exp


@unittest.mock.patch("common.inspect_tap_tasks.TAPTasks.get_due_tasks")
def test_tap_tasks_current_tasks(mock_get_due_tasks, user_workbasket):
    mock_get_due_tasks.return_value = [
        {
            "time_start": None,
            "name": RULE_CHECK_NAME,
            "id": "1234",
            "args": [user_workbasket.id],
            "status": "Active",
        },
    ]
    tap_tasks = TAPTasks()
    current_tasks = tap_tasks.current_tasks(routing_key="rule-check")
    exp = [
        CeleryTask(
            task_id="1234",
            verbose_name="Rule check",
            workbasket_id=user_workbasket.id,
            date_time_start=None,
            progress="0 out of 1",
            status="Active",
        ),
    ]
    assert current_tasks == exp
