"""Generate a native Lovelace dashboard config for NINA Polaris instances.

Produces a plain dict matching the Lovelace storage schema. No JS, no custom
cards required — every card type used is built into Home Assistant Core.

If `use_mushroom=True`, swaps a few cards for Mushroom variants. Mushroom is
optional; default output works with a fresh HA install.
"""

from __future__ import annotations

import re
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_MONITORING_CAMERA_ENTITY, DOMAIN


def _monitoring_camera_entity(hass: HomeAssistant, entry_id: str) -> str | None:
    """Return the optional monitoring camera entity_id from this entry's options."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return None
    value = entry.options.get(CONF_MONITORING_CAMERA_ENTITY)
    if isinstance(value, str) and value.startswith("camera."):
        return value
    return None


def _entities_for_entry(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Return a map of entity_key -> entity_id for one config entry.

    `entity_key` is the key passed to EntityDescription (e.g. `camera_temperature`).
    We extract it from `unique_id` which we build as `{entry_id}_{key}`.
    """
    registry = er.async_get(hass)
    out: dict[str, str] = {}
    prefix = f"{entry_id}_"
    for entry in registry.entities.values():
        if entry.platform != DOMAIN or entry.config_entry_id != entry_id:
            continue
        unique = entry.unique_id or ""
        if unique.startswith(prefix):
            key = unique[len(prefix) :]
            out[key] = entry.entity_id
    return out


def _path_slug(value: str) -> str:
    """Lowercase path fragment. The entry id after it keeps the path unique."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "nina"


def _instance_label(hass: HomeAssistant, entry_id: str) -> str:
    """Human-friendly label for one NINA instance.

    A user rename wins. Otherwise the config entry title (the NINA profile
    name) wins over the device name, which used to be the generic "NINA"
    for every hub.
    """
    entry = hass.config_entries.async_get_entry(entry_id)
    title = entry.title if entry is not None and entry.title else None
    name_by_user: str | None = None
    device_name: str | None = None
    device_reg = dr.async_get(hass)
    for device in device_reg.devices.values():
        if (DOMAIN, entry_id) in device.identifiers:
            name_by_user = device.name_by_user
            device_name = device.name
            break
    if name_by_user:
        return name_by_user
    if title:
        return title
    return device_name or "NINA"


# --------------------------------------------------------------------------- #
# Card builders                                                                #
# --------------------------------------------------------------------------- #


def _entities_card(title: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "entities", "title": title, "entities": rows}


def _glance_card(title: str, entity_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "glance",
        "title": title,
        "show_state": True,
        "entities": [{"entity": e} for e in entity_ids],
    }


def _gauge_card(entity_id: str, name: str, **opts: Any) -> dict[str, Any]:
    card = {"type": "gauge", "entity": entity_id, "name": name}
    card.update(opts)
    return card


def _history_card(title: str, entity_ids: list[str], hours: int = 6) -> dict[str, Any]:
    return {
        "type": "history-graph",
        "title": title,
        "hours_to_show": hours,
        "entities": [{"entity": e} for e in entity_ids],
    }


def _picture_entity(entity_id: str, name: str) -> dict[str, Any]:
    return {
        "type": "picture-entity",
        "entity": entity_id,
        "camera_view": "auto",
        "name": name,
        "show_state": False,
        "show_name": True,
    }


def _conditional(condition: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    return {"type": "conditional", "conditions": [condition], "card": card}


def _markdown(content: str) -> dict[str, Any]:
    return {"type": "markdown", "content": content}


# --------------------------------------------------------------------------- #
# Tile helpers (Option 1 visual: clean grid of tiles, no "Trevinca" prefix)   #
# --------------------------------------------------------------------------- #

# HA tile colors: red, pink, purple, deep-purple, indigo, blue, light-blue,
# cyan, teal, green, light-green, lime, yellow, amber, orange, deep-orange,
# brown, light-grey, grey, dark-grey, blue-grey, black, disabled, white.


def _tile(
    entity_id: str,
    name: str,
    *,
    icon: str | None = None,
    color: str | None = None,
    hide_state: bool = False,
    vertical: bool = True,
    tap_action: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Native HA `tile` card with a friendly label + optional icon override."""
    card: dict[str, Any] = {
        "type": "tile",
        "entity": entity_id,
        "name": name,
        "vertical": vertical,
    }
    if icon is not None:
        card["icon"] = icon
    if color is not None:
        card["color"] = color
    if hide_state:
        card["hide_state"] = True
    if tap_action is not None:
        card["tap_action"] = tap_action
    return card


