"""Tests for NINA image endpoint decoding (raw bytes vs JSON+base64 envelope)."""

import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nina_polaris.api_client import NinaApiClient


def _make_client_with_response(body: bytes, content_type: str) -> NinaApiClient:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.read = AsyncMock(return_value=body)
    resp.headers = {"Content-Type": content_type}

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.closed = False
    session.get = MagicMock(return_value=cm)

    client = NinaApiClient("nina.local", 1888)
    client._session = session  # type: ignore[assignment]
    return client


@pytest.mark.asyncio
async def test_get_bytes_accepts_raw_image_content_type():
    client = _make_client_with_response(b"\x89PNG\r\n\x1a\nRAW", "image/png")
    out = await client._get_bytes("/image/0")
    assert out == b"\x89PNG\r\n\x1a\nRAW"


@pytest.mark.asyncio
async def test_get_bytes_decodes_json_envelope_with_base64_response():
    raw_image = b"\x89PNG\r\n\x1a\nDECODED"
    body = b'{"Response":"' + base64.b64encode(raw_image) + b'","Success":true}'
    client = _make_client_with_response(body, "application/json")
    out = await client._get_bytes("/image/0")
    assert out == raw_image


@pytest.mark.asyncio
async def test_get_bytes_returns_none_when_envelope_has_no_response():
    body = b'{"Response":403,"Success":true}'
    client = _make_client_with_response(body, "application/json")
    out = await client._get_bytes("/image/0")
    assert out is None
