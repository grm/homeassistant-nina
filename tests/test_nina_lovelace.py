"""Tests for the auto-registered NINA Polaris Lovelace dashboards."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.nina_polaris.nina_lovelace import (
    NinaInstanceLovelaceConfig,
    _slugify,
    _url_path_for,
    async_register_instance_dashboard,
    async_unregister_instance_dashboard,
)


@pytest.fixture
async def lovelace_ready(hass: HomeAssistant):
    await async_setup_component(hass, "lovelace", {})
    return hass


def _dashboards(hass: HomeAssistant):
    data = hass.data["lovelace"]
    return data["dashboards"] if isinstance(data, dict) else data.dashboards


def _entry(hass: HomeAssistant):
    return next(iter(hass.config_entries.async_entries("nina_polaris")))


def test_slugify() -> None:
    assert _slugify("Trevinca") == "trevinca"
    assert _slugify("TEC 140 ED") == "tec-140-ed"
    assert _slugify("FRA-400 / pier") == "fra-400-pier"
    assert _slugify("   ") == "instance"


async def test_dashboard_registered_after_setup_entry(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """A per-instance panel + Lovelace config is created on entry setup."""
    entry = _entry(hass)
    url_path = _url_path_for(entry)
    assert url_path.startswith("nina-")
    panels = hass.data.get("frontend_panels", {})
    assert url_path in panels
    panel = panels[url_path]
    # Sidebar title is the configured instance name (entry.title).
    assert panel.sidebar_title == entry.title
    dashboards = _dashboards(hass)
    assert isinstance(dashboards[url_path], NinaInstanceLovelaceConfig)


async def test_dashboard_load_returns_single_view(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """Per-instance dashboard contains exactly one view."""
    entry = _entry(hass)
    cfg = _dashboards(hass)[_url_path_for(entry)]
    loaded = await cfg.async_load(force=False)
    assert isinstance(loaded["views"], list)
    assert len(loaded["views"]) == 1
    info = await cfg.async_get_info()
    assert info["mode"] == "generated"


async def test_dashboard_async_json_returns_fragment(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """Regression: LovelaceConfig.async_json must be implemented."""
    cfg = _dashboards(hass)[_url_path_for(_entry(hass))]
    assert await cfg.async_json(force=False) is not None


async def test_dashboard_rebuilds_on_each_load(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    cfg = _dashboards(hass)[_url_path_for(_entry(hass))]
    with patch(
        "custom_components.nina_polaris.nina_lovelace.build_dashboard_config",
        return_value={"views": [{"title": "fresh"}]},
    ) as mock_build:
        await cfg.async_load(force=False)
        await cfg.async_load(force=False)
    assert mock_build.call_count == 2


async def test_register_is_idempotent(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    entry = _entry(hass)
    async_register_instance_dashboard(hass, entry)
    async_register_instance_dashboard(hass, entry)
    assert _url_path_for(entry) in hass.data.get("frontend_panels", {})


async def test_unregister_removes_panel(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    entry = _entry(hass)
    url_path = _url_path_for(entry)
    async_unregister_instance_dashboard(hass, entry)
    assert url_path not in hass.data.get("frontend_panels", {})
    assert url_path not in _dashboards(hass)
