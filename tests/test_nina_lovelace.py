"""Tests for the auto-registered NINA Polaris Lovelace dashboard."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.nina_polaris.nina_lovelace import (
    NINA_DASHBOARD_TITLE,
    NINA_DASHBOARD_URL_PATH,
    NinaLovelaceConfig,
    async_register_dashboard,
    async_unregister_dashboard,
)


@pytest.fixture
async def lovelace_ready(hass: HomeAssistant):
    """Make sure Lovelace is set up before each test."""
    await async_setup_component(hass, "lovelace", {})
    return hass


def _dashboards(hass: HomeAssistant):
    data = hass.data["lovelace"]
    return data["dashboards"] if isinstance(data, dict) else data.dashboards


async def test_dashboard_registered_after_setup_entry(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """The dashboard panel + Lovelace config entry are created on setup."""
    panels = hass.data.get("frontend_panels", {})
    assert NINA_DASHBOARD_URL_PATH in panels
    panel = panels[NINA_DASHBOARD_URL_PATH]
    assert panel.sidebar_title == NINA_DASHBOARD_TITLE
    dashboards = _dashboards(hass)
    assert isinstance(dashboards[NINA_DASHBOARD_URL_PATH], NinaLovelaceConfig)


async def test_dashboard_load_returns_views(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    cfg = _dashboards(hass)[NINA_DASHBOARD_URL_PATH]
    loaded = await cfg.async_load(force=False)
    assert "views" in loaded and isinstance(loaded["views"], list)
    info = await cfg.async_get_info()
    assert info["mode"] == "generated"


async def test_dashboard_async_json_returns_fragment(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    """Regression: LovelaceConfig.async_json is abstract — must be implemented."""
    cfg = _dashboards(hass)[NINA_DASHBOARD_URL_PATH]
    fragment = await cfg.async_json(force=False)
    # async_json must succeed and return some kind of value (json_fragment).
    # The exact type depends on HA version; what matters is no abstract-method
    # error and no crash.
    assert fragment is not None


async def test_dashboard_rebuilds_on_each_load(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    cfg = _dashboards(hass)[NINA_DASHBOARD_URL_PATH]
    with patch(
        "custom_components.nina_polaris.nina_lovelace.build_dashboard_config",
        return_value={"views": [{"title": "fresh"}]},
    ) as mock_build:
        await cfg.async_load(force=False)
        await cfg.async_load(force=False)
    assert mock_build.call_count == 2


async def test_register_is_idempotent(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    async_register_dashboard(hass)
    async_register_dashboard(hass)
    assert NINA_DASHBOARD_URL_PATH in hass.data.get("frontend_panels", {})


async def test_unregister_removes_panel(hass: HomeAssistant, lovelace_ready, mock_config_entry) -> None:
    async_unregister_dashboard(hass)
    assert NINA_DASHBOARD_URL_PATH not in hass.data.get("frontend_panels", {})
    assert NINA_DASHBOARD_URL_PATH not in _dashboards(hass)
