"""Dependency-free regression checks for the custom-domain integration contract."""

import asyncio
import importlib
import json
import sys
import types
import unittest
from pathlib import Path


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
    const = _module("homeassistant.const")

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.helpers = helpers
    homeassistant.components = components
    helpers.config_validation = config_validation
    helpers.aiohttp_client = aiohttp_client
    helpers.update_coordinator = update_coordinator
    components.sensor = sensor

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
    sensor.SensorDeviceClass = types.SimpleNamespace(
        TEMPERATURE="temperature", HUMIDITY="humidity", PM25="pm25"
    )
    const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
    const.UnitOfSpeed = types.SimpleNamespace(METERS_PER_SECOND="m/s")
    const.UnitOfVolumetricFlux = types.SimpleNamespace(MILLIMETERS_PER_HOUR="mm/h")
    const.PERCENTAGE = "%"
    const.CONCENTRATION_PARTS_PER_MILLION = "ppm"
    const.CONCENTRATION_MICROGRAMS_PER_CUBIC_METER = "µg/m³"


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
        self.assertIn("DOMAIN,\n                    self.area", device_source)

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
