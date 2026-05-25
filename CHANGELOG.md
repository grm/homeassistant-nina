# Changelog

All notable changes to **NINA Polaris** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Dashboard visual overhaul (Option 1 — tile grid)** — *in progress, refactor by section*. The Camera, Mount, and Guiding sections now render as 2-column grids of native HA `tile` cards with adapted MDI icons and color coding (Camera: cyan/light-blue/blue/amber; Mount: indigo/blue-grey/amber/green/orange; Guiding: blue/amber). Park/Unpark row uses tile cards with red/green color split. The previous `gauge` RA-error card is replaced by a tile (cleaner, less screen real estate); the history graph is preserved. Section headings (`heading` cards) introduce each block. The redundant `Trevinca …` prefix is dropped from labels (the dashboard title already names the instance). Weather, Focuser, and Sequence sections will follow.
- **Mount Park/Unpark is now a single-row control** with the parked state, the Park button, and the Unpark button on the same horizontal line. The `mount_at_park` entity also moved out of the Mount status card into this new control to avoid duplication.
- **Equipment card on the dashboard is now a vertical list instead of a glance grid.** Each row shows a clean human label on the left (`Camera`, `Mount`, `Guider`, `Focuser`, `Filter wheel`, `Rotator`, `Dome`, `Weather`, `Safety monitor`) and the connection state (`Connected` / `Disconnected`) on the right — no more truncated `Trevinca C…` labels. The connection icon turns colored when connected (state_color enabled).
- **Config entry title now uses the active NINA profile name** (e.g. `Trevinca`, `TEC140`) instead of the generic `NINA (host:port)` label. The profile name is fetched from `/v2/api/profile/show?active=true` during the config flow. Falls back to `NINA (host:port)` if the profile endpoint is unreachable. This propagates to the integration page header, the device name, and the auto-generated dashboard sidebar entry. Existing entries can adopt the new label by renaming the hub in *Settings → Devices & Services → ⋮ → Rename* (the sidebar updates after the next reload).

## [0.2.0] - 2026-05-25

### Added

- **Per-instance dashboards** — each configured NINA instance now gets its own dedicated entry in the Home Assistant sidebar, named after the instance (e.g. *Trevinca*, *TEC140*, *FRA400*). Adding or removing a NINA instance updates the sidebar automatically; no service to call, no JS, no custom cards.
- The dashboard URL is human-readable and includes the instance slug (e.g. `/nina-trevinca-a1b2c3d4`).

### Changed

- The unified "NINA Polaris" dashboard with one tab per instance has been replaced by the per-instance sidebar entries. Users with a single NINA instance will see the sidebar entry renamed from "NINA Polaris" to their configured instance name.
- The duplicate `## 🔭 <instance>` markdown header at the top of each view has been removed since the instance name is now the page title itself.

## [0.1.0] - 2026-05-25

First public release on HACS.

### Added

- REST + WebSocket connection to NINA's Advanced API plugin (push events with REST polling fallback)
- Multi-instance support — multiple NINA setups, each gets its own dashboard view
- 19 sensor entities: equipment status (camera, mount, focuser, guider, dome, weather, safety), sequence state, image stats
- 17 binary sensor entities: connection / motion / cooling / safety flags
- 1 camera entity: latest captured image proxied through Home Assistant (works through Nabu Casa)
- 6 button entities: park / unpark mount, start / stop sequence, run autofocus, plate solve
- 2 switch entities: camera cooler, mount tracking
- 10 services for advanced control (cooler set point, sequence start with optional skip-validation, plate solve, etc.)
- **Auto-registered Lovelace dashboard** — appears in the sidebar as "NINA Polaris" on first setup, rebuilt from the entity registry on every page load. No service to call, no JS, no custom cards. Same pattern as the built-in Energy / Map dashboards.
- French and English translations
- Full test suite (152 tests) using `pytest-homeassistant-custom-component`
