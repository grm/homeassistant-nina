"""Tests for the dashboard builder."""

from __future__ import annotations

import pytest

from custom_components.nina_polaris.dashboard_builder import build_dashboard_config


def _all_cards(view):
    """Flatten cards across the multi-column 'sections' view, recursing into
    vertical-stack / horizontal-stack / grid containers."""

    def _walk(node, out):
        if isinstance(node, dict):
            out.append(node)
            for child in node.get("cards", []) or []:
                _walk(child, out)
        return out

    out = []
    for section in view.get("sections", []):
        for card in section.get("cards", []):
            _walk(card, out)
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
    """The Equipment card is a single vertical entities list."""
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
    names = {row["name"] for row in rows}
    assert {"Camera", "Mount", "Focuser", "Guider"}.issubset(names)


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_config_equipment_inline_actions(hass):
    """A Controls section follows Equipment with action tiles."""
    config = build_dashboard_config(hass)
    cards = _all_cards(config["views"][0])
    headings = [c.get("heading") for c in cards if c.get("type") == "heading"]
    assert "Equipment" in headings and "Controls" in headings
    action_tile_entities = {
        c.get("entity")
        for c in cards
        if c.get("type") == "tile" and (c.get("entity") or "").startswith("button.")
    }
    joined = " ".join(action_tile_entities)
    assert "park" in joined and "connect" in joined


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
