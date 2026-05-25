# Changelog

All notable changes to **NINA Polaris** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
