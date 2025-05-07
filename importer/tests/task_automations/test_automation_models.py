import pytest
from bs4 import BeautifulSoup

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("automation_name", "css_path", "css_path_text"),
    (
        (
            "import_goods_automation_state_is_CAN_RUN",
            ".automation.state-can-run > a",
            "Import EU TARIC file",
        ),
        (
            "import_goods_automation_state_is_RUNNING",
            ".automation.state-running > h3",
            "File is being imported",
        ),
        (
            "import_goods_automation_state_is_DONE",
            ".automation.state-done > h3",
            "File imported - changes detected",
        ),
        (
            "import_goods_automation_state_is_DONE_empty",
            ".automation.state-done > h3",
            "File imported - empty",
        ),
        (
            "import_goods_automation_state_is_ERRORED",
            ".automation.state-errored > h3",
            "There are problems",
        ),
    ),
)
def test_import_goods_automation(
    automation_name,
    css_path,
    css_path_text,
    request,
):
    """Test that automation instances in various states renders correctly."""
    automation = request.getfixturevalue(automation_name)
    rendering = automation.rendered_state()
    soup = BeautifulSoup(rendering, "html.parser")
    headings = soup.select(css_path)
    assert len(headings) == 1
    assert css_path_text in headings[0]
