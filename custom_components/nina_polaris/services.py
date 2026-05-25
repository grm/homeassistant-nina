"""Services for NINA Polaris.

Parameterized actions invoked via `nina_polaris.<service_name>`.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DEFAULT_COOLER_TARGET_TEMP, DOMAIN

if TYPE_CHECKING:
    from .coordinator import NinaCoordinator

_LOGGER = logging.getLogger(__name__)

ATTR_CONFIG_ENTRY = "config_entry"
ATTR_TEMPERATURE = "temperature"
ATTR_DURATION = "duration"
ATTR_MODE = "mode"
ATTR_SKIP_VALIDATION = "skip_validation"

SERVICE_COOL_CAMERA = "cool_camera"
SERVICE_WARM_CAMERA = "warm_camera"
SERVICE_SET_TRACKING = "set_tracking"
SERVICE_START_SEQUENCE = "start_sequence"
SERVICE_STOP_SEQUENCE = "stop_sequence"
SERVICE_PARK_MOUNT = "park_mount"
SERVICE_UNPARK_MOUNT = "unpark_mount"
SERVICE_START_AUTOFOCUS = "start_autofocus"
SERVICE_CANCEL_AUTOFOCUS = "cancel_autofocus"
SERVICE_PLATE_SOLVE = "plate_solve"

TRACKING_MODES: dict[str, int] = {
    "sidereal": 0,
    "lunar": 1,
    "solar": 2,
    "king": 3,
    "stopped": 4,
}

_BASE_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY): cv.string})

COOL_CAMERA_SCHEMA = _BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_TEMPERATURE, default=DEFAULT_COOLER_TARGET_TEMP): vol.All(
            vol.Coerce(float), vol.Range(min=-50, max=30)
        ),
        vol.Optional(ATTR_DURATION, default=-1): vol.All(vol.Coerce(float), vol.Range(min=-1, max=120)),
    }
)

WARM_CAMERA_SCHEMA = _BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_DURATION, default=-1): vol.All(vol.Coerce(float), vol.Range(min=-1, max=120)),
    }
)

SET_TRACKING_SCHEMA = _BASE_SCHEMA.extend(
    {
        vol.Required(ATTR_MODE): vol.In(list(TRACKING_MODES)),
    }
)

START_SEQUENCE_SCHEMA = _BASE_SCHEMA.extend(
    {
        vol.Optional(ATTR_SKIP_VALIDATION, default=False): cv.boolean,
    }
)


def _resolve_coordinator(hass: HomeAssistant, call: ServiceCall) -> NinaCoordinator:
    entry_id = call.data.get(ATTR_CONFIG_ENTRY)
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    if not entries:
        raise HomeAssistantError("No loaded NINA Polaris config entry found")
    if entry_id is not None:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry.runtime_data  # type: ignore[no-any-return]
        raise HomeAssistantError(f"Config entry '{entry_id}' is not a loaded NINA Polaris entry")
    if len(entries) > 1:
        raise HomeAssistantError("Multiple NINA Polaris instances configured \u2014 pass config_entry")
    return entries[0].runtime_data  # type: ignore[no-any-return]


async def _run(coordinator: NinaCoordinator, action_name: str, fn_name: str, **kwargs: Any) -> None:
    method = getattr(coordinator.api_client, fn_name)
    try:
        await method(**kwargs)
    except Exception as err:  # noqa: BLE001
        raise HomeAssistantError(f"{action_name} failed: {err}") from err
    await coordinator.async_request_refresh()


async def _cool_camera(hass: HomeAssistant, call: ServiceCall) -> None:
    coord = _resolve_coordinator(hass, call)
    await _run(
        coord, "cool_camera", "camera_cool", temperature=call.data[ATTR_TEMPERATURE], minutes=call.data[ATTR_DURATION]
    )


async def _warm_camera(hass: HomeAssistant, call: ServiceCall) -> None:
    coord = _resolve_coordinator(hass, call)
    await _run(coord, "warm_camera", "camera_warm", minutes=call.data[ATTR_DURATION])


async def _set_tracking(hass: HomeAssistant, call: ServiceCall) -> None:
    coord = _resolve_coordinator(hass, call)
    await _run(coord, "set_tracking", "mount_set_tracking", mode=TRACKING_MODES[call.data[ATTR_MODE]])


async def _start_sequence(hass: HomeAssistant, call: ServiceCall) -> None:
    coord = _resolve_coordinator(hass, call)
    await _run(coord, "start_sequence", "sequence_start", skip_validation=call.data[ATTR_SKIP_VALIDATION])


def _make_simple(action_name: str, fn_name: str):
    async def _handler(hass: HomeAssistant, call: ServiceCall) -> None:
        coord = _resolve_coordinator(hass, call)
        await _run(coord, action_name, fn_name)

    return _handler


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_COOL_CAMERA):
        return

    def reg(name: str, handler, schema):
        hass.services.async_register(DOMAIN, name, partial(handler, hass), schema=schema)

    reg(SERVICE_COOL_CAMERA, _cool_camera, COOL_CAMERA_SCHEMA)
    reg(SERVICE_WARM_CAMERA, _warm_camera, WARM_CAMERA_SCHEMA)
    reg(SERVICE_SET_TRACKING, _set_tracking, SET_TRACKING_SCHEMA)
    reg(SERVICE_START_SEQUENCE, _start_sequence, START_SEQUENCE_SCHEMA)
    reg(SERVICE_STOP_SEQUENCE, _make_simple("stop_sequence", "sequence_stop"), _BASE_SCHEMA)
    reg(SERVICE_PARK_MOUNT, _make_simple("park_mount", "mount_park"), _BASE_SCHEMA)
    reg(SERVICE_UNPARK_MOUNT, _make_simple("unpark_mount", "mount_unpark"), _BASE_SCHEMA)
    reg(SERVICE_START_AUTOFOCUS, _make_simple("start_autofocus", "autofocus_start"), _BASE_SCHEMA)
    reg(SERVICE_CANCEL_AUTOFOCUS, _make_simple("cancel_autofocus", "autofocus_cancel"), _BASE_SCHEMA)
    reg(SERVICE_PLATE_SOLVE, _make_simple("plate_solve", "plate_solve"), _BASE_SCHEMA)
