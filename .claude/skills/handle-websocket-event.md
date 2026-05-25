---
name: handle-websocket-event
description: Add handling for a new NINA WebSocket event
---

# Handle WebSocket Event

NINA WebSocket events arrive on `ws://{host}:1888/v2/socket` with this format:
```json
{"Response": <data>, "Event": "EVENT-NAME", "Type": "Socket"}
```

Key events (from websocket_spec.yaml):
- IMAGE-SAVE: New image saved (with stats, path, filter, exposure details)
- SEQUENCE-STARTING / SEQUENCE-FINISHED
- AUTOFOCUS-STARTING / AUTOFOCUS-FINISHED / AUTOFOCUS-POINT-ADDED
- CAMERA-CONNECTED / CAMERA-DISCONNECTED
- MOUNT-*, GUIDER-*, FOCUSER-*, DOME-*, ROTATOR-*
- TS-NEWTARGETSTART / TS-TARGETSTART (target switching)
- ERROR-AF / ERROR-PLATESOLVE

To handle a new event:

1. In `coordinator.py`, update `_on_websocket_event` to parse the specific event type
2. Optionally trigger a full data refresh with `await self.async_request_refresh()`
3. Or update specific data inline with `self.async_set_updated_data(...)`

Example:
```python
def _on_websocket_event(self, event: dict[str, Any]) -> None:
    event_type = event.get("Event", "")
    if event_type == "IMAGE-SAVE":
        # Update image-specific data
        ...
    self.async_set_updated_data({...})
```
