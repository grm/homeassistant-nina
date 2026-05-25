# NINA Polaris - Home Assistant Integration

## Project Overview

Custom Home Assistant integration connecting to NINA (Nighttime Imaging 'N' Astronomy) via its REST API and WebSocket interface. Deployed via HACS.

## Architecture

```
custom_components/nina_polaris/
├── __init__.py          # Integration setup, coordinator creation
├── manifest.json        # HA integration metadata
├── config_flow.py       # UI-based configuration (host/port)
├── const.py             # Constants (DOMAIN, defaults, keys)
├── strings.json         # UI strings / translations
├── coordinator.py       # DataUpdateCoordinator (REST polling)
├── websocket.py         # WebSocket client for real-time events
├── api_client.py        # NINA REST API client
├── sensor.py            # Sensor entities (camera temp, guider RMS, etc.)
├── binary_sensor.py     # Binary sensors (equipment connected, sequence running)
├── camera.py            # Camera entity (latest image)
└── models.py            # Data models / typed dicts
```

## Key Technical Details

- **NINA API**: REST on `http://{host}:1888/v2/api`, WebSocket on `ws://{host}:1888/v2/socket`
- **No authentication** required by NINA API
- **Default port**: 1888 (configurable)
- **IoT class**: `local_push` (WebSocket for real-time + REST polling fallback)
- **Domain**: `nina_polaris`

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Type checking
mypy custom_components/nina_polaris/

# Lint
ruff check custom_components/nina_polaris/
ruff format custom_components/nina_polaris/

# Validate integration (requires HA dev environment)
python -m script.hassfest validate --integration-path custom_components/nina_polaris
```

## API Reference

- REST spec: `api_spec.yaml` (OpenAPI 3.0, 156 endpoints)
- WebSocket spec: `websocket_spec.yaml` (AsyncAPI 2.0)
- WebSocket events include: IMAGE-SAVE, SEQUENCE-*, CAMERA-*, MOUNT-*, GUIDER-*, FOCUSER-*, etc.

## Response Format (all REST endpoints)

```json
{
  "Response": <varies>,
  "Error": "",
  "StatusCode": 200,
  "Success": true,
  "Type": "API"
}
```

## Conventions

- Use `async`/`await` everywhere (HA is async-first)
- Entities must extend `CoordinatorEntity` 
- All entity unique_ids: `{config_entry_id}_{entity_key}`
- Use `aiohttp` for HTTP/WS (already available in HA)
- Pin dependencies in `manifest.json` `requirements` field
- Use `voluptuous` for config schema validation
- When adding/modifying any user-facing string (entity name, config flow text, error message), update `strings.json` (source/fallback) AND every file in `translations/`. List the directory to discover all available languages. All files must stay in sync.

## Documentation

- `README.md` must be kept up to date. When adding/removing entities, changing configuration, or modifying features, update the corresponding sections in the README (entities tables, features list, troubleshooting, etc.)
- `CHANGELOG.md` (`## [Unreleased]` section) must be updated for every functional change. See the *Release Workflow* section below for the rules.
- **Always update documentation as part of the same change**, not as a follow-up. After modifying any user-facing behaviour (entity name, label, dashboard layout, config flow text, services, etc.), check both `README.md` and `CHANGELOG.md` and update them in the same commit. A change isn't done until the docs match.

## Git Workflow

- Branch from `main`
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- PR per feature/fix
- **Commit after every feature increment.** Don't batch unrelated changes. Each logical step (a new card layout, a new entity, a bugfix, a doc update tied to a behaviour change) gets its own focused commit and is pushed immediately. This keeps the CHANGELOG `[Unreleased]` aligned with what's on `main` and makes it trivial to bisect or revert a single change.

## Release Workflow

**Never run a release on your own.** Releases are user-triggered only.

After every functional change (feature, fix, breaking change, removal), add an entry under the `## [Unreleased]` section of `CHANGELOG.md` in the appropriate sub-section (`Breaking Changes`, `Added`, `Fixed`, `Removed`). Reference issues / PRs with `(#N)` when relevant. See `.claude/commands/changelog.md` for the format.

Do **not**:
- Bump `manifest.json` version
- Create git tags
- Run `gh release create`
- Move `[Unreleased]` entries under a versioned section

…unless the user explicitly says "release", "release stable", "release beta", or otherwise asks for a release. The `/release` command in `.claude/commands/release.md` is the only path that performs the version bump + tag + GitHub Release; it's invoked manually.
