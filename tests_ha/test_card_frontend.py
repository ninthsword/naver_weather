"""Exercise card setup, companion-entity permissions, and forecast delivery in HA."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.auth.const import GROUP_ID_READ_ONLY
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import naver_weather_custom as integration
from custom_components.naver_weather_custom.api_nweather import NWeatherAPI
from custom_components.naver_weather_custom.const import (
    CONF_AREA,
    CONF_LOCATION_ENTITY,
    CONF_TODAY,
    DOMAIN,
    LOCATION,
    NOW_TEMP,
    SW_VERSION,
    WEATHER_INFO,
)

CARD_COMMAND = f"{DOMAIN}/card_entities"
FRONTEND_PATH = f"/{DOMAIN}/frontend"
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "custom_components" / DOMAIN / "frontend"


@pytest.mark.parametrize("frontend_loaded,has_http", [(True, True), (False, True), (True, False)])
async def test_frontend_registration(hass, monkeypatch, frontend_loaded, has_http):
    register = Mock()
    add_url = Mock()
    static_paths = AsyncMock()
    monkeypatch.setattr(websocket_api, "async_register_command", register)
    monkeypatch.setattr("homeassistant.components.frontend", SimpleNamespace(add_extra_js_url=add_url), raising=False)
    monkeypatch.setattr(hass, "http", SimpleNamespace(async_register_static_paths=static_paths) if has_http else None)
    if frontend_loaded:
        hass.config.components.add("frontend")

    assert await integration.async_setup(hass, {})
    register.assert_called_once_with(hass, integration._card_entities)
    if frontend_loaded and has_http:
        static_paths.assert_awaited_once()
        assert static_paths.await_args is not None
        paths, = static_paths.await_args.args
        path, = paths
        assert path.url_path == FRONTEND_PATH
        assert Path(path.path) == FRONTEND_DIR
        assert path.cache_headers is False
        add_url.assert_called_once_with(hass, f"{FRONTEND_PATH}/naver-weather-card.js?v={SW_VERSION}")
    else:
        static_paths.assert_not_awaited()
        add_url.assert_not_called()


async def test_frontend_registration_failure_keeps_setup_available(hass, monkeypatch, caplog):
    register = Mock()
    monkeypatch.setattr(websocket_api, "async_register_command", register)
    monkeypatch.setattr("homeassistant.components.frontend", SimpleNamespace(add_extra_js_url=Mock()), raising=False)
    static_paths = AsyncMock(side_effect=RuntimeError("검증동"))
    monkeypatch.setattr(hass, "http", SimpleNamespace(async_register_static_paths=static_paths))
    hass.config.components.add("frontend")

    assert await integration.async_setup(hass, {})
    register.assert_called_once()
    static_paths.assert_awaited_once()
    records = [record for record in caplog.records if record.name == integration.__name__]
    assert len(records) == 1 and records[0].levelno == logging.WARNING
    assert "검증동" not in records[0].getMessage()


async def _setup_entry(hass, area, *, location_entity=None, update=None):
    async def synthetic(api, area: str | None = None):
        api.result = {NOW_TEMP[0]: "21.5", "Condition": "sunny", LOCATION[0]: "검증시 검증구"}

    data = {CONF_AREA: area, CONF_TODAY: True}
    if location_entity:
        data[CONF_LOCATION_ENTITY] = location_entity
    entry = MockConfigEntry(domain=DOMAIN, data=data, unique_id=location_entity or area)
    entry.add_to_hass(hass)
    with patch.object(NWeatherAPI, "update", update or synthetic):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.LOADED
    return entry


def _weather_id(hass, entry):
    weather, = [
        entity.entity_id for entity in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if entity.entity_id.startswith("weather.")
    ]
    return weather


async def _lookup(client, entity_id, msg_id):
    await client.send_json({"id": msg_id, "type": CARD_COMMAND, "entity_id": entity_id})
    reply = await client.receive_json()
    assert reply["id"] == msg_id and reply["type"] == "result"
    return reply


async def test_card_entities_use_registry_identity_for_fixed_and_current_location(hass, hass_ws_client):
    fixed = await _setup_entry(hass, "검증동")
    hass.states.async_set("sensor.synthetic_location", "검증시 검증2동", {
        "Locality": "검증시", "Sub Locality": "검증2동",
    })
    current = await _setup_entry(hass, "날씨", location_entity="sensor.synthetic_location")
    registry = er.async_get(hass)
    client = await hass_ws_client(hass)
    with patch.object(NWeatherAPI, "area", new_callable=PropertyMock, side_effect=AssertionError("API touched")):
        for msg_id, (entry, prefix) in enumerate(
            ((fixed, "검증동 날씨"), (current, f"location_{current.entry_id}")), start=1,
        ):
            reply = await _lookup(client, _weather_id(hass, entry), msg_id)
            expected = {
                key: registry.async_get_entity_id("sensor", DOMAIN, f"{prefix}:{key}")
                for key in (*WEATHER_INFO, "ForecastHourly", "ForecastDaily")
            }
            assert len(expected) == 33 and all(expected.values())
            assert reply["success"] and reply["result"] == {"entities": expected}


async def test_card_entities_returns_same_error_for_unknown_foreign_and_unloaded(hass, hass_ws_client):
    loaded = await _setup_entry(hass, "검증동")
    unloaded = await _setup_entry(hass, "검증2동")
    registry = er.async_get(hass)
    foreign = registry.async_get_or_create("weather", "synthetic_foreign", "foreign", config_entry=loaded)
    unloaded_id = _weather_id(hass, unloaded)
    assert await hass.config_entries.async_unload(unloaded.entry_id)

    client = await hass_ws_client(hass)
    errors = []
    for msg_id, entity_id in enumerate(("weather.missing", foreign.entity_id, unloaded_id), start=1):
        reply = await _lookup(client, entity_id, msg_id)
        assert not reply["success"] and reply["error"]["code"] == "not_found"
        errors.append(reply["error"])
    assert errors[0] == errors[1] == errors[2]


async def test_card_entities_checks_read_permission_for_weather_and_companions(hass, hass_ws_client):
    entry = await _setup_entry(hass, "검증동")
    weather_id = _weather_id(hass, entry)
    denied = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "검증동 날씨:NowTemp")
    assert denied
    user = await hass.auth.async_create_user("검증 사용자", group_ids=[GROUP_ID_READ_ONLY])
    assert not user.is_admin
    refresh_token = await hass.auth.async_create_refresh_token(user, client_id="https://example.invalid/")
    client = await hass_ws_client(hass, access_token=hass.auth.async_create_access_token(refresh_token))
    blocked = {weather_id, denied}

    def can_read(_permissions, entity_id, policy):
        assert policy == POLICY_READ
        return entity_id not in blocked

    with patch.object(type(user.permissions), "check_entity", autospec=True, side_effect=can_read):
        reply = await _lookup(client, weather_id, 1)
        assert not reply["success"] and reply["error"]["code"] == "not_found"
        blocked.remove(weather_id)
        reply = await _lookup(client, weather_id, 2)
    assert reply["success"] and set(reply["result"]["entities"]) == (
        set(WEATHER_INFO) | {"ForecastHourly", "ForecastDaily"}
    ) - {"NowTemp"}


async def test_forecast_only_refresh_is_sent_to_both_subscriptions(hass, hass_ws_client):
    midnight = datetime(2030, 1, 1, tzinfo=UTC)
    temperature = 21
    location = "검증시 검증구"

    async def update(api):
        api.result = {NOW_TEMP[0]: "21.5", "Condition": "sunny", LOCATION[0]: location}
        api.weathertype = "wt1"
        api.forecast_hour = [{"datetime": midnight, "condition": "sunny", "native_temperature": temperature}]
        api.forecast = [{
            "datetime": midnight, "condition_am": "sunny", "condition_pm": "cloudy",
            "weathertype_am": "wt1", "weathertype_pm": "wt5", "rain_rate_am": 0, "rain_rate_pm": 10,
            "templow": 13, "temperature": temperature,
        }]

    entry = await _setup_entry(hass, "검증동", update=update)
    weather_id = _weather_id(hass, entry)
    location_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "검증동 날씨:LocationInfo")
    assert location_id
    before = hass.states.get(weather_id)
    assert before
    client = await hass_ws_client(hass)
    for msg_id, kind in ((1, "hourly"), (2, "daily")):
        await client.send_json({
            "id": msg_id, "type": "weather/subscribe_forecast",
            "entity_id": weather_id, "forecast_type": kind,
        })
        reply = await client.receive_json()
        assert reply["type"] == "result" and reply["id"] == msg_id and reply["success"]
        event = await client.receive_json()
        assert event["type"] == "event" and event["id"] == msg_id
        assert event["event"]["forecast"][0]["temperature"] == 21

    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    with patch.object(NWeatherAPI, "update", update):
        temperature = 24
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        messages = {}
        for _ in range(2):
            event = await client.receive_json(timeout=2)
            assert event["type"] == "event"
            messages[event["id"]] = event["event"]["forecast"][0]["temperature"]
        assert messages == {1: 24, 2: 24}
        after = hass.states.get(weather_id)
        assert after and after.state == before.state and after.attributes == before.attributes
        assert (location_state := hass.states.get(location_id)) and location_state.state == "검증시 검증구"

        location = "검증시 검증2동"
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert (location_state := hass.states.get(location_id)) and location_state.state == location
