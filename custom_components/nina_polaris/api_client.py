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

    async def _get_bytes(self, path: str) -> bytes | None:
        """GET a binary endpoint (image), returns raw bytes or None on error."""
        url = f"{self.base_url}{path}"
        _LOGGER.debug("GET (bytes) %s", url)
        try:
            async with self.session.get(url) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    # Server returned the JSON envelope instead of the image (e.g. error)
                    _LOGGER.debug("Image endpoint returned non-image content-type: %s", content_type)
                    return None
                return await resp.read()
        except aiohttp.ClientError as err:
            _LOGGER.debug("Image fetch failed for %s: %s", path, err)
            return None

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
        return await self._get("/image-history?all=true")

    async def get_image_metadata(self, index: int) -> dict[str, Any] | None:
        """Fetch metadata for a single image at the given history index.

        NINA's `/image-history?index=N` returns either a single entry, a list
        with one entry, or an empty list — normalize to a dict-or-None.
        """
        result = await self._get(f"/image-history?index={index}")
        if isinstance(result, list):
            return result[0] if result else None
        if isinstance(result, dict):
            return result
        return None

    async def get_image_history_count(self) -> int:
        """Return the number of images in NINA's image history."""
        result = await self._get("/image-history?count=true")
        # NINA returns {"Count": N} or just an int depending on version
        if isinstance(result, dict):
            return int(result.get("Count", 0))
        if isinstance(result, int):
            return result
        return 0

    async def get_image_bytes(
        self,
        index: int,
        *,
        quality: int = 85,
        resize: bool = False,
        size: str | None = None,
    ) -> bytes | None:
        """Fetch a JPEG image from NINA at the given history index."""
        params = [f"quality={quality}"]
        if resize:
            params.append("resize=true")
            if size:
                params.append(f"size={size}")
        return await self._get_bytes(f"/image/{index}?{'&'.join(params)}")

    async def get_image_thumbnail(self, index: int) -> bytes | None:
        """Fetch the thumbnail for a given image history index."""
        return await self._get_bytes(f"/image/thumbnail/{index}")

    # --- Action endpoints (NINA exposes them as GET requests) ---

    async def mount_park(self) -> Any:
        return await self._get("/equipment/mount/park")

    async def mount_unpark(self) -> Any:
        return await self._get("/equipment/mount/unpark")

    async def mount_set_tracking(self, mode: int) -> Any:
        """Set the mount tracking mode (0=Sidereal, 1=Lunar, 2=Solar, 3=King, 4=Stopped)."""
        return await self._get(f"/equipment/mount/tracking?mode={mode}")

    async def sequence_start(self, *, skip_validation: bool = False) -> Any:
        suffix = "?skipValidation=true" if skip_validation else ""
        return await self._get(f"/sequence/start{suffix}")

    async def sequence_stop(self) -> Any:
        return await self._get("/sequence/stop")

    async def autofocus_start(self) -> Any:
        return await self._get("/equipment/focuser/auto-focus")

    async def autofocus_cancel(self) -> Any:
        return await self._get("/equipment/focuser/auto-focus?cancel=true")

    async def plate_solve(self) -> Any:
        """Capture an image and platesolve it (uses NINA's plate-solver settings)."""
        return await self._get("/equipment/camera/capture?solve=true&omitImage=true")

    async def camera_cool(self, temperature: float, minutes: float = -1) -> Any:
        return await self._get(f"/equipment/camera/cool?temperature={temperature}&minutes={minutes}")

    async def camera_warm(self, minutes: float = -1) -> Any:
        return await self._get(f"/equipment/camera/warm?minutes={minutes}")

    # --- Connect / disconnect (one method per device) ---

    async def device_connect(self, device: str) -> Any:
        """Connect a NINA device.

        ``device`` must be a NINA equipment slug:
        ``camera``, ``mount``, ``focuser``, ``guider``, ``filterwheel``,
        ``dome``, ``rotator``, ``flatdevice``, ``weather``, ``safetymonitor``,
        ``switch``.
        """
        return await self._get(f"/equipment/{device}/connect")

    async def device_disconnect(self, device: str) -> Any:
        """Disconnect a NINA device. See :meth:`device_connect` for slugs."""
        return await self._get(f"/equipment/{device}/disconnect")

    # --- Dome actions ---

    async def dome_open(self) -> Any:
        return await self._get("/equipment/dome/open")

    async def dome_close(self) -> Any:
        return await self._get("/equipment/dome/close")

    async def dome_park(self) -> Any:
        return await self._get("/equipment/dome/park")

    async def dome_stop(self) -> Any:
        return await self._get("/equipment/dome/stop")

    # --- Guider actions ---

    async def guider_start(self) -> Any:
        return await self._get("/equipment/guider/start")

    async def guider_stop(self) -> Any:
        return await self._get("/equipment/guider/stop")

    # --- Camera additional actions ---

    async def camera_abort_exposure(self) -> Any:
        return await self._get("/equipment/camera/abort-exposure")

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
