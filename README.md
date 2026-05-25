<p align="center">
  <img src=".github/logo.png" alt="NINA Polaris" width="320">
</p>

# NINA Polaris — Home Assistant Integration

Custom Home Assistant integration for [NINA (Nighttime Imaging 'N' Astronomy)](https://nighttime-imaging.eu/) via the [ninaAPI plugin](https://github.com/christian-photo/ninaAPI).

Monitor your astrophotography sessions in real-time from Home Assistant.

## Features

- Real-time equipment status (camera, mount, guider, focuser, filter wheel, dome, rotator)
- Sequence monitoring (running state, current target)
- Guiding metrics (RA/Dec distance)
- Weather data (temperature, humidity, pressure, dew point, wind, sky quality, sky temperature)
- Safety monitor status
- **Live image preview** — the latest frame captured by NINA is exposed as a Camera entity, proxied through Home Assistant (no need for the browser to reach NINA directly, works fine through Nabu Casa)
- **Action buttons** — park / unpark mount, start / stop sequence, run autofocus, plate solve
- **Toggleable controls** — camera cooler (on / off), mount tracking (sidereal / stopped)
- **One-click dashboard** — the `nina_polaris.generate_dashboard` service builds a complete Lovelace dashboard from your registry (no custom cards needed)
- WebSocket push for instant event updates + REST polling fallback
- Multi-instance support (multiple NINA setups, each gets its own dashboard view)
- French and English translations

## Requirements

- Home Assistant 2024.1.0+
- HACS 2.0.0+
- NINA with the [ninaAPI plugin](https://github.com/christian-photo/ninaAPI) installed and enabled
- Network access from Home Assistant to the NINA machine on port 1888 (default)

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu > **Custom repositories**
3. Add `https://github.com/grm/homeassistant-nina` with category **Integration**
4. Search for "NINA Polaris" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/nina_polaris/` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "NINA Polaris"
3. Enter the host (IP or hostname) and port (default: 1888) of your NINA machine
4. Done

## Entities

### Sensors

| Entity | Description | Unit |
|--------|-------------|------|
| Camera temperature | CCD/CMOS sensor temperature | °C |
| Camera cooler power | Cooler power usage | % |
| Guider RA distance | Last guide step RA correction | px |
| Guider Dec distance | Last guide step Dec correction | px |
| Focuser position | Current focuser step position | - |
| Focuser temperature | Focuser probe temperature | °C |
| Mount RA | Right ascension | hours |
| Mount Dec | Declination | degrees |
| Mount altitude | Altitude above horizon | ° |
| Mount azimuth | Azimuth | ° |
| Time to meridian flip | Time remaining before flip | min |
| Sequence current target | Name of the active target | - |
| Weather temperature | Ambient temperature | °C |
| Weather humidity | Relative humidity | % |
| Weather pressure | Atmospheric pressure | hPa |
| Weather dew point | Dew point temperature | °C |
| Weather wind speed | Wind speed | m/s |
| Sky quality (SQM) | Sky background magnitude | mag/arcsec² |
| Sky temperature | Infrared sky temperature | °C |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| Camera connected | Camera equipment connection |
| Mount connected | Mount equipment connection |
| Guider connected | Guider equipment connection |
| Focuser connected | Focuser equipment connection |
| Filter wheel connected | Filter wheel connection |
| Dome connected | Dome connection |
| Rotator connected | Rotator connection |
| Weather station connected | Weather station connection |
| Safety monitor connected | Safety monitor connection |
| Observatory safe | Safety monitor reports safe |
| Sequence running | A sequence is currently running |
| Mount tracking | Mount sidereal tracking active |
| Mount slewing | Mount is slewing |
| Mount parked | Mount is in park position |
| Camera exposing | Camera is currently exposing |
| Camera cooler on | Camera cooler is active |

### Camera

| Entity | Description |
|--------|-------------|
| Latest image | Last frame captured by NINA, refreshed automatically on every `IMAGE-SAVE` event. Bytes are proxied through Home Assistant — the browser never needs to talk to the NINA host directly, so the preview works through Nabu Casa and any reverse proxy. |

### Buttons

| Entity | Description |
|--------|-------------|
| Park mount | Calls `/equipment/mount/park`. Available when the mount is connected. |
| Unpark mount | Calls `/equipment/mount/unpark`. Available when the mount is connected. |
| Start sequence | Calls `/sequence/start`. Available only when no sequence is running. |
| Stop sequence | Calls `/sequence/stop`. Available only when a sequence is running. |
| Run autofocus | Calls `/equipment/focuser/auto-focus`. Available when the focuser is connected. |
| Plate solve | Calls `/equipment/camera/capture?solve=true&omitImage=true`. Available when the camera is connected. |

### Switches

| Entity | Description |
|--------|-------------|
| Camera cooler | ON cools the camera (default target -10 °C, override via the entry option `cooler_target_temperature`). OFF triggers `/equipment/camera/warm`. |
| Mount tracking | ON sets sidereal tracking (mode 0). OFF stops tracking (mode 4). |

## Services

In addition to the action buttons (which run with sensible defaults), the integration exposes parameterized services callable from automations, scripts, and the developer tools panel.

| Service | Description | Notable parameters |
| --- | --- | --- |
| `nina_polaris.cool_camera` | Ramp the camera cooler down | `temperature` (°C), `duration` (min) |
| `nina_polaris.warm_camera` | Warm up gracefully | `duration` (min) |
| `nina_polaris.set_tracking` | Switch tracking rate | `mode` (`sidereal`, `lunar`, `solar`, `king`, `stopped`) |
| `nina_polaris.start_sequence` | Start the active sequence | `skip_validation` (bool) |
| `nina_polaris.stop_sequence` | Stop the running sequence | – |
| `nina_polaris.park_mount` / `nina_polaris.unpark_mount` | Park / unpark the mount | – |
| `nina_polaris.start_autofocus` / `nina_polaris.cancel_autofocus` | Run / cancel autofocus | – |
| `nina_polaris.plate_solve` | Capture and platesolve | – |

All services accept an optional `config_entry` parameter (NINA instance selector). When you only have one NINA Polaris instance configured, you can omit it.

Example — automation that cools the camera to -20 °C at sunset:

```yaml
automation:
  - alias: Pre-cool camera before session
    trigger:
      - platform: sun
        event: sunset
        offset: "-00:30:00"
    action:
      - service: nina_polaris.cool_camera
        data:
          temperature: -20
          duration: 10
```

## Dashboard

NINA Polaris generates a complete Lovelace dashboard for you with a **single service call**. No JS, no custom cards required — every card is built into Home Assistant Core.

### One-click setup

1. Open **Developer Tools → Actions** (or **Services**)
2. Pick `nina_polaris.generate_dashboard`
3. Click **Perform action**

A dashboard called **NINA Polaris** appears in your sidebar with one view per configured instance. Cards: equipment chips, latest camera image, mount RA/DEC, guiding history graph, focuser, sequence progress, weather, safety. You can edit it like any normal dashboard afterwards.

Run the service again any time to rebuild after adding a NINA instance or new entities. It overwrites the dashboard but you can change the URL path to keep multiple variants.

### Service options

| Field | Default | Description |
|---|---|---|
| `url_path` | `nina-polaris` | URL slug for the dashboard |
| `title` | `NINA Polaris` | Sidebar title |
| `use_mushroom` | `false` | Replace equipment glance card with `mushroom-chips-card` (requires Mushroom from HACS) |

Example (YAML):

```yaml
action: nina_polaris.generate_dashboard
data:
  use_mushroom: true
```

### Optional: prettier cards

The default output uses 100% native HA cards. If you want extra polish, install from HACS → Frontend:

- **Mushroom** — pretty chips for equipment (set `use_mushroom: true`)

### YAML mode

The service requires Lovelace **storage** mode (the default). If you run `lovelace: mode: yaml`, the service refuses with a clear error — manually copy a dashboard YAML instead.

## Troubleshooting

1. **Cannot connect**: Verify NINA is running with the ninaAPI plugin enabled. Test with:
   ```
   curl http://<nina-host>:1888/v2/api/version
   ```
2. **Entities unavailable**: Check that the corresponding equipment is connected in NINA
3. **Enable debug logs** in `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.nina_polaris: debug
   ```

## Development

```bash
# Setup
pyenv local 3.12.12
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Lint & type check
ruff check custom_components/nina_polaris/
mypy custom_components/nina_polaris/
```

## License

MIT
