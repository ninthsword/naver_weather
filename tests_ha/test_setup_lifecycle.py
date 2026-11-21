"""Exercise actual HA setup, refresh, forecast services, and unload offline."""

from asyncio import Event
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientResponseError, RequestInfo
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from multidict import CIMultiDict, CIMultiDictProxy
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from yarl import URL

from custom_components.naver_weather_custom import api_nweather as api_module
from custom_components.naver_weather_custom import coordinator as coordinator_module
from custom_components.naver_weather_custom.api_nweather import NWeatherAPI
from custom_components.naver_weather_custom.const import (
    BSE_URL,
    CONF_AREA,
    CONF_LOCATION_ENTITY,
    CONF_TODAY,
    DOMAIN,
    LOCATION,
    NDUST,
    NOW_TEMP,
    WEATHER_INFO,
)
from custom_components.naver_weather_custom.sensor import NWeatherForecastSensor
from custom_components.naver_weather_custom.weather import NWeatherMain


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


@pytest.mark.asyncio
async def test_restart_during_refusal_starts_from_recent_stored_values(hass, hass_storage):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "날씨"}, unique_id="synthetic")
    entry.add_to_hass(hass)
    key = f"{DOMAIN}.{entry.entry_id}"
    fail = True

    async def update(api):
        if fail:
            raise _forbidden()
        api.result = {NOW_TEMP[0]: 9.0}

    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": {
        "saved_at": 1000.0, "result": {NOW_TEMP[0]: 13.8}, "forecast": [],
        "forecast_hour": [{"datetime": {"__datetime__": "2030-01-01T00:00:00+09:00"},
                           "condition": "sunny", "native_temperature": 12,
                           "native_wind_speed": 1, "native_precipitation": 0}],
        "weathertype": "맑음",
    }}
    with patch.object(NWeatherAPI, "update", update), patch.object(
        coordinator_module, "time", lambda: 1000.0 + 600
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
        entity_id = er.async_get(hass).async_get_entity_id(
            "weather", DOMAIN, "날씨:Naver Weather Custom"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None and state.attributes["temperature"] == 13.8
        forecasts = await hass.services.async_call(
            "weather", "get_forecasts", {"entity_id": entity_id, "type": "hourly"},
            blocking=True, return_response=True,
        )
        assert forecasts is not None
        assert forecasts[entity_id]["forecast"][0]["temperature"] == 12

        fail = False
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=11))
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state is not None and state.attributes["temperature"] == 9.0
        assert coordinator.last_update_success
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_restart_during_refusal_with_old_stored_values_retries_setup(hass, hass_storage):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "날씨"}, unique_id="synthetic")
    entry.add_to_hass(hass)
    key = f"{DOMAIN}.{entry.entry_id}"

    async def update(api):
        raise _forbidden()

    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": {
        "saved_at": 1000.0, "result": {NOW_TEMP[0]: 13.8}, "forecast": [],
        "forecast_hour": [], "weathertype": "",
    }}
    with patch.object(NWeatherAPI, "update", update), patch.object(
        coordinator_module, "time", lambda: 1000.0 + 3600
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.asyncio
async def test_successful_refresh_is_saved_for_the_next_start(hass, hass_storage):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "날씨"}, unique_id="synthetic")
    entry.add_to_hass(hass)

    async def update(api):
        api.result = {NOW_TEMP[0]: 7.5}

    with patch.object(NWeatherAPI, "update", update), patch.object(
        coordinator_module, "time", lambda: 4321.0
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
        await hass.async_block_till_done()
    saved = hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]
    assert saved["saved_at"] == 4321.0 and saved["result"] == {NOW_TEMP[0]: 7.5}
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def _set_forecast_payload(api):
    """Populate both forecast periods with synthetic data in native units."""
    api.result = {NOW_TEMP[0]: 21, "Condition": "rainy", "Humidity": "61"}
    api.forecast_hour = [{
        "datetime": datetime(2030, 1, 1, hour, tzinfo=UTC),
        "condition": "rainy", "native_temperature": 23 + hour,
        "native_wind_speed": 2, "native_precipitation": 1.5,
        "precipitation_probability": 40, "humidity": 61,
        "wind_bearing": 135, "weathertype_hour": "wt9",
    } for hour in range(2)]
    api.forecast = [{
        "datetime": datetime(2030, 1, day, tzinfo=UTC),
        "condition_am": "sunny", "condition_pm": "rainy",
        "temperature": 22 + day, "templow": 12,
        "rain_rate_am": 20, "rain_rate_pm": 40,
        "weathertype_am": "wt1", "weathertype_pm": "wt9",
    } for day in (1, 2)]


