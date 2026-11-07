"""Exercise actual HA setup, refresh, forecast services, and unload offline."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from aiohttp import ClientResponseError, RequestInfo
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er
from multidict import CIMultiDict, CIMultiDictProxy
from pytest_homeassistant_custom_component.common import MockConfigEntry
from yarl import URL

from custom_components.naver_weather_custom import coordinator as coordinator_module
from custom_components.naver_weather_custom.api_nweather import NWeatherAPI
from custom_components.naver_weather_custom.const import CONF_AREA, DOMAIN, NOW_TEMP


@pytest.mark.asyncio
async def test_setup_refresh_forecast_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "날씨"}, unique_id="synthetic")
    entry.add_to_hass(hass)
    calls = 0

    async def update(api):
        nonlocal calls
        calls += 1
        api.result = {NOW_TEMP[0]: 20 + calls}
        api.forecast_hour = [{
            "datetime": datetime(2030, 1, 1, tzinfo=UTC),
            "condition": "sunny", "native_temperature": 23,
            "native_wind_speed": 2, "native_precipitation": 0,
        }]

    with patch.object(NWeatherAPI, "update", update):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED and calls == 1
        coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
        entity_id = er.async_get(hass).async_get_entity_id(
            "weather", DOMAIN, "날씨:Naver Weather Custom"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None and state.attributes["temperature"] == 21
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state is not None and state.attributes["temperature"] == 22
        forecasts = await hass.services.async_call(
            "weather", "get_forecasts", {"entity_id": entity_id, "type": "hourly"},
            blocking=True, return_response=True,
        )
        assert forecasts is not None
        assert forecasts[entity_id]["forecast"][0]["temperature"] == 23
        assert forecasts[entity_id]["forecast"][0]["wind_speed"] == 7.2
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        assert entry.entry_id not in hass.data[DOMAIN]["api"]
        assert entry.entry_id not in hass.data[DOMAIN]["coordinators"]
        assert not coordinator._listeners


def _forbidden() -> ClientResponseError:
    url = URL("https://search.example.invalid/")
    info = RequestInfo(url, "GET", CIMultiDictProxy(CIMultiDict()), url)
    return ClientResponseError(info, (), status=403, message="Forbidden")


@pytest.mark.asyncio
async def test_forbidden_refreshes_keep_last_value_for_one_hour(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "날씨"}, unique_id="synthetic")
    entry.add_to_hass(hass)
    fail = False
    temperature = 7.5

    async def update(api):
        if fail:
            raise _forbidden()
        api.result = {NOW_TEMP[0]: temperature}

    clock = [1000.0]
    with patch.object(NWeatherAPI, "update", update), patch.object(
        coordinator_module, "monotonic", lambda: clock[0]
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
        entity_id = er.async_get(hass).async_get_entity_id(
            "weather", DOMAIN, "날씨:Naver Weather Custom"
        )
        assert entity_id is not None

        fail = True
        for elapsed in (600.0, 3599.0):
            clock[0] = 1000.0 + elapsed
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            assert not coordinator.last_update_success
            state = hass.states.get(entity_id)
            assert state is not None and state.attributes["temperature"] == 7.5

        clock[0] = 1000.0 + 3600.0
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state is not None and state.state == STATE_UNAVAILABLE

        fail = False
        temperature = 8.0
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state is not None and state.state != STATE_UNAVAILABLE
        assert state.attributes["temperature"] == 8.0

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
