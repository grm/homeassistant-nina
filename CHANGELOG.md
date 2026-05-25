# Changelog

All notable changes to **NINA Polaris** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Sensors and binary sensors now report `unknown` when their parent NINA device is disconnected** instead of echoing stale defaults like `0`, `-1`, or `False` cached from the last connected session. NINA's `/equipment/*/info` endpoints keep returning placeholder numerics even with `Connected: false`, which made the dashboard look "live" when the rig was actually offline (camera temp showing `-10 °C` while the sensor was unplugged, focuser at position `0`, etc.). Affected sensors: camera temp / cooler power, mount RA/Dec/Alt/Az/time-to-flip/tracking/slewing/parked, guider RA-Dec distance, focuser position/temperature, camera exposing/cooler-on. Weather, Safety and `latest_image_*` sensors are unaffected (they're either independent or expose historical data).

### Changed

- **Latest image pixel statistics now report `ADU` as their unit** — `latest_image_mean`, `latest_image_median` and `latest_image_stdev` were unitless before, which made values like `30 678` meaningless. The unit is the raw ADC reading (Analog-to-Digital Units, 0–65535 for typical 16-bit astro CMOS sensors). The `latest_image_stars` sensor lost its previous `stars` unit (cosmetic — HA shows the count without it).

## [0.5.0-beta.1] - 2026-05-25

### Added

- **Latest image metrics sensors.** New sensors expose key statistics from the most recently saved frame so you can monitor session quality without leaving Home Assistant: `latest_image_hfr` (px), `latest_image_stars`, `latest_image_filter`, `latest_image_exposure_time` (s), `latest_image_mean`, `latest_image_median`, `latest_image_stdev`, `latest_image_temperature` (°C, sensor temp during exposure) and `latest_image_guiding_rms` (″, parsed from NINA's `RmsText`). Metadata is fetched once per new image (cached on the index, no spam) via `/image-history?index=N`. Translations: EN + FR.
- **Dashboard "Last image" section** in the Imaging column rendering all nine new sensors as a 2-column tile grid (HFR, Stars, Filter, Exposure, Guiding RMS, Sensor temp, Mean, Median, Std dev) with topic-appropriate MDI icons.
- **Prominent "Current target" tile** at the top of the Sequence section — the most important piece of session info now occupies its own full-width row instead of a half-tile cell.

### Changed

- **Dashboard layout reordered.** The Focuser card is now grouped under the Camera section in the Imaging column (focus belongs to imaging, not pointing). The Equipment connection list moves to the top of the Environment column, above Weather, so a glance at the left column tells you what's connected and what the sky is doing.

### Added

- README: support / donations section (Buy Me A Coffee + PayPal) for users who want to thank the maintainer.

## [0.4.0] - 2026-05-25

### Changed

- **Dashboard now uses a 3-column responsive `sections` view** (HA 2024.3+). On desktop, the dashboard reflows into three side-by-side columns instead of one tall single column; on mobile/tabl...[truncated]

## [0.3.0] - 2026-05-25

### Changed

- **Dashboard visual overhaul (Option 1 — tile grid).** Every section (Equipment / Camera / Mount / Guiding / Focuser / Sequence / Weather / Safety) now renders as a 2- or 3-column grid of native HA `tile` cards with adapted MDI icons and color coding instead of flat `entities` lists / glance grids. Color palette: cyan/light-blue/blue/amber for Camera, indigo/blue-grey/amber/green/orange for Mount, blue/amber for Guiding, purple/cyan for Focuser, green/red for Sequence actions, orange/light-blue/blue-grey/cyan/teal/indigo/deep-purple for Weather, green for Safety. Section headings (`heading` cards) introduce each block. Park/Unpark and Sequence Start/Stop use red/green color split. The previous `gauge` RA-error card is replaced by a tile (cleaner, less screen real estate); the history graph is preserved. The redundant `Trevinca …` prefix is dropped from labels (the dashboard title already names the instance).
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
