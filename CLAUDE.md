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

## Git Workflow

- Branch from `main`
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- PR per feature/fix
