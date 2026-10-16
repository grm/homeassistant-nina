"""Tests for the auto-registered NINA Polaris Lovelace dashboards."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.nina_polaris.nina_lovelace import (
    NinaLovelaceConfig,
    _slugify,
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
    """One shared panel is created on entry setup."""
    panels = hass.data.get("frontend_panels", {})
    assert "nina" in panels
    assert panels["nina"].sidebar_title == "NINA"
    assert isinstance(_dashboards(hass)["nina"], NinaLovelaceConfig)


async def test_dashboard_load_returns_single_view(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """A single instance opens directly, without the telescope menu."""
    cfg = _dashboards(hass)["nina"]
    loaded = await cfg.async_load(force=False)
    assert isinstance(loaded["views"], list)
    assert len(loaded["views"]) == 1
    info = await cfg.async_get_info()
    assert info["mode"] == "generated"


async def test_dashboard_async_json_returns_fragment(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """Regression: LovelaceConfig.async_json must be implemented."""
    cfg = _dashboards(hass)["nina"]
    assert await cfg.async_json(force=False) is not None


async def test_dashboard_rebuilds_on_each_load(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    cfg = _dashboards(hass)["nina"]
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
    assert "nina" in hass.data.get("frontend_panels", {})


async def test_unregister_removes_panel(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    entry = _entry(hass)
    async_unregister_instance_dashboard(hass, entry)
    assert "nina" not in hass.data.get("frontend_panels", {})
    assert "nina" not in _dashboards(hass)
