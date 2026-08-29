"""Dependency-free regression checks for the custom-domain integration contract."""

import asyncio
import importlib
import json
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock


REPOSITORY = Path(__file__).resolve().parents[1]
INTEGRATION = REPOSITORY / "custom_components" / "naver_weather_custom"
sys.path.insert(0, str(REPOSITORY))


def _module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def install_home_assistant_shims() -> None:
    """Install the small Home Assistant surface needed by these unit tests."""
    bs4 = _module("bs4")
    bs4.BeautifulSoup = object

    class OptionalKey(str):
        def __new__(cls, value, default=None):
            key = super().__new__(cls, value)
            key.default = default
            return key

    voluptuous = _module("voluptuous")
    voluptuous.Schema = lambda value: value
    voluptuous.Optional = OptionalKey
    voluptuous.All = lambda *values: values
    voluptuous.Coerce = lambda value: value
    voluptuous.Range = lambda **kwargs: kwargs

    homeassistant = _module("homeassistant")
    config_entries = _module("homeassistant.config_entries")
    core = _module("homeassistant.core")
    helpers = _module("homeassistant.helpers")
    config_validation = _module("homeassistant.helpers.config_validation")
    aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
    update_coordinator = _module("homeassistant.helpers.update_coordinator")
    components = _module("homeassistant.components")
    sensor = _module("homeassistant.components.sensor")
    weather = _module("homeassistant.components.weather")
    const = _module("homeassistant.const")

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.helpers = helpers
    homeassistant.components = components
    helpers.config_validation = config_validation
    helpers.aiohttp_client = aiohttp_client
    helpers.update_coordinator = update_coordinator
    components.sensor = sensor
    components.weather = weather

    class ConfigEntry:
        pass

    class ConfigEntryNotReady(Exception):
        pass

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        async def async_set_unique_id(self, unique_id):
            self.unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            return None

        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    class OptionsFlow:
        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    class DataUpdateCoordinator:
        def __init__(self, hass, *, logger, name, update_interval, config_entry):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.config_entry = config_entry
            self.data = None
            self.last_update_success = False

        async def async_config_entry_first_refresh(self):
            try:
                self.data = await self._async_update_data()
            except Exception as err:
                self.last_update_success = False
                raise ConfigEntryNotReady from err
            self.last_update_success = True

        async def async_request_refresh(self):
            try:
                self.data = await self._async_update_data()
            except Exception:
                self.last_update_success = False
                return
            self.last_update_success = True

    class Entity:
        @property
        def unique_id(self):
            return getattr(self, "_attr_unique_id", None)

        @property
        def device_info(self):
            return getattr(self, "_attr_device_info", None)

    class CoordinatorEntity(Entity):
        def __init__(self, coordinator):
            self.coordinator = coordinator

        async def async_added_to_hass(self):
            return None

        async def async_will_remove_from_hass(self):
            return None

    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigEntryNotReady = ConfigEntryNotReady
    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.SOURCE_IMPORT = "import"
    core.HomeAssistant = object
    core.callback = lambda function: function
    config_validation.string = str
    aiohttp_client.async_get_clientsession = lambda hass: None
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    class WeatherEntity(Entity):
        pass

    weather.WeatherEntity = WeatherEntity
    weather.DOMAIN = "weather"
    weather.Forecast = dict
    weather.WeatherEntityFeature = types.SimpleNamespace(
        FORECAST_DAILY=1,
        FORECAST_TWICE_DAILY=2,
        FORECAST_HOURLY=4,
    )
    for name in (
        "ATTR_CONDITION_CLEAR_NIGHT",
        "ATTR_CONDITION_CLOUDY",
        "ATTR_CONDITION_FOG",
        "ATTR_CONDITION_HAIL",
        "ATTR_CONDITION_LIGHTNING",
        "ATTR_CONDITION_PARTLYCLOUDY",
        "ATTR_CONDITION_POURING",
        "ATTR_CONDITION_RAINY",
        "ATTR_CONDITION_SNOWY",
        "ATTR_CONDITION_SUNNY",
    ):
        setattr(weather, name, name.removeprefix("ATTR_CONDITION_").lower())
    for name, value in (
        ("ATTR_FORECAST_CONDITION", "condition"),
        ("ATTR_FORECAST_NATIVE_PRECIPITATION", "native_precipitation"),
        ("ATTR_FORECAST_NATIVE_TEMP", "native_temperature"),
        ("ATTR_FORECAST_NATIVE_TEMP_LOW", "native_templow"),
        ("ATTR_FORECAST_NATIVE_WIND_SPEED", "native_wind_speed"),
        ("ATTR_FORECAST_PRECIPITATION_PROBABILITY", "precipitation_probability"),
        ("ATTR_FORECAST_TEMP", "temperature"),
        ("ATTR_FORECAST_TEMP_LOW", "templow"),
        ("ATTR_FORECAST_TIME", "datetime"),
        ("ATTR_FORECAST_WIND_BEARING", "wind_bearing"),
        ("ATTR_FORECAST_WIND_SPEED", "wind_speed"),
    ):
        setattr(weather, name, value)
    sensor.SensorDeviceClass = types.SimpleNamespace(
        TEMPERATURE="temperature", HUMIDITY="humidity", PM25="pm25"
    )
    const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
    const.UnitOfDensity = types.SimpleNamespace(
        MICROGRAMS_PER_CUBIC_METER="µg/m³"
    )
    const.UnitOfPrecipitationDepth = types.SimpleNamespace(MILLIMETERS="mm")
    const.UnitOfSpeed = types.SimpleNamespace(METERS_PER_SECOND="m/s")
    const.UnitOfVolumetricFlux = types.SimpleNamespace(MILLIMETERS_PER_HOUR="mm/h")
    const.PERCENTAGE = "%"


