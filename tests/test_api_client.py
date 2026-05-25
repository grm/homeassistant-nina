"""Tests for NINA API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.nina_astro.api_client import NinaApiClient, NinaApiError


@pytest.fixture
def api_client():
    return NinaApiClient("localhost", 1888)


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response."""

    def _make_response(json_data, status=200):
        response = AsyncMock()
        response.raise_for_status = MagicMock()
        response.json = AsyncMock(return_value=json_data)
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=False)
        return response

    return _make_response


@pytest.mark.asyncio
async def test_get_version(api_client, mock_response):
    """Test fetching NINA version."""
    resp = mock_response(
        {
            "Response": {"Version": "2.2.15", "NinaVersion": "3.1"},
            "Error": "",
            "StatusCode": 200,
            "Success": True,
            "Type": "API",
        }
    )

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=resp)
    mock_session.closed = False
    api_client._session = mock_session

    result = await api_client.get_version()
    assert result == {"Version": "2.2.15", "NinaVersion": "3.1"}
    mock_session.get.assert_called_once_with("http://localhost:1888/v2/api/version")


@pytest.mark.asyncio
async def test_get_equipment_info(api_client, mock_response):
    """Test fetching equipment info."""
    equipment_data = {"Camera": {"Connected": True}, "Mount": {"Connected": False}}
    resp = mock_response(
        {
            "Response": equipment_data,
            "Error": "",
            "StatusCode": 200,
            "Success": True,
            "Type": "API",
        }
    )

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=resp)
    mock_session.closed = False
    api_client._session = mock_session

    result = await api_client.get_equipment_info()
    assert result == equipment_data


@pytest.mark.asyncio
async def test_api_error_response(api_client, mock_response):
    """Test that API error responses raise NinaApiError."""
    resp = mock_response(
        {
            "Response": None,
            "Error": "Camera not connected",
            "StatusCode": 500,
            "Success": False,
            "Type": "API",
        }
    )

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=resp)
    mock_session.closed = False
    api_client._session = mock_session

    with pytest.raises(NinaApiError, match="Camera not connected"):
        await api_client.get_camera_info()


@pytest.mark.asyncio
async def test_http_error(api_client):
    """Test that HTTP errors are propagated."""
    response = AsyncMock()
    response.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(request_info=MagicMock(), history=(), status=404)
    )
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=False)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=response)
    mock_session.closed = False
    api_client._session = mock_session

    with pytest.raises(aiohttp.ClientResponseError):
        await api_client.get_version()


@pytest.mark.asyncio
async def test_close_session(api_client):
    """Test closing the API client session."""
    mock_session = AsyncMock()
    mock_session.closed = False
    mock_session.close = AsyncMock()
    api_client._session = mock_session

    await api_client.close()
    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_no_session(api_client):
    """Test closing when no session exists."""
    await api_client.close()


def test_base_url(api_client):
    """Test base URL construction."""
    assert api_client.base_url == "http://localhost:1888/v2/api"


def test_base_url_custom_port():
    """Test base URL with custom port."""
    client = NinaApiClient("192.168.1.50", 2000)
    assert client.base_url == "http://192.168.1.50:2000/v2/api"


@pytest.mark.asyncio
async def test_session_created_on_first_use(api_client):
    """Test that session is created lazily."""
    assert api_client._session is None
    with patch("custom_components.nina_astro.api_client.aiohttp.ClientSession") as mock_cls:
        fake = MagicMock()
        fake.closed = False
        mock_cls.return_value = fake

        session = api_client.session
        assert session is fake
        mock_cls.assert_called_once()

        # Second access reuses the same instance
        assert api_client.session is fake
        mock_cls.assert_called_once()
