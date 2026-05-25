# NINA Astrophotography - Home Assistant Integration

Custom Home Assistant integration for [NINA (Nighttime Imaging 'N' Astronomy)](https://nighttime-imaging.eu/) via the [ninaAPI plugin](https://github.com/christian-photo/ninaAPI).

Monitor your astrophotography sessions in real-time from Home Assistant.

## Features

- Real-time equipment status (camera, mount, guider, focuser, filter wheel, dome, rotator)
- Sequence monitoring (running state, current target)
- Guiding metrics (RA/Dec distance)
- Weather data (temperature, humidity, pressure, dew point, wind, sky quality, sky temperature)
- Safety monitor status
- WebSocket push for instant event updates + REST polling fallback
- Multi-instance support (multiple NINA setups)
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
4. Search for "NINA Astrophotography" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/nina_astro/` to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "NINA Astrophotography"
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
       custom_components.nina_astro: debug
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
ruff check custom_components/nina_astro/
mypy custom_components/nina_astro/
```

## License

MIT