@pytest.mark.asyncio
@pytest.mark.parametrize("sensors_first", [True, False])
@pytest.mark.parametrize("imperial", [False, True])
async def test_forecast_sensors_match_services_on_setup_and_clear_on_weather_removal(
    hass, sensors_first, imperial
):
    if imperial:
        hass.config.units = US_CUSTOMARY_SYSTEM
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "날씨"}, unique_id="synthetic")
    entry.add_to_hass(hass)
    calls = 0
    forecasts_ready, weather_ready = Event(), Event()
    added_forecasts = 0
    original_weather_added = NWeatherMain.async_added_to_hass
    original_sensor_added = NWeatherForecastSensor.async_added_to_hass

    async def update(api):
        nonlocal calls
        calls += 1
        _set_forecast_payload(api)

    async def weather_added(entity):
        if sensors_first:
            await forecasts_ready.wait()
        await original_weather_added(entity)
        weather_ready.set()

    async def sensor_added(entity):
        nonlocal added_forecasts
        if not sensors_first:
            await weather_ready.wait()
        await original_sensor_added(entity)
        added_forecasts += 1
        if added_forecasts == 2:
            forecasts_ready.set()

    with patch.object(NWeatherAPI, "update", update), patch.object(
        NWeatherMain, "async_added_to_hass", weather_added
    ), patch.object(NWeatherForecastSensor, "async_added_to_hass", sensor_added):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        api = hass.data[DOMAIN]["api"][entry.entry_id]
        registry = er.async_get(hass)
        weather_id = registry.async_get_entity_id("weather", DOMAIN, "날씨:Naver Weather Custom")
        assert weather_id is not None and api.weather_entity is not None
        sensor_ids = []
        for period, key in (("hourly", "ForecastHourly"), ("daily", "ForecastDaily")):
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"날씨:{key}")
            assert entity_id is not None
            sensor_ids.append(entity_id)
            state = hass.states.get(entity_id)
            assert state is not None and state.state == "rainy"
            forecasts = await hass.services.async_call(
                "weather", "get_forecasts", {"entity_id": weather_id, "type": period},
                blocking=True, return_response=True,
            )
            assert forecasts is not None
            forecast = forecasts[weather_id]["forecast"]
            assert state.attributes["forecast"] == forecast and len(forecast) == 2
            first = forecast[0]
            assert "temperature" in first and "native_temperature" not in first
            if period == "hourly":
                assert {"precipitation", "wind_speed", "weathertype_hour", "humidity"} <= first.keys()
                assert "native_precipitation" not in first and "native_wind_speed" not in first
                if imperial:
                    assert first["temperature"] != 23 and first["precipitation"] != 1.5
                else:
                    assert first["temperature"] == 23 and first["wind_speed"] == 7.2
                    assert first["precipitation"] == 1.5
            else:
                assert {"templow", "weathertype_am", "weathertype_pm", "rain_rate_am", "rain_rate_pm"} <= first.keys()
                assert "native_templow" not in first
        assert calls == 1

        registry.async_remove(weather_id)
        await hass.async_block_till_done()
        assert api.weather_entity is None and calls == 1
        for entity_id in sensor_ids:
            state = hass.states.get(entity_id)
            assert state is not None and state.attributes["forecast"] == []
            assert state.state == STATE_UNKNOWN
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_location_queries_change_on_refresh_while_all_entry_ids_stay_stable(hass):
    location_entity = "sensor.synthetic_location"
    hass.states.async_set(location_entity, "synthetic", {"Locality": "테스트시", "Sub Locality": "첫동"})
    moving = MockConfigEntry(domain=DOMAIN, data={CONF_LOCATION_ENTITY: location_entity, CONF_TODAY: True},
                             unique_id=f"location:{location_entity}")
    fixed = MockConfigEntry(domain=DOMAIN, data={CONF_AREA: "고정시"}, unique_id="고정시")
    moving.add_to_hass(hass)
    fixed.add_to_hass(hass)
    queries = []

    async def update(api, area=None):
        queries.append((api.entry.entry_id, area or api.area))
        _set_forecast_payload(api)

    with patch.object(NWeatherAPI, "update", update):
        # Setting up the first entry sets up the component, which loads every entry of the domain.
        assert await hass.config_entries.async_setup(moving.entry_id)
        await hass.async_block_till_done()
        assert moving.state is ConfigEntryState.LOADED and fixed.state is ConfigEntryState.LOADED
        registry = er.async_get(hass)
        moving_ids = {item.unique_id: item.entity_id for item in er.async_entries_for_config_entry(registry, moving.entry_id)}
        fixed_ids = {item.unique_id: item.entity_id for item in er.async_entries_for_config_entry(registry, fixed.entry_id)}
        keys = {*WEATHER_INFO, "ForecastHourly", "ForecastDaily", "Naver Weather Custom"}
        assert set(moving_ids) == {f"location_{moving.entry_id}:{key}" for key in keys}
        assert set(fixed_ids) == {f"고정시 날씨:{key}" for key in keys}
        devices = dr.async_get(hass)
        moving_device = devices.async_get_device_by_identifier((DOMAIN, f"location_{moving.entry_id}"), moving.entry_id)
        fixed_device = devices.async_get_device_by_identifier((DOMAIN, "고정시 날씨"), fixed.entry_id)
        assert moving_device is not None and moving_device.name == "Naver Weather Custom 현재 위치"
        assert moving_device.configuration_url is None
        assert fixed_device is not None and fixed_device.name == "Naver Weather Custom 고정시 날씨"
        assert fixed_device.configuration_url == BSE_URL.format("고정시 날씨")
        weather_id = moving_ids[f"location_{moving.entry_id}:Naver Weather Custom"]
        assert hass.states.get(weather_id) is not None
        moving_weather = hass.data[DOMAIN]["api"][moving.entry_id].weather_entity
        assert moving_weather is not None and moving_weather.entity_id == weather_id
        assert moving_weather.name == "현재 위치"

        hass.states.async_set(location_entity, "synthetic", {"Locality": "다른시", "Sub Locality": "다음동"})
        coordinator = hass.data[DOMAIN]["coordinators"][moving.entry_id]
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert sorted(queries[:2]) == sorted([(moving.entry_id, "테스트시 첫동 날씨"), (fixed.entry_id, "고정시 날씨")])
        assert queries[2:] == [(moving.entry_id, "다른시 다음동 날씨")]
        assert moving_ids == {item.unique_id: item.entity_id for item in er.async_entries_for_config_entry(registry, moving.entry_id)}
        assert fixed_ids == {item.unique_id: item.entity_id for item in er.async_entries_for_config_entry(registry, fixed.entry_id)}
        for entry in (moving, fixed):
            assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