install_home_assistant_shims()
for name in tuple(sys.modules):
    if name.startswith("custom_components.naver_weather_custom"):
        del sys.modules[name]

api_module = importlib.import_module(
    "custom_components.naver_weather_custom.api_nweather"
)
config_flow_module = importlib.import_module(
    "custom_components.naver_weather_custom.config_flow"
)
coordinator_module = importlib.import_module(
    "custom_components.naver_weather_custom.coordinator"
)
device_module = importlib.import_module(
    "custom_components.naver_weather_custom.nweather_device"
)
const_module = importlib.import_module("custom_components.naver_weather_custom.const")
weather_module = importlib.import_module("custom_components.naver_weather_custom.weather")
sensor_module = importlib.import_module("custom_components.naver_weather_custom.sensor")
integration_module = importlib.import_module("custom_components.naver_weather_custom")


_MISSING = object()


class FakeEntry:
    """Small config-entry replacement for API and flow tests."""

    def __init__(self, area="날씨", today=_MISSING, *, options=None, unique_id=None):
        self.data = {"area": area}
        if today is not _MISSING:
            self.data["today"] = today
        self.options = options or {}
        self.unique_id = unique_id


class FakeHass:
    """Only the API constructor needs a config-entry manager."""

    config_entries = types.SimpleNamespace(async_update_entry=lambda **kwargs: None)


class FakeNode:
    """Small selector-backed DOM node for parser contract tests."""

    def __init__(self, text="", *, classes=None, selections=None):
        self.text = text
        self._classes = list(classes or [])
        self._selections = selections or {}

    def select(self, selector):
        return self._selections.get(selector, [])

    def select_one(self, selector):
        return next(iter(self.select(selector)), None)

    def get(self, key, default=None):
        if key == "class":
            return self._classes
        return default

    def __getitem__(self, key):
        if key == "class":
            return self._classes
        raise KeyError(key)


class FakeSoup(FakeNode):
    """Root selector node used to keep tests dependency-free."""

    pass


