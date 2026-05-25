---
name: add-binary-sensor
description: Add a new binary sensor entity to the NINA integration
---

# Add Binary Sensor

When adding a new binary sensor:

1. Add a `BinarySensorEntityDescription` to `BINARY_SENSOR_DESCRIPTIONS` in `custom_components/nina_astro/binary_sensor.py`
2. Add the data extraction logic in the `_extract_value` method's mapping dict
3. Add the translation string in `custom_components/nina_astro/strings.json` under `entity.binary_sensor`

Template:
```python
BinarySensorEntityDescription(
    key="my_new_binary_sensor",
    translation_key="my_new_binary_sensor",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,  # or RUNNING, etc.
),
```

And in `_extract_value` mapping:
```python
"my_new_binary_sensor": lambda: equipment.get("Category", {}).get("Connected", False),
```
