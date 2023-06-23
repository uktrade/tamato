from unittest.mock import MagicMock

import pytest
from django.template.loader import render_to_string
from py_w3c.validators.html.validator import HTMLValidator


@pytest.fixture
def mock_request():
    mock_request = MagicMock()
    mock_request.csp_nonce = "1234"
    return mock_request


def test_commodities_hierarchy_html(mock_request):
    mock_snapshot = {}
    mock_commodity = MagicMock(item_id="2620999590", sid=1234, suffix="80", indent=4)
    mock_commodities = [
        MagicMock(item_id="2620000000", suffix="80", indent=0),
        MagicMock(item_id="2620110000", suffix="10", indent=1),
        MagicMock(item_id="2620110000", suffix="80", indent=2),
        MagicMock(item_id="2620200000", suffix="80", indent=1),
        MagicMock(item_id="2620210000", suffix="10", indent=1),
        MagicMock(item_id="2620210000", suffix="80", indent=2),
        MagicMock(item_id="2620290000", suffix="80", indent=2),
        MagicMock(item_id="2620910000", suffix="10", indent=1),
        MagicMock(item_id="2620910000", suffix="80", indent=2),
        MagicMock(item_id="2620992000", suffix="80", indent=3),
        MagicMock(item_id="2620993000", suffix="80", indent=3),
        MagicMock(item_id="2620999510", suffix="80", indent=4),
        mock_commodity,
    ]
    mock_ancestors = {
        mock_commodity: [
            MagicMock(item_id="2620993000", suffix="80", indent=3),
            MagicMock(item_id="2620910000", suffix="10", indent=1),
            MagicMock(item_id="2620910000", suffix="80", indent=2),
        ],
    }
    mock_snapshot["commodities"] = mock_commodities
    mock_snapshot["ancestors"] = mock_ancestors
    page = render_to_string(
        "includes/commodities/tabs/hierarchy.jinja",
        {
            "snapshot": mock_snapshot,
            "commodity": mock_commodity,
            "this_commodity": mock_commodity,
            "request": mock_request,
        },
    )
    html_validator = HTMLValidator()
    html_validator.validate_fragment(page)
    assert not html_validator.errors


def test_commodities_hierarchy_html_single_commodity(mock_request):
    mock_snapshot = {}
    mock_commodity = MagicMock(item_id="2620000000", suffix="80", indent=0)
    mock_commodities = [
        mock_commodity,
    ]
    mock_ancestors = {mock_commodity: []}
    mock_snapshot["commodities"] = mock_commodities
    mock_snapshot["ancestors"] = mock_ancestors
    page = render_to_string(
        "includes/commodities/tabs/hierarchy.jinja",
        {
            "snapshot": mock_snapshot,
            "commodity": mock_commodity,
            "this_commodity": mock_commodity,
            "request": mock_request,
        },
    )
    html_validator = HTMLValidator()
    html_validator.validate_fragment(page)
    assert not html_validator.errors
