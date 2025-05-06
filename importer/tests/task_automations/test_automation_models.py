import pytest
from bs4 import BeautifulSoup

from tasks.models import StateChoices

pytestmark = pytest.mark.django_db


def test_import_goods_automation_get_state_can_run(
    import_goods_automation_state_is_CAN_RUN,
):
    """Test that an automation in CAN_RUN state renders correctly."""
    assert import_goods_automation_state_is_CAN_RUN.get_state() == StateChoices.CAN_RUN
    rendering = import_goods_automation_state_is_CAN_RUN.rendered_state()
    soup = BeautifulSoup(rendering)
    import_anchor = soup.select(".automation.state-can-run > a")
    assert len(import_anchor) == 1
    assert "Import EU TARIC file" in import_anchor[0]


def test_import_goods_automation_get_state_running(
    import_goods_automation_state_is_RUNNING,
):
    """Test that an automation in RUNNING state renders correctly."""
    assert import_goods_automation_state_is_RUNNING.get_state() == StateChoices.RUNNING
    rendering = import_goods_automation_state_is_RUNNING.rendered_state()
    soup = BeautifulSoup(rendering)
    headings = soup.select(".automation.state-running > h3")
    assert len(headings) == 1
    assert "File is being imported" in headings[0]


def test_import_goods_automation_get_state_done(
    import_goods_automation_state_is_DONE,
):
    """Test that an automation in DONE state renders correctly."""
    """TODO."""


def test_import_goods_automation_get_state_errored(
    import_goods_automation_state_is_ERRORED,
):
    """Test that an automation in ERRORED state renders correctly."""
    """TODO."""
