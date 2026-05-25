"""Tests for NINA config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType

from custom_components.nina_astro.config_flow import NinaConfigFlow
from custom_components.nina_astro.const import CONF_PORT, DEFAULT_PORT, DOMAIN


@pytest.fixture
def config_flow():
    flow = NinaConfigFlow()
    flow.hass = AsyncMock()
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = AsyncMock()
    flow.async_create_entry = AsyncMock(
        return_value={"type": FlowResultType.CREATE_ENTRY}
    )
    flow.async_show_form = AsyncMock(
        return_value={"type": FlowResultType.FORM}
    )
    return flow


@pytest.mark.asyncio
async def test_step_user_shows_form(config_flow):
    """Test that the user step shows a form when no input is given."""
    result = await config_flow.async_step_user(user_input=None)
    config_flow.async_show_form.assert_called_once()


@pytest.mark.asyncio
async def test_step_user_success(config_flow):
    """Test successful connection creates an entry."""
    with patch.object(config_flow, "_test_connection", new_callable=AsyncMock):
        result = await config_flow.async_step_user(
            user_input={CONF_HOST: "192.168.1.100", CONF_PORT: DEFAULT_PORT}
        )

    config_flow.async_set_unique_id.assert_called_once_with("nina_192.168.1.100_1888")
    config_flow.async_create_entry.assert_called_once_with(
        title="NINA (192.168.1.100:1888)",
        data={CONF_HOST: "192.168.1.100", CONF_PORT: DEFAULT_PORT},
    )


@pytest.mark.asyncio
async def test_step_user_cannot_connect(config_flow):
    """Test that connection failure shows an error."""
    with patch.object(
        config_flow,
        "_test_connection",
        new_callable=AsyncMock,
        side_effect=aiohttp.ClientError("Connection refused"),
    ):
        result = await config_flow.async_step_user(
            user_input={CONF_HOST: "badhost", CONF_PORT: DEFAULT_PORT}
        )

    config_flow.async_show_form.assert_called_once()
    call_kwargs = config_flow.async_show_form.call_args[1]
    assert call_kwargs["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_step_user_timeout(config_flow):
    """Test that timeout shows connection error."""
    with patch.object(
        config_flow,
        "_test_connection",
        new_callable=AsyncMock,
        side_effect=TimeoutError(),
    ):
        result = await config_flow.async_step_user(
            user_input={CONF_HOST: "slowhost", CONF_PORT: DEFAULT_PORT}
        )

    call_kwargs = config_flow.async_show_form.call_args[1]
    assert call_kwargs["errors"] == {"base": "cannot_connect"}


@pytest.mark.asyncio
async def test_test_connection_success():
    """Test _test_connection with a successful response."""
    flow = NinaConfigFlow()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        await flow._test_connection("localhost", 1888)

    mock_session.get.assert_called_once()
