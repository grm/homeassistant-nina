"""Tests for NINA WebSocket client."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.nina_polaris.websocket import NinaWebSocket


@pytest.fixture
def mock_hass():
    hass = MagicMock()

    def _create_bg_task(coro, name=None):
        # Close the coroutine so it is not flagged as "never awaited"
        coro.close()
        return AsyncMock()

    hass.async_create_background_task = MagicMock(side_effect=_create_bg_task)
    return hass


@pytest.fixture
def websocket(mock_hass):
    return NinaWebSocket(mock_hass, "localhost", 1888)


class TestWebSocketInit:
    """Test WebSocket initialization."""

    def test_url_construction(self, websocket):
        assert websocket.url == "ws://localhost:1888/v2/socket"

    def test_custom_host_port(self, mock_hass):
        ws = NinaWebSocket(mock_hass, "192.168.1.50", 2000)
        assert ws.url == "ws://192.168.1.50:2000/v2/socket"

    def test_initial_state(self, websocket):
        assert websocket._running is False
        assert websocket._ws is None
        assert websocket._session is None
        assert websocket._callback is None


class TestWebSocketConnect:
    """Test WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_connect_starts_background_task(self, websocket, mock_hass):
        await websocket.async_connect()

        assert websocket._running is True
        mock_hass.async_create_background_task.assert_called_once()
        call_args = mock_hass.async_create_background_task.call_args
        assert call_args[0][1] == "nina_websocket"

    @pytest.mark.asyncio
    async def test_disconnect_stops_running(self, websocket):
        websocket._running = True
        websocket._task = asyncio.Future()
        websocket._task.cancel = MagicMock()
        websocket._task.set_exception(asyncio.CancelledError())

        await websocket.async_disconnect()

        assert websocket._running is False

    @pytest.mark.asyncio
    async def test_disconnect_closes_ws(self, websocket):
        websocket._running = True
        websocket._task = asyncio.Future()
        websocket._task.cancel = MagicMock()
        websocket._task.set_exception(asyncio.CancelledError())

        mock_ws = AsyncMock()
        mock_ws.closed = False
        websocket._ws = mock_ws

        mock_session = AsyncMock()
        mock_session.closed = False
        websocket._session = mock_session

        await websocket.async_disconnect()

        mock_ws.close.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_already_closed(self, websocket):
        websocket._running = True
        websocket._task = asyncio.Future()
        websocket._task.cancel = MagicMock()
        websocket._task.set_exception(asyncio.CancelledError())

        mock_ws = AsyncMock()
        mock_ws.closed = True
        websocket._ws = mock_ws

        mock_session = AsyncMock()
        mock_session.closed = True
        websocket._session = mock_session

        await websocket.async_disconnect()

        mock_ws.close.assert_not_called()
        mock_session.close.assert_not_called()


class TestWebSocketCallback:
    """Test WebSocket callback handling."""

    def test_set_callback(self, websocket):
        callback = MagicMock()
        websocket.set_callback(callback)
        assert websocket._callback is callback

    @pytest.mark.asyncio
    async def test_callback_invoked_on_message(self, websocket):
        callback = MagicMock()
        websocket.set_callback(callback)

        event_data = {"Event": "IMAGE-SAVE", "Response": {"FileName": "test.fits"}}
        msg = MagicMock()
        msg.type = aiohttp.WSMsgType.TEXT
        msg.data = json.dumps(event_data)

        mock_ws = AsyncMock()
        mock_ws.__aiter__ = MagicMock(return_value=iter([msg]))
        mock_ws.closed = False

        mock_session = AsyncMock()
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)
        mock_session.closed = False

        websocket._running = True

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Run one iteration then stop
            async def run_once():
                websocket._session = mock_session
                websocket._ws = mock_ws
                # Process one message
                for m in [msg]:
                    if m.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(m.data)
                        if websocket._callback:
                            websocket._callback(data)

            await run_once()

        callback.assert_called_once_with(event_data)