def _tile_grid(cards: list[dict[str, Any]], columns: int = 2) -> dict[str, Any]:
    """Wrap tiles in a `grid` card (or `horizontal-stack` for 2)."""
    if not cards:
        return {}
    if len(cards) == 1:
        return cards[0]
    return {
        "type": "grid",
        "columns": columns,
        "square": False,
        "cards": cards,
    }


def _section(title: str, *bodies: dict[str, Any]) -> list[dict[str, Any]]:
    """Emit a heading card followed by content cards, filtering empties."""
    out: list[dict[str, Any]] = [{"type": "heading", "heading": title, "heading_style": "title"}]
    out.extend(b for b in bodies if b)
    return out


# Sidebar dashboard url. View navigation paths are rooted here.
DASHBOARD_URL_PATH = "nina"
MENU_PATH = "home"

# A sections view with max_columns 1 stays one narrow column and leaves the
# rest of the screen empty. Every band spans the full view instead.
# The section grid is 12 columns: info tiles are six across, actions four.
_VIEW_COLUMNS = 4
_TILE_COLUMNS = 2
_ACTION_COLUMNS = 3


def _with_grid(card: dict[str, Any], columns: int | str, rows: int | None = None) -> dict[str, Any]:
    """Attach a section-grid size so neighbouring cards share a column rhythm."""
    opts: dict[str, Any] = {"columns": columns}
    if rows is not None:
        opts["rows"] = rows
    card["grid_options"] = opts
    return card


def _heading(text: str, *, style: str = "title") -> dict[str, Any]:
    return _with_grid(
        {"type": "heading", "heading": text, "heading_style": style},
        "full",
    )


def _press_action(entity_id: str, confirm: str | None = None) -> dict[str, Any]:
    """Tap action that presses a button entity, optionally after a confirmation."""
    action: dict[str, Any] = {
        "action": "perform-action",
        "perform_action": "button.press",
        "target": {"entity_id": entity_id},
    }
    if confirm:
        action["confirmation"] = {"text": confirm}
    return action


def _status_tile(
    entity_id: str,
    name: str,
    *,
    icon: str,
    color: str | None = None,
    columns: int = _TILE_COLUMNS,
) -> dict[str, Any]:
    return _with_grid(
        _tile(entity_id, name, icon=icon, color=color, vertical=True),
        columns,
        rows=2,
    )


def _action_tile(
    entity_id: str,
    name: str,
    *,
    icon: str,
    color: str,
    confirm: str | None = None,
) -> dict[str, Any]:
    return _with_grid(
        _tile(
            entity_id,
            name,
            icon=icon,
            color=color,
            hide_state=True,
            vertical=False,
            tap_action=_press_action(entity_id, confirm),
        ),
        _ACTION_COLUMNS,
        rows=1,
    )


def _tiles_for(
    ents: dict[str, str],
    layout: list[tuple[str, str, str, str | None]],
    *,
    columns: int = _TILE_COLUMNS,
) -> list[dict[str, Any]]:
    return [
        _status_tile(ents[key], label, icon=icon, color=color, columns=columns)
        for key, label, icon, color in layout
        if key in ents
    ]


def _actions_for(
    ents: dict[str, str],
    layout: list[tuple[str, str, str, str, str | None]],
) -> list[dict[str, Any]]:
    """Build equal-width action tiles. Last field is the confirmation text."""
    return [
        _action_tile(ents[key], label, icon=icon, color=color, confirm=confirm)
        for key, label, icon, color, confirm in layout
        if key in ents
    ]


