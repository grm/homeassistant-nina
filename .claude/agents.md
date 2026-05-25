# Agents Configuration

## Available Agent Types

### Explore
Use for finding code patterns, understanding data flow, locating where things are defined.
- "Where does the coordinator get camera data?"
- "Find all WebSocket event handlers"
- "Which sensors use temperature data?"

### Plan
Use before implementing complex features that touch multiple files.
- Adding a new entity platform (camera, switch, button)
- Refactoring the coordinator for multiple data sources
- Adding options flow or reauth flow

### general-purpose
Use for multi-step research tasks.
- Checking NINA API spec for available endpoints
- Comparing HA integration patterns across other projects
- Investigating HA deprecation warnings

## Task Patterns

### Adding a New Entity Platform
1. Plan: design the entity, decide on descriptions
2. Create the platform file (e.g., `switch.py`, `button.py`)
3. Add to PLATFORMS list in `__init__.py`
4. Add strings to `strings.json`
5. Test

### Adding WebSocket-Driven Features
1. Identify the event in `websocket_spec.yaml`
2. Update coordinator to handle the event
3. Create/update entities that consume the data
4. Test with mock WebSocket messages

### Debugging Connection Issues
1. Check NINA is running with API plugin enabled
2. Verify port (default 1888) is accessible
3. Test with: `curl http://{host}:1888/v2/api/version`
4. Check WebSocket: `wscat -c ws://{host}:1888/v2/socket`
