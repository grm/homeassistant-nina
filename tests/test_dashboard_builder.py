"""Tests for the dashboard builder."""

from __future__ import annotations

import pytest

from custom_components.nina_polaris.dashboard_builder import build_dashboard_config


def _all_cards(view):
    """Flatten cards across the multi-column 'sections' view."""
    out = []
    for section in view.get("sections", []):
        out.extend(section.get("cards", []))
    return out


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_config_has_one_view_per_instance(hass):
    config = build_dashboard_config(hass)
    assert config["title"] == "NINA Polaris"
    assert isinstance(config["views"], list)
    assert len(config["views"]) == 1
    view = config["views"][0]
    assert view["icon"] == "mdi:telescope"
    assert view["type"] == "sections"
    # We expect a 3-column layout with at least 2 sections populated.
    assert len(view["sections"]) >= 2
    assert len(_all_cards(view)) >= 4


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_config_includes_camera(hass):
    config = build_dashboard_config(hass)
    cards = _all_cards(config["views"][0])
    types = [c.get("type") for c in cards]
    assert "picture-entity" in types


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_config_equipment_uses_entities_card(hass):
    """The Equipment card is a vertical entities list with friendly names."""
    config = build_dashboard_config(hass)
    cards = _all_cards(config["views"][0])
    eq_cards = [
        c
        for c in cards
        if c.get("type") == "entities"
        and any(row.get("name") in {"Camera", "Mount", "Guider"} for row in c.get("entities", []))
    ]
    assert len(eq_cards) == 1, "expected exactly one Equipment entities card"
    rows = eq_cards[0]["entities"]
    assert all(isinstance(row, dict) and "name" in row and "entity" in row for row in rows)
    names = {row["name"] for row in rows}
    assert "Camera" in names or "Mount" in names


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_config_mushroom_chips(hass):
    config = build_dashboard_config(hass, use_mushroom=True)
    cards = _all_cards(config["views"][0])
    assert any(c.get("type") == "custom:mushroom-chips-card" for c in cards)
    entities_titles = [c.get("title") for c in cards if c.get("type") == "entities"]
    assert "Equipment" not in entities_titles


async def test_build_dashboard_config_no_instances(hass):
    config = build_dashboard_config(hass, entry_ids=[])
    assert len(config["views"]) == 1
    # No-instances fallback uses a classic 'cards' view, not a sections view.
    cards = config["views"][0].get("cards") or _all_cards(config["views"][0])
    assert any(c.get("type") == "markdown" for c in cards)
    assert "No NINA Polaris instance" in cards[0]["content"]
