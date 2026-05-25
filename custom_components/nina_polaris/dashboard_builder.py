"""Generate a native Lovelace dashboard config for NINA Polaris instances.

Produces a plain dict matching the Lovelace storage schema. No JS, no custom
cards required — every card type used is built into Home Assistant Core.

If `use_mushroom=True`, swaps a few cards for Mushroom variants. Mushroom is
optional; default output works with a fresh HA install.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN


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


def _instance_label(hass: HomeAssistant, entry_id: str) -> str:
    """Human-friendly label for one NINA instance."""
    device_reg = dr.async_get(hass)
    for device in device_reg.devices.values():
        if (DOMAIN, entry_id) in device.identifiers:
            return device.name_by_user or device.name or "NINA"
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is not None and entry.title:
        return entry.title
    return "NINA"


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


def _build_view(
    hass: HomeAssistant,
    entry_id: str,
    *,
    use_mushroom: bool = False,
) -> dict[str, Any]:
    """Build one Lovelace view for a single NINA instance.

    Layout uses HA's multi-column 'sections' view (HA 2024.3+) so the dashboard
    reflows from 3 columns on desktop to 1 column on mobile. Sections:

      1. Environment — Weather + Safety (left column on desktop)
      2. Imaging     — Camera image, Camera tiles, Sequence (middle column)
      3. Pointing    — Mount status + Park/Unpark, Guiding, Focuser, Equipment
                       (right column)
    """
    label = _instance_label(hass, entry_id)
    ents = _entities_for_entry(hass, entry_id)

    # ---- Environment section -------------------------------------------- #
    env_cards: list[dict[str, Any]] = []
    weather_layout: list[tuple[str, str, str, str]] = [
        ("weather_temperature", "Temp", "mdi:thermometer", "orange"),
        ("weather_humidity", "Humidity", "mdi:water-percent", "light-blue"),
        ("weather_pressure", "Pressure", "mdi:gauge", "blue-grey"),
        ("weather_dewpoint", "Dew point", "mdi:water", "cyan"),
        ("weather_wind_speed", "Wind", "mdi:weather-windy", "teal"),
        ("weather_sky_quality", "SQM", "mdi:weather-night", "indigo"),
        ("weather_sky_temperature", "Sky temp", "mdi:weather-cloudy", "deep-purple"),
    ]
    weather_tiles = [
        _tile(ents[key], lbl, icon=icon, color=color) for key, lbl, icon, color in weather_layout if key in ents
    ]
    if weather_tiles:
        env_cards.append({"type": "heading", "heading": "Weather", "heading_style": "title"})
        env_cards.append(_tile_grid(weather_tiles, columns=2))
    if "safety_is_safe" in ents:
        env_cards.append({"type": "heading", "heading": "Safety", "heading_style": "title"})
        env_cards.append(_tile(ents["safety_is_safe"], "Safe to image", icon="mdi:shield-check", color="green"))

    # ---- Imaging section ------------------------------------------------- #
    img_cards: list[dict[str, Any]] = []
    registry = er.async_get(hass)
    cam_eid = None
    for entry in registry.entities.values():
        if entry.platform == DOMAIN and entry.config_entry_id == entry_id and entry.domain == Platform.CAMERA:
            cam_eid = entry.entity_id
            break
    img_cards.append({"type": "heading", "heading": "Camera", "heading_style": "title"})
    if cam_eid:
        img_cards.append(_picture_entity(cam_eid, "Latest image"))

    cam_tiles: list[dict[str, Any]] = []
    if "camera_temperature" in ents:
        cam_tiles.append(_tile(ents["camera_temperature"], "Sensor", icon="mdi:thermometer", color="cyan"))
    if "camera_cooler_power" in ents:
        cam_tiles.append(_tile(ents["camera_cooler_power"], "Cooler power", icon="mdi:snowflake", color="light-blue"))
    if "camera_cooler_on" in ents:
        cam_tiles.append(_tile(ents["camera_cooler_on"], "Cooler", icon="mdi:snowflake-thermometer", color="blue"))
    if "camera_exposing" in ents:
        cam_tiles.append(_tile(ents["camera_exposing"], "Exposing", icon="mdi:camera-iris", color="amber"))
    if cam_tiles:
        img_cards.append(_tile_grid(cam_tiles, columns=2))

    if any(k in ents for k in ("focuser_position", "focuser_temperature")):
        img_cards.append({"type": "heading", "heading": "Focuser", "heading_style": "title"})
        focus_tiles: list[dict[str, Any]] = []
        if "focuser_position" in ents:
            focus_tiles.append(_tile(ents["focuser_position"], "Position", icon="mdi:focus-field", color="purple"))
        if "focuser_temperature" in ents:
            focus_tiles.append(_tile(ents["focuser_temperature"], "Temperature", icon="mdi:thermometer", color="cyan"))
        if focus_tiles:
            img_cards.append(_tile_grid(focus_tiles, columns=2))

    if any(k in ents for k in ("sequence_running", "sequence_target", "sequence_start", "sequence_stop")):
        img_cards.append({"type": "heading", "heading": "Sequence", "heading_style": "title"})
        seq_status_tiles: list[dict[str, Any]] = []
        if "sequence_running" in ents:
            seq_status_tiles.append(_tile(ents["sequence_running"], "Running", icon="mdi:play-circle", color="green"))
        if "sequence_target" in ents:
            seq_status_tiles.append(_tile(ents["sequence_target"], "Target", icon="mdi:bullseye-arrow", color="indigo"))
        if seq_status_tiles:
            img_cards.append(_tile_grid(seq_status_tiles, columns=2))

        seq_action_tiles: list[dict[str, Any]] = []
        if "sequence_start" in ents:
            seq_action_tiles.append(
                _tile(ents["sequence_start"], "Start", icon="mdi:play", color="green", hide_state=True)
            )
        if "sequence_stop" in ents:
            seq_action_tiles.append(_tile(ents["sequence_stop"], "Stop", icon="mdi:stop", color="red", hide_state=True))
        if seq_action_tiles:
            img_cards.append(_tile_grid(seq_action_tiles, columns=2))

    # ---- Pointing section (Mount + Guiding + Focuser + Equipment) -------- #
    point_cards: list[dict[str, Any]] = []
    point_cards.append({"type": "heading", "heading": "Mount", "heading_style": "title"})

    mount_tiles: list[dict[str, Any]] = []
    mount_layout: list[tuple[str, str, str, str | None]] = [
        ("mount_ra", "RA", "mdi:axis-x-rotate-clockwise", "indigo"),
        ("mount_dec", "Dec", "mdi:axis-y-rotate-clockwise", "indigo"),
        ("mount_altitude", "Altitude", "mdi:angle-acute", "blue-grey"),
        ("mount_azimuth", "Azimuth", "mdi:compass", "blue-grey"),
        ("mount_time_to_flip", "Meridian flip", "mdi:timer-sand", "amber"),
        ("mount_tracking", "Tracking", "mdi:target", "green"),
        ("mount_slewing", "Slewing", "mdi:rotate-orbit", "orange"),
    ]
    for key, lbl, icon, color in mount_layout:
        if key in ents:
            mount_tiles.append(_tile(ents[key], lbl, icon=icon, color=color))
    if mount_tiles:
        point_cards.append(_tile_grid(mount_tiles, columns=2))

    if any(k in ents for k in ("mount_park", "mount_unpark", "mount_at_park")):
        row: list[dict[str, Any]] = []
        if "mount_at_park" in ents:
            row.append(
                {
                    "type": "tile",
                    "entity": ents["mount_at_park"],
                    "name": "Parked",
                    "icon": "mdi:parking",
                    "color": "amber",
                    "vertical": False,
                }
            )
        if "mount_park" in ents:
            row.append(
                {
                    "type": "tile",
                    "entity": ents["mount_park"],
                    "name": "Park",
                    "icon": "mdi:car-brake-parking",
                    "color": "red",
                    "hide_state": True,
                }
            )
        if "mount_unpark" in ents:
            row.append(
                {
                    "type": "tile",
                    "entity": ents["mount_unpark"],
                    "name": "Unpark",
                    "icon": "mdi:telescope",
                    "color": "green",
                    "hide_state": True,
                }
            )
        point_cards.append({"type": "horizontal-stack", "cards": row})

    guide_keys = ("guider_ra_distance", "guider_dec_distance")
    guide_entities = [ents[k] for k in guide_keys if k in ents]
    if guide_entities:
        point_cards.append({"type": "heading", "heading": "Guiding", "heading_style": "title"})
        guide_tiles: list[dict[str, Any]] = []
        if "guider_ra_distance" in ents:
            guide_tiles.append(_tile(ents["guider_ra_distance"], "RA error", icon="mdi:arrow-left-right", color="blue"))
        if "guider_dec_distance" in ents:
            guide_tiles.append(_tile(ents["guider_dec_distance"], "Dec error", icon="mdi:arrow-up-down", color="amber"))
        if guide_tiles:
            point_cards.append(_tile_grid(guide_tiles, columns=2))
        point_cards.append(_history_card("Guiding error (arcsec)", guide_entities, hours=2))

    # Equipment connection state — shown above Weather in the Environment column.
    connect_keys: list[tuple[str, str]] = [
        ("camera_connected", "Camera"),
        ("mount_connected", "Mount"),
        ("guider_connected", "Guider"),
        ("focuser_connected", "Focuser"),
        ("filterwheel_connected", "Filter wheel"),
        ("rotator_connected", "Rotator"),
        ("dome_connected", "Dome"),
        ("weather_connected", "Weather"),
        ("safety_monitor_connected", "Safety monitor"),
    ]
    connect_rows = [{"entity": ents[key], "name": lbl} for key, lbl in connect_keys if key in ents]
    equipment_card: dict[str, Any] | None = None
    if connect_rows:
        equipment_card = {
            "type": "entities",
            "title": "Equipment",
            "show_header_toggle": False,
            "state_color": True,
            "entities": connect_rows,
        }

    # Optional Mushroom replacement of the Equipment list with a chips card.
    if use_mushroom and connect_rows:
        equipment_card = {
            "type": "custom:mushroom-chips-card",
            "chips": [
                {"type": "entity", "entity": row["entity"], "icon_color": "blue", "content_info": "name"}
                for row in connect_rows
            ],
        }
    if equipment_card is not None:
        # Equipment list shown ABOVE Weather in the Environment column.
        env_cards.insert(0, {"type": "heading", "heading": "Equipment", "heading_style": "title"})
        # The 'entities' card already has its own "Equipment" title; drop it to
        # avoid duplication with the heading card.
        if equipment_card.get("type") == "entities":
            equipment_card.pop("title", None)
        env_cards.insert(1, equipment_card)

    # ---- Assemble multi-column 'sections' view --------------------------- #
    sections: list[dict[str, Any]] = []
    if env_cards:
        sections.append({"type": "grid", "cards": env_cards, "column_span": 1})
    # img_cards always has at least the Camera heading; only emit it if it has
    # real content (more than just the heading).
    if len(img_cards) > 1:
        sections.append({"type": "grid", "cards": img_cards, "column_span": 1})
    if len(point_cards) > 1:
        sections.append({"type": "grid", "cards": point_cards, "column_span": 1})

    if not sections:
        sections.append(
            {
                "type": "grid",
                "cards": [
                    _markdown(
                        "_No NINA entities detected yet. Make sure NINA is running and the integration is connected._"
                    )
                ],
                "column_span": 1,
            }
        )

    return {
        "title": label,
        "path": f"nina-{entry_id[:8]}",
        "icon": "mdi:telescope",
        "type": "sections",
        "max_columns": 3,
        "sections": sections,
    }


def build_dashboard_config(
    hass: HomeAssistant,
    *,
    entry_id: str | None = None,
    entry_ids: list[str] | None = None,
    use_mushroom: bool = False,
) -> dict[str, Any]:
    """Build the full Lovelace storage config (views[]).

    Three modes:
      - `entry_id` set → single-instance dashboard (1 view, used by per-entry
        sidebars). This is the v0.2+ default.
      - `entry_ids` set → multi-instance dashboard (N views, kept for the
        umbrella dashboard during migration).
      - both None → every loaded NINA Polaris entry, multi-view.
    """
    if entry_id is not None:
        label = _instance_label(hass, entry_id)
        return {
            "title": label,
            "views": [_build_view(hass, entry_id, use_mushroom=use_mushroom)],
        }

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

    return {
        "title": "NINA Polaris",
        "views": [_build_view(hass, eid, use_mushroom=use_mushroom) for eid in entry_ids],
    }
