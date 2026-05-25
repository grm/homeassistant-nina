# Changelog

All notable changes to **NINA Polaris** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
