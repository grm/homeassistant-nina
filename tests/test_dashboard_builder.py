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
    # Status, then capture, then dangerous actions — stacked, one column.
    assert view["max_columns"] == 1
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
    """Capture actions sit under status; dangerous ones confirm before they run."""
    config = build_dashboard_config(hass)
    cards = _all_cards(config["views"][0])
    headings = [c.get("heading") for c in cards if c.get("type") == "heading"]
    assert headings.index("Status") < headings.index("Capture") < headings.index("Dangerous")
    action_tiles = [c for c in cards if c.get("type") == "tile" and (c.get("entity") or "").startswith("button.")]
    joined = " ".join(c["entity"] for c in action_tiles)
    assert "park" in joined and "connect" in joined
    park = next(c for c in action_tiles if c.get("name") == "Park mount")
    assert park["tap_action"]["confirmation"]["text"] == "Park the mount?"
    start = next(c for c in action_tiles if c.get("name") == "Start sequence")
    assert "confirmation" not in start["tap_action"]
    widths = {c["grid_options"]["columns"] for c in action_tiles}
    assert widths == {6}


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_monitoring_camera_inserted_when_option_set(hass, mock_config_entry):
    """When the monitoring_camera_entity option is set, a picture-entity card is added."""
    # Mutate options in place to avoid triggering the update listener (which would
    # reload the entry mid-test). We only need build_dashboard_config to read
    # entry.options at call time.
    object.__setattr__(mock_config_entry, "options", {"monitoring_camera_entity": "camera.obs_cam"})
    config = build_dashboard_config(hass)
    cards = _all_cards(config["views"][0])
    assert any(c.get("type") == "picture-entity" and c.get("entity") == "camera.obs_cam" for c in cards)
    headings = [c.get("heading") for c in cards if c.get("type") == "heading"]
    assert "Monitoring" in headings


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_no_monitoring_camera_by_default(hass):
    """Without the option, no 'Monitoring' heading is rendered."""
    config = build_dashboard_config(hass)
    cards = _all_cards(config["views"][0])
    headings = [c.get("heading") for c in cards if c.get("type") == "heading"]
    assert "Monitoring" not in headings


@pytest.mark.usefixtures("mock_config_entry")
async def test_build_dashboard_config_mushroom_chips(hass):
    config = build_dashboard_config(hass, use_mushroom=True)
    cards = _all_cards(config["views"][0])
    assert any(c.get("type") == "custom:mushroom-chips-card" for c in cards)
    entities_titles = [c.get("title") for c in cards if c.get("type") == "entities"]
    assert "Equipment" not in entities_titles


async def test_build_dashboard_config_stacks_instances_in_a_menu(hass):
    """Several instances open from a menu, one telescope under the other."""
    config = build_dashboard_config(hass, entry_ids=["aaaabbbbcccc", "ddddeeeeffff"])
    assert config["title"] == "NINA Polaris"
    views = config["views"]
    assert len(views) == 3
    menu, first, second = views
    assert menu["path"] == "home"
    assert menu.get("subview") is not True
    assert first["subview"] is True
    assert second["subview"] is True
    assert first["back_path"] == "/nina/home"
    buttons = [c for c in _all_cards(menu) if c.get("type") == "button"]
    assert len(buttons) == 2
    assert [b["grid_options"]["columns"] for b in buttons] == [12, 12]
    assert buttons[0]["tap_action"]["navigation_path"] == f"/nina/{first['path']}"
    assert buttons[1]["tap_action"]["navigation_path"] == f"/nina/{second['path']}"


async def test_build_dashboard_config_no_instances(hass):
    config = build_dashboard_config(hass, entry_ids=[])
    assert len(config["views"]) == 1
    # No-instances fallback uses a classic 'cards' view, not a sections view.
    cards = config["views"][0].get("cards") or _all_cards(config["views"][0])
    assert any(c.get("type") == "markdown" for c in cards)
    assert "No NINA Polaris instance" in cards[0]["content"]
