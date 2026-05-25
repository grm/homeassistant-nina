---
name: add-sensor
description: Add a new sensor entity to the NINA integration
---

# Add Sensor

When adding a new sensor to the integration:

1. Add a `SensorEntityDescription` to `SENSOR_DESCRIPTIONS` in `custom_components/nina_astro/sensor.py`
2. Add the data extraction logic in the `_extract_value` method's mapping dict
3. Add the translation string in `custom_components/nina_astro/strings.json` under `entity.sensor`
4. If the sensor requires new API data, add the corresponding method to `api_client.py` and update the coordinator's `_async_update_data`

Template for a new sensor:
```python
SensorEntityDescription(
    key="my_new_sensor",
    translation_key="my_new_sensor",
    native_unit_of_measurement="unit",
    state_class=SensorStateClass.MEASUREMENT,
),
```

And in `_extract_value` mapping:
```python
"my_new_sensor": lambda: equipment.get("Category", {}).get("Field"),
```
