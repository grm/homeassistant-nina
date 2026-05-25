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


def _build_view(
    hass: HomeAssistant,
    entry_id: str,
    *,
    use_mushroom: bool = False,
) -> dict[str, Any]:
    """Build one Lovelace view (tab) for a single NINA instance."""
    label = _instance_label(hass, entry_id)
    ents = _entities_for_entry(hass, entry_id)

    cards: list[dict[str, Any]] = []

    # Header is intentionally minimal — the dashboard's own title (set via
    # the sidebar entry / page title) already shows the instance name.
    # We only emit a subtle subtitle on the first card.

    # ---- Equipment connection state -------------------------------------- #
    # One row per equipment: clean label on the left ("Camera", "Mount"…),
    # state on the right ("Connected" / "Disconnected"). No truncation, no
    # noisy "Trevinca …" prefix — the page title already says it.
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
    connect_rows = [
        {"entity": ents[key], "name": label} for key, label in connect_keys if key in ents
    ]
    if connect_rows:
        cards.append(
            {
                "type": "entities",
                "title": "Equipment",
                "show_header_toggle": False,
                "state_color": True,
                "entities": connect_rows,
            }
        )

    # ---- Camera ---------------------------------------------------------- #
    # Robust path: lookup by registry domain
    registry = er.async_get(hass)
    cam_eid = None
    for entry in registry.entities.values():
        if entry.platform == DOMAIN and entry.config_entry_id == entry_id and entry.domain == Platform.CAMERA:
            cam_eid = entry.entity_id
            break
    if cam_eid:
        cards.append(_picture_entity(cam_eid, "Latest image"))

    cam_status: list[dict[str, Any]] = []
    for key, _name in [
        ("camera_temperature", "Sensor temp"),
        ("camera_cooler_power", "Cooler power"),
    ]:
        if key in ents:
            cam_status.append({"entity": ents[key]})
    cooler_actions: list[dict[str, Any]] = []
    if "camera_cooler_on" in ents:
        cooler_actions.append({"entity": ents["camera_cooler_on"], "name": "Cooler"})
    if "camera_exposing" in ents:
        cooler_actions.append({"entity": ents["camera_exposing"], "name": "Exposing"})
    if cam_status or cooler_actions:
        cards.append(_entities_card("Camera", cam_status + cooler_actions))

    # ---- Mount ----------------------------------------------------------- #
    mount_status = []
    for key in ("mount_ra", "mount_dec", "mount_altitude", "mount_azimuth", "mount_time_to_flip"):
        if key in ents:
            mount_status.append({"entity": ents[key]})
    for key in ("mount_tracking", "mount_slewing", "mount_at_park"):
        if key in ents:
            mount_status.append({"entity": ents[key]})
    if mount_status:
        cards.append(_entities_card("Mount", mount_status))

    mount_actions = []
    for key, name in [
        ("mount_park", "Park"),
        ("mount_unpark", "Unpark"),
    ]:
        if key in ents:
            mount_actions.append({"entity": ents[key], "name": name})
    if mount_actions:
        cards.append(_entities_card("Mount actions", mount_actions))

    # ---- Guiding --------------------------------------------------------- #
    guide_keys = ("guider_ra_distance", "guider_dec_distance")
    guide_entities = [ents[k] for k in guide_keys if k in ents]
    if guide_entities:
        cards.append(_history_card("Guiding error (arcsec)", guide_entities, hours=2))
        if "guider_ra_distance" in ents:
            cards.append(
                _gauge_card(
                    ents["guider_ra_distance"],
                    "RA error",
                    min=-3,
                    max=3,
                    severity={"green": 0, "yellow": 1, "red": 2},
                )
            )

    # ---- Focuser --------------------------------------------------------- #
    focus_status = []
    for key in ("focuser_position", "focuser_temperature"):
        if key in ents:
            focus_status.append({"entity": ents[key]})
    if focus_status:
        cards.append(_entities_card("Focuser", focus_status))

    # ---- Sequence -------------------------------------------------------- #
    seq_status: list[dict[str, Any]] = []
    if "sequence_running" in ents:
        seq_status.append({"entity": ents["sequence_running"]})
    if "sequence_target" in ents:
        seq_status.append({"entity": ents["sequence_target"]})
    seq_actions = []
    for key, name in [
        ("sequence_start", "Start sequence"),
        ("sequence_stop", "Stop sequence"),
    ]:
        if key in ents:
            seq_actions.append({"entity": ents[key], "name": name})
    if seq_status or seq_actions:
        cards.append(_entities_card("Sequence", seq_status + seq_actions))

    # ---- Weather --------------------------------------------------------- #
    weather_keys = (
        "weather_temperature",
        "weather_humidity",
        "weather_pressure",
        "weather_dewpoint",
        "weather_wind_speed",
        "weather_sky_quality",
        "weather_sky_temperature",
    )
    weather_entities = [ents[k] for k in weather_keys if k in ents]
    if weather_entities:
        cards.append(_glance_card("Weather", weather_entities))

    # ---- Safety --------------------------------------------------------- #
    if "safety_is_safe" in ents:
        cards.append(_entities_card("Safety", [{"entity": ents["safety_is_safe"]}]))

    if not cards:
        cards.append(
            _markdown("_No NINA entities detected yet. Make sure NINA is running and the integration is connected._")
        )

    # Mushroom hooks: replace the equipment list with a chips card if requested.
    if use_mushroom and connect_rows:
        chips = [
            {"type": "entity", "entity": row["entity"], "icon_color": "blue", "content_info": "name"}
            for row in connect_rows
        ]
        for i, c in enumerate(cards):
            if c.get("type") == "entities" and c.get("title") == "Equipment":
                cards[i] = {"type": "custom:mushroom-chips-card", "chips": chips}
                break

    title = label
    return {
        "title": title,
        "path": f"nina-{entry_id[:8]}",
        "icon": "mdi:telescope",
        "cards": cards,
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
