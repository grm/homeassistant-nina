"""NINA REST API client."""

import logging
from typing import Any

import aiohttp

from .const import API_BASE_PATH

_LOGGER = logging.getLogger(__name__)


class NinaApiClient:
    """Client to interact with the NINA REST API."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the API client."""
        self.base_url = f"http://{host}:{port}{API_BASE_PATH}"
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def _get(self, path: str) -> Any:
        """Make a GET request to the NINA API."""
        url = f"{self.base_url}{path}"
        _LOGGER.debug("GET %s", url)
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
            if not data.get("Success", False):
                _LOGGER.debug("API error on %s: %s", path, data.get("Error"))
                raise NinaApiError(data.get("Error", "Unknown error"))
            _LOGGER.debug("API response from %s: keys=%s", path, _summarize(data.get("Response")))
            return data.get("Response")

    async def get_version(self) -> str:
        return await self._get("/version")

    async def get_nina_version(self) -> str:
        return await self._get("/version/nina")

    async def get_equipment_info(self) -> dict[str, Any]:
        return await self._get("/equipment/info")

    async def get_sequence_state(self) -> list[dict[str, Any]]:
        return await self._get("/sequence/state")

    async def get_camera_info(self) -> dict[str, Any]:
        return await self._get("/equipment/camera/info")

    async def get_mount_info(self) -> dict[str, Any]:
        return await self._get("/equipment/mount/info")

    async def get_guider_info(self) -> dict[str, Any]:
        return await self._get("/equipment/guider/info")

    async def get_focuser_info(self) -> dict[str, Any]:
        return await self._get("/equipment/focuser/info")

    async def get_weather_info(self) -> dict[str, Any]:
        return await self._get("/equipment/weather/info")

    async def get_image_history(self) -> list[dict[str, Any]]:
        return await self._get("/image-history")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()


def _summarize(obj: Any) -> str:
    """Summarize response for debug logging."""
    if isinstance(obj, dict):
        return str(list(obj.keys()))
    if isinstance(obj, list):
        return f"list[{len(obj)} items]"
    return repr(obj)[:100]


class NinaApiError(Exception):
    """Exception for NINA API errors."""