def _location_weather_markup(location, temperature):
    day = datetime.now(api_module.KST).strftime("%m.%d.")
    weather = (
        '<span><i class="wt_icon ico_wt1"><span>맑음</span></i>'
        '<span class="weather_left"><span class="rainfall">10%</span></span></span>'
    )
    return f"""
        <div class="title_area _area_panel"><h2 class="title">{location}</h2></div>
        <div class="temperature_text">{temperature}°</div>
        <div class="open"><div class="graph_inner _hourly_weather"><ul>
          <li class="_li"><dl><dt class="time">12시</dt>
            <dd class="weather_box"><i class="wt_icon ico_wt1"><span>맑음</span></i></dd>
            <dd><span class="num">{temperature + 1}</span></dd>
          </dl></li>
        </ul></div></div>
        <div class="weekly_forecast_area _toggle_panel"><ul><li class="week_item"><div>
          <div class="cell_date"><span><strong class="day">오늘</strong><span class="date">{day}</span></span></div>
          <div class="cell_weather">{weather}{weather}</div>
          <span class="lowest">10°</span><span class="highest">{temperature + 2}°</span>
        </div></li></ul></div>
    """


@pytest.mark.asyncio
async def test_coordinate_move_commits_only_after_weather_and_air_succeed(hass, hass_storage, monkeypatch):
    location_entity = "sensor.synthetic_location"
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_LOCATION_ENTITY: location_entity, CONF_TODAY: True})
    entry.add_to_hass(hass)
    hass.states.async_set(location_entity, "synthetic", {"Location": [37.60069, 126.92676]})
    first, second = "은평구 응암1동", "은평구 응암2동"
    urls = {
        (location, kind): BSE_URL.format(f"서울특별시 {location} {kind}")
        for location in (first, second) for kind in ("날씨", "미세먼지")
    }
    replies = {
        urls[location, kind]: Mock(text=AsyncMock(return_value=markup))
        for location, temperature in ((first, 21), (second, 28))
        for kind, markup in (
            ("날씨", _location_weather_markup(location, temperature)),
            ("미세먼지", '<div class="state_info"><div class="grade"><div class="text_box">'
                      f'<span class="num">{temperature + 3}</span></div></div></div>'),
        )
    }
    rejected_air = Mock()
    rejected_air.raise_for_status.side_effect = _forbidden()
    second_air_url = urls[second, "미세먼지"]
    second_air = replies[second_air_url]
    replies[second_air_url] = rejected_air

    async def get(url, **_kwargs):
        return replies[url]

    session = Mock(get=AsyncMock(side_effect=get))
    monkeypatch.setattr(api_module, "async_get_clientsession", lambda _hass: session)
    save_key = f"{DOMAIN}.{entry.entry_id}"

    async def flush_storage():
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
        await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await flush_storage()
    coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
    api = coordinator.api
    payload, daily, hourly = coordinator.data, api.forecast, api.forecast_hour
    saved = hass_storage[save_key]["data"]
    last_good_refresh = coordinator.last_good_refresh
    assert payload[LOCATION[0]] == first
    assert payload[NDUST[0]] == "24"
    assert daily[0]["temperature"] == 23 and hourly[0]["native_temperature"] == 22
    assert saved["result"] == payload
    assert saved["forecast"][0]["temperature"] == 23 and saved["forecast_hour"][0]["native_temperature"] == 22

    hass.states.async_set(location_entity, "synthetic", {"Location": [37.59460, 126.92307]})
    await coordinator.async_refresh()
    await flush_storage()
    assert not coordinator.last_update_success
    replies[urls[second, "날씨"]].text.assert_awaited_once_with()
    rejected_air.raise_for_status.assert_called_once_with()
    assert coordinator.data is payload and api.result is payload
    assert api.result[LOCATION[0]] == first and api.forecast is daily and api.forecast_hour is hourly
    assert hass_storage[save_key]["data"] == saved and coordinator.last_good_refresh == last_good_refresh

    replies[second_air_url] = second_air
    await coordinator.async_refresh()
    await flush_storage()
    assert coordinator.last_update_success
    assert coordinator.data[LOCATION[0]] == second and coordinator.data[NDUST[0]] == "31"
    assert api.forecast[0]["temperature"] == 30 and api.forecast_hour[0]["native_temperature"] == 29
    recovered = hass_storage[save_key]["data"]
    assert recovered["result"] == coordinator.data
    assert recovered["forecast"][0]["temperature"] == 30
    assert recovered["forecast_hour"][0]["native_temperature"] == 29
    assert [call.args[0] for call in session.get.await_args_list] == [
        urls[location, kind]
        for location in (first, second, second) for kind in ("날씨", "미세먼지")
    ]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_location_without_locality_at_startup_keeps_stored_values_without_error(hass, hass_storage, caplog):
    location_entity = "sensor.synthetic_location"
    hass.states.async_set(location_entity, "synthetic", {})
    moving = MockConfigEntry(domain=DOMAIN, data={CONF_LOCATION_ENTITY: location_entity, CONF_TODAY: True},
                             unique_id=f"location:{location_entity}")
    moving.add_to_hass(hass)
    key = f"{DOMAIN}.{moving.entry_id}"
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": {
        "saved_at": 1000.0, "result": {NOW_TEMP[0]: 13.8}, "forecast": [], "forecast_hour": [],
        "weathertype": "맑음",
    }}
    areas = []

    async def update(api, area=None):
        areas.append(area)
        api.result = {NOW_TEMP[0]: 9.0}

    with patch.object(NWeatherAPI, "update", update), patch.object(
        coordinator_module, "time", lambda: 1000.0 + 600
    ):
        assert await hass.config_entries.async_setup(moving.entry_id)
        await hass.async_block_till_done()
        assert moving.state is ConfigEntryState.LOADED and areas == []
        temperature = er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, f"location_{moving.entry_id}:{NOW_TEMP[0]}"
        )
        assert temperature is not None
        state = hass.states.get(temperature)
        assert state is not None and float(state.state) == 13.8

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=11))
        await hass.async_block_till_done()
        assert areas == []
        state = hass.states.get(temperature)
        assert state is not None and float(state.state) == 13.8

        hass.states.async_set(location_entity, "synthetic", {"Locality": "테스트시", "Sub Locality": "첫동"})
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=22))
        await hass.async_block_till_done()
        assert areas == ["테스트시 첫동 날씨"]
        state = hass.states.get(temperature)
        assert state is not None and float(state.state) == 9.0
        assert not [r for r in caplog.records if r.levelname == "ERROR" and DOMAIN in r.name]
        assert await hass.config_entries.async_unload(moving.entry_id)
        await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_location_without_locality_expiring_stored_values_become_unavailable(hass, hass_storage):
    location_entity = "sensor.synthetic_location"
    hass.states.async_set(location_entity, "synthetic", {})
    moving = MockConfigEntry(domain=DOMAIN, data={CONF_LOCATION_ENTITY: location_entity, CONF_TODAY: True},
                             unique_id=f"location:{location_entity}")
    moving.add_to_hass(hass)
    key = f"{DOMAIN}.{moving.entry_id}"
    hass_storage[key] = {"version": 1, "minor_version": 1, "key": key, "data": {
        "saved_at": 1000.0, "result": {NOW_TEMP[0]: 13.8}, "forecast": [], "forecast_hour": [],
        "weathertype": "맑음",
    }}
    now = [1000.0 + 55 * 60]

    async def update(api):
        raise AssertionError("no fetch while the location is unknown")

    with patch.object(NWeatherAPI, "update", update), patch.object(
        coordinator_module, "time", lambda: now[0]
    ), patch.object(coordinator_module, "monotonic", lambda: now[0]):
        assert await hass.config_entries.async_setup(moving.entry_id)
        await hass.async_block_till_done()
        temperature = er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, f"location_{moving.entry_id}:{NOW_TEMP[0]}"
        )
        assert temperature is not None
        state = hass.states.get(temperature)
        assert state is not None and float(state.state) == 13.8

        now[0] += 11 * 60
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=11))
        await hass.async_block_till_done()
        state = hass.states.get(temperature)
        assert state is not None and state.state == STATE_UNAVAILABLE
        assert await hass.config_entries.async_unload(moving.entry_id)
        await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_location_config_flow_stores_only_sensor_and_today_and_rejects_duplicates(hass):
    location_entity = "sensor.synthetic_location"
    hass.states.async_set(location_entity, "synthetic", {"Locality": "테스트시 &"})
    with patch("custom_components.naver_weather_custom.async_setup_entry", return_value=True):
        flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert flow["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {
            CONF_LOCATION_ENTITY: location_entity, CONF_AREA: "ignored", CONF_TODAY: True,
        })
        assert result["type"] is FlowResultType.CREATE_ENTRY
        entry = result["result"]
        assert entry.title == "현재 위치" and entry.unique_id == f"location:{location_entity}"
        assert entry.data == {CONF_LOCATION_ENTITY: location_entity, CONF_TODAY: True}
        await hass.async_block_till_done()
        flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert flow["type"] is FlowResultType.FORM
        duplicate = await hass.config_entries.flow.async_configure(flow["flow_id"], {CONF_LOCATION_ENTITY: location_entity})
        assert duplicate["type"] is FlowResultType.ABORT
        assert duplicate["reason"] == "already_configured"