def _band(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """One full-width section. column_span fills the view so tiles aren't stuck in a narrow column."""
    return {"type": "grid", "column_span": _VIEW_COLUMNS, "cards": cards}


def _image_spacer() -> dict[str, Any]:
    """Empty side column so the image section sits in the middle on a wide screen.

    Hidden below 1200px, where the view is already a single column.
    """
    return {
        "type": "grid",
        "column_span": 1,
        "visibility": [{"condition": "screen", "media_query": "(min-width: 1200px)"}],
        "cards": [{"type": "heading", "heading": ""}],
    }


def _image_band(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """Half-width section. With a spacer on each side it lands in the middle."""
    return {"type": "grid", "column_span": 2, "cards": cards}


def _build_view(
    hass: HomeAssistant,
    entry_id: str,
    *,
    use_mushroom: bool = False,
) -> dict[str, Any]:
    """Build one Lovelace view for a single NINA instance.

    Full-width bands, top to bottom:

      1. Latest image
      2. Last image metrics
      3. What is currently being shot
      4. Sensor, mount, guiding, focuser, weather
      5. Which equipment is connected
      6. Capture actions, then dangerous actions with confirmation
    """
    label = _instance_label(hass, entry_id)
    ents = _entities_for_entry(hass, entry_id)
    bands: list[dict[str, Any]] = []

    registry = er.async_get(hass)
    cam_eid = None
    for entry in registry.entities.values():
        if entry.platform == DOMAIN and entry.config_entry_id == entry_id and entry.domain == Platform.CAMERA:
            cam_eid = entry.entity_id
            break

    pictures: list[dict[str, Any]] = []
    monitoring_entity = _monitoring_camera_entity(hass, entry_id)
    if cam_eid and monitoring_entity:
        pictures.append(_with_grid(_picture_entity(cam_eid, "Latest image"), 12, rows=6))
        pictures.append(
            _with_grid(
                {
                    "type": "picture-entity",
                    "entity": monitoring_entity,
                    "name": "Monitoring",
                    "show_state": False,
                    "show_name": True,
                    "camera_view": "live",
                },
                12,
                rows=6,
            )
        )
    elif cam_eid:
        pictures.append(_with_grid(_picture_entity(cam_eid, "Latest image"), "full", rows=6))
    elif monitoring_entity:
        pictures.append(
            _with_grid(
                {
                    "type": "picture-entity",
                    "entity": monitoring_entity,
                    "name": "Monitoring",
                    "show_state": False,
                    "show_name": True,
                    "camera_view": "live",
                },
                "full",
                rows=6,
            )
        )
    if pictures:
        # The latest image leads. A monitoring camera sits beside it and is
        # labelled on the card, so a heading does not push the image down.
        if monitoring_entity and not cam_eid:
            pictures.insert(0, _heading("Monitoring"))
        # Spacers flank the image on a wide screen so it sits in the middle.
        bands.append(_image_spacer())
        bands.append(_image_band(pictures))
        bands.append(_image_spacer())

    last_image_tiles = _tiles_for(
        ents,
        [
            ("latest_image_hfr", "HFR", "mdi:star-four-points", "amber"),
            ("latest_image_stars", "Stars", "mdi:star-shooting", "amber"),
            ("latest_image_filter", "Filter", "mdi:filter", "indigo"),
            ("latest_image_exposure_time", "Exposure", "mdi:timer-outline", "blue"),
            ("latest_image_guiding_rms", "Guiding RMS", "mdi:crosshairs", "green"),
            ("latest_image_temperature", "Sensor temp", "mdi:thermometer-low", "blue"),
            ("latest_image_mean", "Mean", "mdi:sigma-lower", "blue-grey"),
            ("latest_image_median", "Median", "mdi:sigma", "blue-grey"),
            ("latest_image_stdev", "Std dev", "mdi:chart-bell-curve", "blue-grey"),
        ],
    )
    if last_image_tiles:
        bands.append(_band([_heading("Last image"), *last_image_tiles]))

    shooting: list[dict[str, Any]] = []
    if "sequence_running" in ents:
        shooting.append(
            _status_tile(ents["sequence_running"], "Sequence", icon="mdi:play-circle", color="green", columns=3)
        )
    if "sequence_target" in ents:
        shooting.append(
            _status_tile(
                ents["sequence_target"],
                "Target",
                icon="mdi:bullseye-arrow",
                color="indigo",
                columns=6 if "sequence_running" in ents else 9,
            )
        )
    if "camera_exposing" in ents:
        shooting.append(
            _status_tile(ents["camera_exposing"], "Exposing", icon="mdi:camera-iris", color="amber", columns=3)
        )
    if "safety_is_safe" in ents:
        shooting.append(_status_tile(ents["safety_is_safe"], "Safe", icon="mdi:shield-check", color="green", columns=3))
    if shooting:
        bands.append(_band([_heading("Shooting"), *shooting]))

    sensor_tiles = _tiles_for(
        ents,
        [
            ("camera_temperature", "Sensor", "mdi:thermometer", "cyan"),
            ("camera_cooler_power", "Cooler power", "mdi:snowflake", "light-blue"),
            ("camera_cooler_on", "Cooler", "mdi:snowflake-thermometer", "blue"),
        ],
        columns=4,
    )
    if sensor_tiles:
        bands.append(_band([_heading("Sensor"), *sensor_tiles]))

    mount_tiles = _tiles_for(
        ents,
        [
            ("mount_ra", "RA", "mdi:axis-x-rotate-clockwise", "indigo"),
            ("mount_dec", "Dec", "mdi:axis-y-rotate-clockwise", "indigo"),
            ("mount_altitude", "Altitude", "mdi:angle-acute", "blue-grey"),
            ("mount_azimuth", "Azimuth", "mdi:compass", "blue-grey"),
            ("mount_time_to_flip", "Meridian flip", "mdi:timer-sand", "amber"),
            ("mount_slewing", "Slewing", "mdi:rotate-orbit", "orange"),
            ("mount_tracking", "Tracking", "mdi:target", "green"),
            ("mount_at_park", "Parked", "mdi:parking", "amber"),
        ],
    )
    if mount_tiles:
        bands.append(_band([_heading("Mount"), *mount_tiles]))

    guide_entities = [ents[k] for k in ("guider_ra_distance", "guider_dec_distance") if k in ents]
    guide_tiles = _tiles_for(
        ents,
        [
            ("guider_ra_distance", "RA error", "mdi:arrow-left-right", "blue"),
            ("guider_dec_distance", "Dec error", "mdi:arrow-up-down", "amber"),
        ],
        columns=6,
    )
    guiding: list[dict[str, Any]] = []
    if guide_tiles or guide_entities:
        guiding.append(_heading("Guiding"))
        guiding.extend(guide_tiles)
        if guide_entities:
            guiding.append(_with_grid(_history_card("Guiding error (arcsec)", guide_entities, hours=2), 12, rows=4))
    if guiding:
        bands.append(_band(guiding))

    focus_tiles = _tiles_for(
        ents,
        [
            ("focuser_position", "Position", "mdi:focus-field", "purple"),
            ("focuser_temperature", "Temperature", "mdi:thermometer", "cyan"),
        ],
        columns=6,
    )
    if focus_tiles:
        bands.append(_band([_heading("Focuser"), *focus_tiles]))

    weather_tiles = _tiles_for(
        ents,
        [
            ("weather_temperature", "Temp", "mdi:thermometer", "orange"),
            ("weather_humidity", "Humidity", "mdi:water-percent", "light-blue"),
            ("weather_pressure", "Pressure", "mdi:gauge", "blue-grey"),
            ("weather_dewpoint", "Dew point", "mdi:water", "cyan"),
            ("weather_wind_speed", "Wind", "mdi:weather-windy", "teal"),
            ("weather_sky_quality", "SQM", "mdi:weather-night", "indigo"),
            ("weather_sky_temperature", "Sky temp", "mdi:weather-cloudy", "deep-purple"),
        ],
    )
    if weather_tiles:
        bands.append(_band([_heading("Weather"), *weather_tiles]))

    connect_keys: list[tuple[str, str]] = [
        ("camera_connected", "Camera"),
        ("mount_connected", "Mount"),
        ("focuser_connected", "Focuser"),
        ("guider_connected", "Guider"),
        ("filterwheel_connected", "Filter wheel"),
        ("rotator_connected", "Rotator"),
        ("dome_connected", "Dome"),
        ("weather_connected", "Weather"),
        ("safety_monitor_connected", "Safety monitor"),
    ]
    connect_rows = [{"entity": ents[key], "name": lbl} for key, lbl in connect_keys if key in ents]
    if connect_rows:
        if use_mushroom:
            equipment: list[dict[str, Any]] = [
                _heading("Equipment"),
                _with_grid(
                    {
                        "type": "custom:mushroom-chips-card",
                        "chips": [
                            {"type": "entity", "entity": row["entity"], "icon_color": "blue", "content_info": "name"}
                            for row in connect_rows
                        ],
                    },
                    12,
                ),
            ]
        else:
            equipment = [
                _heading("Equipment"),
                *[_status_tile(row["entity"], row["name"], icon="mdi:lan-connect") for row in connect_rows],
            ]
        bands.append(_band(equipment))

    # Capture stays in the middle. Dangerous actions are a separate block at
    # the bottom and always ask before they run.
    capture = _actions_for(
        ents,
        [
            ("sequence_start", "Start sequence", "mdi:play", "green", None),
            ("plate_solve", "Plate solve", "mdi:crosshairs-gps", "indigo", None),
            ("autofocus_start", "Autofocus", "mdi:focus-auto", "purple", None),
            ("guider_start", "Start guiding", "mdi:crosshairs", "green", None),
            ("mount_unpark", "Unpark", "mdi:telescope", "green", None),
            ("dome_open", "Open shutter", "mdi:window-open", "green", None),
            ("camera_connect", "Connect camera", "mdi:lan-connect", "teal", None),
            ("mount_connect", "Connect mount", "mdi:lan-connect", "teal", None),
            ("focuser_connect", "Connect focuser", "mdi:lan-connect", "teal", None),
            ("guider_connect", "Connect guider", "mdi:lan-connect", "teal", None),
            ("filterwheel_connect", "Connect filter wheel", "mdi:lan-connect", "teal", None),
            ("dome_connect", "Connect dome", "mdi:lan-connect", "teal", None),
        ],
    )
    danger = _actions_for(
        ents,
        [
            ("sequence_stop", "Stop sequence", "mdi:stop", "red", "Stop the running sequence?"),
            ("camera_abort_exposure", "Abort exposure", "mdi:camera-off", "red", "Abort the current exposure?"),
            ("mount_park", "Park mount", "mdi:car-brake-parking", "red", "Park the mount?"),
            ("guider_stop", "Stop guiding", "mdi:crosshairs-off", "red", "Stop guiding?"),
            ("dome_close", "Close shutter", "mdi:window-closed", "red", "Close the dome shutter?"),
            ("dome_park", "Park dome", "mdi:parking", "red", "Park the dome?"),
            ("camera_disconnect", "Disconnect camera", "mdi:lan-disconnect", "red", "Disconnect the camera?"),
            ("mount_disconnect", "Disconnect mount", "mdi:lan-disconnect", "red", "Disconnect the mount?"),
            ("focuser_disconnect", "Disconnect focuser", "mdi:lan-disconnect", "red", "Disconnect the focuser?"),
            ("guider_disconnect", "Disconnect guider", "mdi:lan-disconnect", "red", "Disconnect the guider?"),
            (
                "filterwheel_disconnect",
                "Disconnect filter wheel",
                "mdi:lan-disconnect",
                "red",
                "Disconnect the filter wheel?",
            ),
            ("dome_disconnect", "Disconnect dome", "mdi:lan-disconnect", "red", "Disconnect the dome?"),
        ],
    )

    if capture:
        bands.append(_band([_heading("Capture"), *capture]))
    if danger:
        bands.append(_band([_heading("Dangerous"), *danger]))

    if not bands:
        bands.append(
            _band(
                [
                    _markdown(
                        "_No NINA entities detected yet. Make sure NINA is running and the integration is connected._"
                    )
                ]
            )
        )

    return {
        "title": label,
        # The full entry id: two hubs created together share the first 8
        # characters of their ULID, so a short prefix made both menu links
        # open the same telescope.
        "path": f"nina-{_path_slug(label)}-{entry_id}",
        "icon": "mdi:telescope",
        "type": "sections",
        "max_columns": _VIEW_COLUMNS,
        "sections": bands,
    }


def _menu_view(views: list[dict[str, Any]]) -> dict[str, Any]:
    """Index view: one full-width row per telescope, stacked top to bottom."""
    buttons = [
        _with_grid(
            {
                "type": "button",
                "name": view["title"],
                "icon": "mdi:telescope",
                "show_name": True,
                "show_icon": True,
                "tap_action": {
                    "action": "navigate",
                    "navigation_path": f"/{DASHBOARD_URL_PATH}/{view['path']}",
                },
            },
            12,
            rows=1,
        )
        for view in views
    ]
    return {
        "title": "Telescopes",
        "path": MENU_PATH,
        "icon": "mdi:telescope",
        "type": "sections",
        "max_columns": _VIEW_COLUMNS,
        "sections": [_band([_heading("Telescopes"), *buttons])],
    }


def build_dashboard_config(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
    entry_ids: list[str] | None = None,
    use_mushroom: bool = False,
) -> dict[str, Any]:
    """Build the full Lovelace storage config (views[]).

    One sidebar dashboard. A single instance is the view itself. Several
    instances get an index view (telescopes stacked one under the other)
    and each telescope is a subview opened from that menu.

    Modes:
      - `entry_id` set → that instance only.
      - `entry_ids` set → those instances.
      - both None → every loaded NINA Polaris entry.
    """
    if entry_id is not None:
        entry_ids = [entry_id]

    if entry_ids is None:
        entry_ids = [
            e.entry_id for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
        ]

    if not entry_ids:
        return {
            "title": "NINA Polaris",
            "views": [
                {
                    "title": "NINA",
                    "path": "nina",
                    "icon": "mdi:telescope",
                    "cards": [
                        _markdown(
                            "### NINA Polaris\n\nNo NINA Polaris instance configured. "
                            "Add one in **Settings → Devices & Services**."
                        ),
                    ],
                }
            ],
        }

    views = [_build_view(hass, eid, use_mushroom=use_mushroom) for eid in entry_ids]
    if len(views) == 1:
        title = views[0]["title"] if entry_id is not None else "NINA Polaris"
        return {"title": title, "views": views}

    for view in views:
        view["subview"] = True
        view["back_path"] = f"/{DASHBOARD_URL_PATH}/{MENU_PATH}"
    return {"title": "NINA Polaris", "views": [_menu_view(views), *views]}
