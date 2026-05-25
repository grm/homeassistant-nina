---
name: add-api-endpoint
description: Add a new NINA REST API endpoint call
---

# Add API Endpoint

When adding a new API endpoint:

1. Add the method to `custom_components/nina_polaris/api_client.py`
2. Reference `api_spec.yaml` for the endpoint path, parameters, and response format
3. All NINA endpoints return: `{"Response": <data>, "Error": "", "StatusCode": 200, "Success": true, "Type": "API"}`
4. The `_get` method already unwraps the `Response` field

Template:
```python
async def get_something(self) -> dict[str, Any]:
    return await self._get("/equipment/something/info")
```

For POST endpoints, add a `_post` method to the client if not already present:
```python
async def _post(self, path: str, data: dict | None = None) -> Any:
    async with self.session.post(f"{self.base_url}{path}", json=data) as resp:
        resp.raise_for_status()
        result = await resp.json()
        if not result.get("Success", False):
            raise NinaApiError(result.get("Error", "Unknown error"))
        return result.get("Response")
```