class IntegrationContractTest(unittest.TestCase):
    """Protect coexistence and coordinator freshness behavior without Home Assistant."""

    def test_custom_domain_path_and_manifest_match(self):
        self.assertTrue(INTEGRATION.is_dir())
        self.assertFalse((REPOSITORY / "custom_components" / "naver_weather").exists())
        manifest = (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        self.assertIn('"domain": "naver_weather_custom"', manifest)
        self.assertIn("custom_components/naver_weather_custom/", (REPOSITORY / "README.md").read_text(encoding="utf-8"))

    def test_api_cold_fields_are_safe_before_first_refresh(self):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)
        self.assertEqual(api.result, {})
        self.assertEqual(api.forecast, [])
        self.assertEqual(api.forecast_hour, [])
        self.assertEqual(api.weathertype, "")

    def test_single_ten_minute_coordinator_reports_later_failure(self):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)
        calls = 0

        async def update():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("fixture refresh failure")
            api.result = {"NowTemp": "22"}

        api.update = update
        coordinator = coordinator_module.NWeatherDataUpdateCoordinator(
            FakeHass(), api, entry
        )
        self.assertEqual(coordinator.update_interval.total_seconds(), 600)
        self.assertIs(coordinator.config_entry, entry)
        asyncio.run(coordinator.async_config_entry_first_refresh())
        self.assertTrue(coordinator.last_update_success)
        self.assertEqual(coordinator.data, {"NowTemp": "22"})
        asyncio.run(coordinator.async_request_refresh())
        self.assertFalse(coordinator.last_update_success)

    def test_unload_platforms_success_cleans_up_and_false_preserves_state(self):
        entry = types.SimpleNamespace(entry_id="entry")

        for unload_result, should_clean in ((True, True), (False, False)):
            with self.subTest(unload_result=unload_result):
                manager = types.SimpleNamespace(
                    async_unload_platforms=AsyncMock(return_value=unload_result)
                )
                hass = types.SimpleNamespace(
                    config_entries=manager,
                    data={
                        const_module.DOMAIN: {
                            "api": {entry.entry_id: object()},
                            "coordinators": {entry.entry_id: object()},
                        }
                    },
                )

                result = asyncio.run(integration_module.async_unload_entry(hass, entry))

                self.assertEqual(should_clean, result)
                manager.async_unload_platforms.assert_awaited_once_with(
                    entry, const_module.PLATFORMS
                )
                for collection in hass.data[const_module.DOMAIN].values():
                    self.assertEqual(0 if should_clean else 1, len(collection))

    def test_unload_platforms_exception_propagates_without_cleanup(self):
        entry = types.SimpleNamespace(entry_id="entry")
        error = RuntimeError("platform unload failed")
        manager = types.SimpleNamespace(
            async_unload_platforms=AsyncMock(side_effect=error)
        )
        hass = types.SimpleNamespace(
            config_entries=manager,
            data={
                const_module.DOMAIN: {
                    "api": {entry.entry_id: object()},
                    "coordinators": {entry.entry_id: object()},
                }
            },
        )

        with self.assertRaisesRegex(RuntimeError, "platform unload failed"):
            asyncio.run(integration_module.async_unload_entry(hass, entry))
        self.assertIn(entry.entry_id, hass.data[const_module.DOMAIN]["api"])
        self.assertIn(entry.entry_id, hass.data[const_module.DOMAIN]["coordinators"])

    def test_weather_cast_optional_blind_label_is_safe(self):
        cases = (
            ("오늘 예보 blind 뒤", "blind", "뒤, 오늘 예보 blind"),
            ("원문", None, "원문"),
            ("원문", "", "원문"),
            ("원문", "blind", "원문"),
            ("", "blind", ""),
        )
        for text, blind, expected in cases:
            with self.subTest(text=text, blind=blind):
                self.assertEqual(expected, api_module.format_weather_cast(text, blind))

    def test_concrete_device_initializes_api_and_coordinator_bases(self):
        class ConcreteDevice(device_module.NWeatherDevice):
            pass

        api = api_module.NWeatherAPI(FakeHass(), FakeEntry("서울"), 1)
        coordinator = types.SimpleNamespace(last_update_success=True)
        device = ConcreteDevice(["Metric", "측정값", "", ""], api, coordinator)

        self.assertIs(device.api, api)
        self.assertEqual(device.area, "서울 날씨")
        self.assertIs(device.coordinator, coordinator)
        self.assertTrue(device.available)
        self.assertEqual(device.unique_id, "서울 날씨:Metric")
        self.assertEqual(set(api.unique), {"서울 날씨:Metric"})
        self.assertNotIn(None, api.unique)
        self.assertIs(device.register.__self__, api)
        self.assertIs(device.unregister.__self__, api)

        coordinator.last_update_success = False
        self.assertFalse(device.available)

    def test_first_refresh_failure_remains_an_error(self):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)

        async def update():
            raise RuntimeError("fixture cold-start failure")

        api.update = update
        coordinator = coordinator_module.NWeatherDataUpdateCoordinator(
            FakeHass(), api, entry
        )
        with self.assertRaises(config_flow_module.config_entries.ConfigEntryNotReady) as context:
            asyncio.run(coordinator.async_config_entry_first_refresh())
        self.assertFalse(coordinator.last_update_success)
        self.assertIsInstance(context.exception.__cause__, RuntimeError)
        self.assertIn("cold-start", str(context.exception.__cause__))

    def test_platforms_share_coordinator_and_never_poll_independently(self):
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        device_source = (INTEGRATION / "nweather_device.py").read_text(encoding="utf-8")
        sensor_source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
        weather_source = (INTEGRATION / "weather.py").read_text(encoding="utf-8")
        self.assertIn("async_config_entry_first_refresh", init_source)
        self.assertIn('"coordinators"', init_source)
        self.assertIn("CoordinatorEntity", device_source)
        self.assertIn("self.coordinator.last_update_success", device_source)
        self.assertIn("return False", device_source)
        self.assertNotIn("await self.api.update()", device_source)
        self.assertIn('["coordinators"][config_entry.entry_id]', sensor_source)
        self.assertIn('["coordinators"][config_entry.entry_id]', weather_source)
        self.assertNotIn("async def async_update", weather_source)

    def test_new_entries_use_canonical_area_without_legacy_identity_rewrites(self):
        self.assertEqual(config_flow_module.canonical_area("  Seoul\tStation  "), "seoul station")
        self.assertEqual(config_flow_module.canonical_area("  \n"), "날씨")
        flow = config_flow_module.ConfigFlow()
        legacy_entry = FakeEntry("Seoul Station", unique_id="legacy raw area")
        flow._async_current_entries = lambda: [legacy_entry]
        self.assertTrue(flow._area_is_configured("seoul station"))
        duplicate = asyncio.run(flow.async_step_user({"area": " Seoul  Station "}))
        self.assertEqual(duplicate, {"type": "abort", "reason": "already_configured"})
        self.assertEqual(legacy_entry.unique_id, "legacy raw area")

        new_flow = config_flow_module.ConfigFlow()
        new_flow._async_current_entries = lambda: []
        created = asyncio.run(new_flow.async_step_user({"area": " Seoul  Station "}))
        self.assertEqual(created["type"], "create_entry")
        self.assertEqual(new_flow.unique_id, "seoul station")
        self.assertNotEqual(new_flow.unique_id, "")

    def test_options_keep_today_but_cannot_change_area(self):
        source = (INTEGRATION / "config_flow.py").read_text(encoding="utf-8")
        self.assertIn("CONF_TODAY", source)
        self.assertIn("vol.Optional(CONF_TODAY, default=False)", source)
        self.assertNotIn("vol.Optional(CONF_AREA", source.split("class OptionsFlowHandler", 1)[1])
        options = config_flow_module.OptionsFlowHandler(FakeEntry("서울", today=True))
        result = asyncio.run(options.async_step_init())
        self.assertEqual(result["data_schema"], {"today": bool})
        self.assertTrue(next(iter(result["data_schema"])).default)
        saved = asyncio.run(options.async_step_init({"today": False}))
        self.assertEqual(saved["data"], {"today": False})

    def test_legacy_today_default_and_explicit_values_are_preserved(self):
        legacy = api_module.NWeatherAPI(FakeHass(), FakeEntry(), 1)
        self.assertTrue(legacy.today)
        self.assertFalse(api_module.NWeatherAPI(FakeHass(), FakeEntry(today=False), 1).today)
        self.assertTrue(api_module.NWeatherAPI(FakeHass(), FakeEntry(today=True), 1).today)

        for expected in (True, False):
            options = config_flow_module.OptionsFlowHandler(FakeEntry(today=expected))
            form = asyncio.run(options.async_step_init())
            self.assertEqual(next(iter(form["data_schema"])).default, expected)

        legacy_options = config_flow_module.OptionsFlowHandler(FakeEntry())
        legacy_form = asyncio.run(legacy_options.async_step_init())
        self.assertTrue(next(iter(legacy_form["data_schema"])).default)

    def test_air_request_failure_is_still_one_all_or_nothing_refresh(self):
        source = (INTEGRATION / "api_nweather.py").read_text(encoding="utf-8")
        self.assertIn("air.raise_for_status()", source)
        self.assertLess(source.index("air.raise_for_status()"), source.rindex("self.result = {"))
        self.assertIn("Failed to update NWeather API status", source)

    def test_existing_identity_constants_are_unchanged(self):
        self.assertEqual(const_module.DOMAIN, "naver_weather_custom")
        device_source = (INTEGRATION / "nweather_device.py").read_text(encoding="utf-8")
        self.assertIn('return self.area + ":" + self.device[0]', device_source)
        self.assertIn('"identifiers": {(DOMAIN, self.area)}', device_source)
        self.assertNotIn('"connections"', device_source)

    def test_entities_use_native_shared_device_info_without_identity_drift(self):
        self.assertEqual(len(const_module.WEATHER_INFO), 31)
        self.assertTrue(
            {"publicTimeC", "publicTimeH", "publicTimeW"}.issubset(
                const_module.WEATHER_INFO
            )
        )
        api = api_module.NWeatherAPI(FakeHass(), FakeEntry("서울"), 1)
        coordinator = types.SimpleNamespace(last_update_success=True)
        entities = [
            sensor_module.NWeatherSensor(
                const_module.WEATHER_INFO["NowTemp"], api, coordinator
            ),
            sensor_module.NWeatherSensor(
                const_module.WEATHER_INFO["Humidity"], api, coordinator
            ),
            weather_module.NWeatherMain(
                ["Naver Weather Custom", "네이버날씨Custom", "", ""],
                api,
                coordinator,
            ),
        ]
        expected_ids = {
            "서울 날씨:NowTemp",
            "서울 날씨:Humidity",
            "서울 날씨:Naver Weather Custom",
        }
        self.assertEqual(set(api.unique), expected_ids)
        for entity in entities:
            self.assertEqual(entity.unique_id, entity._attr_unique_id)
            self.assertEqual(
                entity.device_info["identifiers"],
                {(const_module.DOMAIN, "서울 날씨")},
            )
            self.assertIs(entity.device_info, entity._attr_device_info)
            self.assertNotIn("connections", entity.device_info)
            self.assertEqual(entity.device_info["manufacturer"], api.brand_name)
            self.assertEqual(entity.device_info["model"], f"{api.model}_{api.version}")
            self.assertEqual(entity.device_info["sw_version"], api.version)

    def test_publication_lines_use_exact_notice_selector_and_kst_nearest_year(self):
        notices = [FakeNode(
            "현재 및 1시간예보\n"
            "발표시간 : 12.31. 23:45\n"
            "시간별예보\n"
            "발표시간 : 01.01. 00:00\n"
            "주간예보\n"
            "발표시간 : 12.30. 18:00"
        )]
        soup = FakeSoup(
            selections={api_module.PUBLICATION_TIME_SELECTOR: notices}
        )
        reference = datetime(2026, 1, 1, 0, 30, tzinfo=api_module.KST)
        self.assertEqual(
            api_module.parse_publication_times(soup, reference),
            {
                "publicTimeC": "2025-12-31T23:45:00+09:00",
                "publicTimeH": "2026-01-01T00:00:00+09:00",
                "publicTimeW": "2025-12-30T18:00:00+09:00",
            },
        )
        malformed = FakeSoup(
            selections={api_module.PUBLICATION_TIME_SELECTOR: [FakeNode(
                "현재 및 1시간예보\n발표시간 : 02.31. 25:99\n"
                "시간별예보\n발표시간 : 01.01 00:15\n"
                "주간예보\n발표시간 : 01.01. 01:15"
            )]}
        )
        self.assertEqual(
            api_module.parse_publication_times(malformed, reference),
            {
                "publicTimeC": None,
                "publicTimeH": "2026-01-01T00:15:00+09:00",
                "publicTimeW": "2026-01-01T01:15:00+09:00",
            },
        )
        self.assertIsNone(
            api_module.resolve_public_timestamp_kst("주간예보: 02.31. 25:99", reference)
        )
        self.assertEqual(
            api_module.parse_publication_times(FakeSoup(), reference),
            {"publicTimeC": None, "publicTimeH": None, "publicTimeW": None},
        )
        self.assertEqual(
            api_module.PUBLICATION_TIME_SELECTOR,
            "div.api_subject_bx._weekly_weather_wrap div.notice_area._related_info._info_layer_wrap div.layer_pop._select_panel > p.desc",
        )

    def test_hourly_open_panel_alignment_wind_and_optional_arrays(self):
        def hourly_row(label, temperature, condition):
            icon = (
                [FakeNode(classes=["wt_icon", f"ico_{condition}"])]
                if condition
                else []
            )
            return FakeNode(
                selections={
                    "dt.time": [FakeNode(label)],
                    "span.num": [FakeNode(temperature)],
                    "dd.weather_box > i": icon,
                }
            )

        rows = [hourly_row("18시", "10", "wt1"), hourly_row("19시", "11", "wt9")]
        reference = datetime(2026, 8, 27, 18, tzinfo=api_module.KST)
        open_panel = FakeNode(
            selections={
                api_module.HOURLY_ROW_SELECTOR: rows,
                api_module.HOURLY_RAIN_PERCENT_SELECTOR: [
                    FakeNode("20%"),
                    FakeNode("40%"),
                ],
                api_module.HOURLY_RAINFALL_SELECTOR: [
                    FakeNode("1.5mm"),
                    FakeNode("2.5mm"),
                ],
                api_module.HOURLY_HUMIDITY_SELECTOR: [
                    FakeNode("60"),
                    FakeNode("61"),
                ],
                api_module.HOURLY_WIND_DIRECTION_SELECTOR: [
                    FakeNode("북서풍"),
                    FakeNode("남동풍"),
                ],
                api_module.HOURLY_WIND_SPEED_SELECTOR: [
                    FakeNode("3"),
                    FakeNode("4"),
                ],
            }
        )
        soup = FakeSoup(selections={"div.open": [open_panel]})
        selected = api_module._open_hourly_panel(soup)
        self.assertIs(selected, open_panel)
        # Arrays are read only from the selected open panel.
        forecast = api_module.parse_hourly_forecast(open_panel, reference)
        self.assertEqual(len(forecast), 2)
        row = forecast[1]
        self.assertEqual(row["datetime"].isoformat(), "2026-08-27T19:00:00+09:00")
        self.assertEqual(row["native_temperature"], 11.0)
        self.assertEqual(row["condition"], "rainy")
        self.assertEqual(row["precipitation_probability"], 40)
        self.assertEqual(row["native_precipitation"], 2.5)
        self.assertEqual(row["humidity"], 61.0)
        self.assertEqual(row["wind_bearing"], 135)
        self.assertEqual(row["wind_speed"], 4.0)

        sparse_panel = FakeNode(
            selections={
                api_module.HOURLY_ROW_SELECTOR: rows,
                # Optional arrays may be shorter than the row list without
                # dropping the remaining valid hourly rows.
                api_module.HOURLY_RAIN_PERCENT_SELECTOR: [FakeNode("30%")],
                api_module.HOURLY_RAINFALL_SELECTOR: [FakeNode("0.5mm")],
            }
        )
        sparse = api_module.parse_hourly_forecast(sparse_panel, reference)
        self.assertEqual(len(sparse), 2)
        self.assertEqual(sparse[0]["precipitation_probability"], 30)
        self.assertEqual(sparse[0]["native_precipitation"], 0.5)
        self.assertIsNone(sparse[1]["precipitation_probability"])
        self.assertIsNone(sparse[1]["native_precipitation"])
        self.assertIsNone(sparse[1]["humidity"])
        self.assertIsNone(sparse[1]["wind_speed"])
        self.assertIsNone(
            api_module.parse_hourly_forecast(
                FakeNode(selections={api_module.HOURLY_ROW_SELECTOR: [hourly_row("20시", "12", None)]}),
                reference,
            )[0]["condition"]
        )

    def test_wind_direction_variants_and_native_forecast_fields(self):
        for label, expected in (
            ("북", 0),
            ("북북동풍", 22.5),
            ("동풍", 90),
            ("남서풍", 225),
            ("서북서", 292.5),
            ("NW", 315),
        ):
            with self.subTest(label=label):
                self.assertEqual(api_module.parse_wind_direction(label), expected)
        self.assertEqual(api_module.parse_wind_text("북서풍 3.25m/s"), (315, 3.25))

        api = api_module.NWeatherAPI(FakeHass(), FakeEntry(), 1)
        api.result["WindSpeed"] = "2.5"
        coordinator = types.SimpleNamespace(last_update_success=True)
        entity = weather_module.NWeatherMain(
            ["Naver Weather Custom", "네이버날씨Custom", "", ""], api, coordinator
        )
        self.assertEqual(entity.native_wind_speed, 2.5)
        self.assertEqual(entity._attr_native_wind_speed_unit, "m/s")
        self.assertEqual(entity._attr_native_precipitation_unit, "mm")
        reference_time = datetime(2026, 8, 27, 19, tzinfo=api_module.KST)
        api.forecast_hour = [
            {
                "datetime": reference_time,
                "condition": "rainy",
                "native_temperature": 21.0,
                "precipitation_probability": 40,
                "wind_bearing": 135,
                "wind_speed": 4.0,
                "native_precipitation": 1.0,
                "humidity": 60.0,
            }
        ]
        hourly = entity._forecast_hour(4)
        self.assertEqual(hourly[0]["datetime"], "2026-08-27T10:00:00+00:00")
        self.assertEqual(hourly[0]["native_temperature"], 21.0)
        self.assertEqual(hourly[0]["native_precipitation"], 1.0)
        self.assertEqual(hourly[0]["wind_bearing"], 135)
        self.assertEqual(hourly[0]["native_wind_speed"], 4.0)
        self.assertNotIn("temperature", hourly[0])
        self.assertNotIn("wind_speed", hourly[0])

        api.forecast = [
            {
                "datetime": reference_time,
                "condition_am": "sunny",
                "condition_pm": "rainy",
                "templow": 12.0,
                "temperature": 22.0,
                "rain_rate_am": 20,
                "rain_rate_pm": 40,
                "weathertype_am": "wt1",
                "weathertype_pm": "wt9",
            }
        ]
        daily = entity._forecast(1)
        self.assertEqual(daily[0]["datetime"], "2026-08-27T10:00:00+00:00")
        self.assertEqual(daily[0]["native_temperature"], 22.0)
        self.assertEqual(daily[0]["native_templow"], 12.0)

    def test_forecast_rollover_resolvers_and_today_presentation(self):
        fixture = json.loads(
            (REPOSITORY / "tests/fixtures/forecast_rollover.json").read_text(
                encoding="utf-8"
            )
        )
        reference = api_module.datetime.fromisoformat(fixture["reference"])
        daily = [
            api_module.resolve_daily_timestamp_kst(label, reference)
            for label in fixture["daily_labels"]
        ]
        hourly = api_module.resolve_hourly_timestamps_kst(
            fixture["hourly_labels"], reference
        )
        self.assertEqual(
            [timestamp.isoformat() for timestamp in daily], fixture["expected_daily"]
        )
        self.assertEqual(
            [timestamp.isoformat() for timestamp in hourly], fixture["expected_hourly"]
        )
        self.assertTrue(all(timestamp.tzinfo is not None for timestamp in hourly))
        self.assertTrue(all(left < right for left, right in zip(hourly, hourly[1:])))

        rows = [{"datetime": timestamp, "value": index} for index, timestamp in enumerate(daily)]
        self.assertEqual(
            api_module.filter_daily_forecast_rows(rows, False, reference), rows[1:]
        )
        self.assertEqual(
            api_module.filter_daily_forecast_rows(rows, True, reference), rows
        )
        self.assertEqual(rows[0]["value"], 0)


if __name__ == "__main__":
    unittest.main()