@pytest.mark.asyncio
@pytest.mark.parametrize("attributes", [None, {}, {"Locality": ""}, {"Locality": " n/a "},
                                        {"Locality": "& &"}, {"Locality": 1}, {"Sub Locality": "가상동"}])
async def test_location_config_flow_requires_an_existing_sensor_with_normalized_locality(hass, attributes):
    location_entity = "sensor.synthetic_location"
    if attributes is not None:
        hass.states.async_set(location_entity, "synthetic", attributes)
    flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert flow["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {CONF_LOCATION_ENTITY: location_entity})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_LOCATION_ENTITY: "invalid_location_entity"}


@pytest.mark.asyncio
@pytest.mark.parametrize("location_first", [True, False])
@pytest.mark.parametrize("fixed_area", ["", "날씨"])
async def test_location_and_default_fixed_area_config_flows_coexist_in_either_order(hass, location_first, fixed_area):
    location_entity = "sensor.synthetic_location"
    hass.states.async_set(location_entity, "synthetic", {"Locality": "테스트시"})
    inputs = [{CONF_LOCATION_ENTITY: location_entity}, {CONF_AREA: fixed_area}]
    if not location_first:
        inputs.reverse()
    with patch("custom_components.naver_weather_custom.async_setup_entry", return_value=True):
        entries = []
        for user_input in inputs:
            flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
            assert flow["type"] is FlowResultType.FORM
            result = await hass.config_entries.flow.async_configure(flow["flow_id"], user_input)
            assert result["type"] is FlowResultType.CREATE_ENTRY
            entries.append(result["result"])
            await hass.async_block_till_done()
        assert {entry.unique_id for entry in entries} == {f"location:{location_entity}", "날씨"}
        for entry in entries:
            if entry.unique_id == "날씨":
                assert entry.title == "날씨" and entry.data == {CONF_AREA: "날씨", CONF_TODAY: False}
            else:
                assert entry.title == "현재 위치" and entry.data == {CONF_LOCATION_ENTITY: location_entity, CONF_TODAY: False}

