"""WebSocket client for NINA real-time events."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant

from .const import WS_PATH

_LOGGER = logging.getLogger(__name__)


class NinaWebSocket:
    """WebSocket client for NINA event stream."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize the WebSocket client."""
        self.hass = hass
        self.url = f"ws://{host}:{port}{WS_PATH}"
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._callback: Callable[[dict[str, Any]], None] | None = None
        self._task: asyncio.Task | None = None
        self._running = False

    def set_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Set the callback for incoming events."""
        self._callback = callback

    async def async_connect(self) -> None:
        """Connect to the NINA WebSocket."""
        self._running = True
        self._task = self.hass.async_create_background_task(
            self._listen(), "nina_websocket"
        )
        _LOGGER.debug("WebSocket connection task started for %s", self.url)

    async def _listen(self) -> None:
        """Listen for WebSocket messages with reconnection."""
        while self._running:
            try:
                self._session = aiohttp.ClientSession()
                _LOGGER.debug("Attempting WebSocket connection to %s", self.url)
                self._ws = await self._session.ws_connect(self.url)
                _LOGGER.info("Connected to NINA WebSocket at %s", self.url)

                async for msg in self._ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            event_type = data.get("Event", "unknown")
                            _LOGGER.debug(
                                "WebSocket message: event=%s, success=%s",
                                event_type,
                                data.get("Success"),
                            )
                            if self._callback:
                                self._callback(data)
                        except json.JSONDecodeError:
                            _LOGGER.debug("Invalid JSON from NINA WebSocket: %s", msg.data[:200])
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        _LOGGER.error("WebSocket error: %s", self._ws.exception())
                        break
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                        _LOGGER.debug("WebSocket connection closing")
                        break

            except (aiohttp.ClientError, asyncio.CancelledError) as err:
                if isinstance(err, asyncio.CancelledError):
                    _LOGGER.debug("WebSocket task cancelled")
                    return
                _LOGGER.warning("NINA WebSocket connection lost: %s. Reconnecting in 10s...", err)
            finally:
                if self._ws and not self._ws.closed:
                    await self._ws.close()
                if self._session and not self._session.closed:
                    await self._session.close()

            if self._running:
                _LOGGER.debug("WebSocket reconnecting in 10s...")
                await asyncio.sleep(10)

    async def async_disconnect(self) -> None:
        """Disconnect from the NINA WebSocket."""
        _LOGGER.debug("Disconnecting WebSocket")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()
        _LOGGER.debug("WebSocket disconnected")
