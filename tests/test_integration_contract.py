"""Dependency-free regression checks for the custom-domain integration contract."""

import ast
import asyncio
import importlib
import json
import sys
import types
import unittest
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from unittest.mock import AsyncMock, Mock, PropertyMock, patch

REPOSITORY = Path(__file__).resolve().parents[1]
INTEGRATION = REPOSITORY / "custom_components" / "naver_weather_custom"
sys.path.insert(0, str(REPOSITORY))


def _module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def _set_attributes(module: types.ModuleType, **attributes: object) -> None:
    """Populate deliberate module shims through Python's dynamic module interface."""
    for name, value in attributes.items():
        setattr(module, name, value)


def install_home_assistant_shims() -> None:
    """Install the small Home Assistant surface needed by these unit tests."""
    aiohttp = _module("aiohttp")

    class ClientTimeout:
        def __init__(self, *, total):
            self.total = total

    class ClientError(Exception):
        pass

    _set_attributes(aiohttp, ClientTimeout=ClientTimeout, ClientError=ClientError)
    bs4 = _module("bs4")
    _set_attributes(bs4, __path__=[])
    _set_attributes(bs4, BeautifulSoup=object)
    bs4_element = _module("bs4.element")
    _set_attributes(bs4_element, Tag=type("Tag", (), {}))
    _set_attributes(bs4, element=bs4_element)

    class OptionalKey(str):
        default: object
        description: object
        def __new__(cls, value, default=None, description=None):
            key = super().__new__(cls, value)
            key.default = default
            key.description = description
            return key

    voluptuous = _module("voluptuous")
    _set_attributes(voluptuous, Schema=lambda value: value)
    _set_attributes(voluptuous, Optional=OptionalKey)
    _set_attributes(voluptuous, Required=OptionalKey)
    _set_attributes(voluptuous, All=lambda *values: values)
    _set_attributes(voluptuous, Coerce=lambda value: value)
    _set_attributes(voluptuous, Range=lambda **kwargs: kwargs)

    homeassistant = _module("homeassistant")
    auth = _module("homeassistant.auth")
    permissions = _module("homeassistant.auth.permissions")
    permissions_const = _module("homeassistant.auth.permissions.const")
    config_entries = _module("homeassistant.config_entries")
    core = _module("homeassistant.core")
    helpers = _module("homeassistant.helpers")
    config_validation = _module("homeassistant.helpers.config_validation")
    aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
    update_coordinator = _module("homeassistant.helpers.update_coordinator")
    storage = _module("homeassistant.helpers.storage")
    selector = _module("homeassistant.helpers.selector")
    exceptions = _module("homeassistant.exceptions")
    components = _module("homeassistant.components")
    frontend = _module("homeassistant.components.frontend")
    http = _module("homeassistant.components.http")
    http_server = _module("homeassistant.components.http.server")
    websocket_api = _module("homeassistant.components.websocket_api")
    websocket_connection = _module("homeassistant.components.websocket_api.connection")
    websocket_decorators = _module("homeassistant.components.websocket_api.decorators")
    entity_registry = _module("homeassistant.helpers.entity_registry")
    sensor = _module("homeassistant.components.sensor")
    weather = _module("homeassistant.components.weather")
    weather_const = _module("homeassistant.components.weather.const")
    const = _module("homeassistant.const")

    _set_attributes(homeassistant, config_entries=config_entries)
    _set_attributes(homeassistant, auth=auth)
    _set_attributes(auth, permissions=permissions)
    _set_attributes(permissions, const=permissions_const)
    _set_attributes(permissions_const, POLICY_READ="read")
    _set_attributes(homeassistant, core=core)
    _set_attributes(homeassistant, helpers=helpers)
    _set_attributes(homeassistant, components=components)
    _set_attributes(helpers, config_validation=config_validation)
    _set_attributes(helpers, aiohttp_client=aiohttp_client)
    _set_attributes(helpers, storage=storage)
    _set_attributes(helpers, selector=selector)
    _set_attributes(selector, EntitySelector=lambda config: config)
    _set_attributes(selector, EntitySelectorConfig=lambda **kwargs: kwargs)
    _set_attributes(homeassistant, exceptions=exceptions)
    _set_attributes(helpers, update_coordinator=update_coordinator)
    _set_attributes(helpers, entity_registry=entity_registry)
    _set_attributes(components, frontend=frontend, http=http, websocket_api=websocket_api)
    _set_attributes(frontend, add_extra_js_url=Mock())
    _set_attributes(http, server=http_server)
    _set_attributes(http_server, StaticPathConfig=Mock())
    _set_attributes(websocket_api, connection=websocket_connection, decorators=websocket_decorators)
    _set_attributes(websocket_decorators, websocket_command=lambda schema: lambda function: function)
    _set_attributes(websocket_api, async_register_command=Mock())
    _set_attributes(websocket_connection, ActiveConnection=object)
    _set_attributes(components, sensor=sensor)
    _set_attributes(components, weather=weather)

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
        @property
        def config_entry(self):
            raise ValueError("Unavailable before HA initializes the flow")

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

    class DataUpdateCoordinator:
        @classmethod
        def __class_getitem__(cls, item):
            return cls

        async def _async_update_data(self):
            raise NotImplementedError

        def __init__(self, hass, *, logger, name, update_interval, config_entry):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.config_entry = config_entry
            self.data = None
            self.last_update_success = False
            self.listener_updates = 0

        def async_update_listeners(self):
            self.listener_updates += 1

        async def async_shutdown(self):
            return None

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
            except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
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
        @classmethod
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

        async def async_added_to_hass(self):
            return None

        async def async_will_remove_from_hass(self):
            return None

    _set_attributes(config_entries, ConfigEntry=ConfigEntry)
    _set_attributes(config_entries, ConfigEntryState=types.SimpleNamespace(LOADED="loaded"))
    _set_attributes(config_entries, ConfigFlowResult=dict)
    _set_attributes(config_entries, ConfigEntryNotReady=ConfigEntryNotReady)
    _set_attributes(exceptions, ConfigEntryNotReady=ConfigEntryNotReady)

    class Store:
        @classmethod
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, version, key):
            self.key = key
            self.data = None

        async def async_load(self):
            return self.data

        def async_delay_save(self, data_func, delay=0):
            self.data = data_func()

    _set_attributes(storage, Store=Store)
    _set_attributes(config_entries, ConfigFlow=ConfigFlow)
    _set_attributes(config_entries, OptionsFlow=OptionsFlow)
    _set_attributes(config_entries, SOURCE_IMPORT="import")
    _set_attributes(core, HomeAssistant=object)
    _set_attributes(core, callback=lambda function: function)
    _set_attributes(config_validation, string=str)
    _set_attributes(aiohttp_client, async_get_clientsession=lambda hass: None)
    _set_attributes(update_coordinator, DataUpdateCoordinator=DataUpdateCoordinator)
    _set_attributes(update_coordinator, UpdateFailed=type("UpdateFailed", (Exception,), {}))
    _set_attributes(update_coordinator, CoordinatorEntity=CoordinatorEntity)
    class WeatherEntity(Entity):
        @property
        def state(self):
            return getattr(self, "condition", None)

    _set_attributes(weather, WeatherEntity=WeatherEntity)
    _set_attributes(weather, DOMAIN="weather")
    _set_attributes(weather, Forecast=dict)
    _set_attributes(weather, WeatherEntityFeature=types.SimpleNamespace(
        FORECAST_DAILY=1,
        FORECAST_TWICE_DAILY=2,
        FORECAST_HOURLY=4,
    ))
    _set_attributes(weather_const, WeatherEntityFeature=vars(weather)["WeatherEntityFeature"])
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
    _set_attributes(sensor, SensorDeviceClass=types.SimpleNamespace(
        TEMPERATURE="temperature", HUMIDITY="humidity", PM25="pm25"
    ))
    _set_attributes(const, UnitOfTemperature=types.SimpleNamespace(CELSIUS="°C"))
    _set_attributes(const, UnitOfDensity=types.SimpleNamespace(
        MICROGRAMS_PER_CUBIC_METER="µg/m³"
    ))
    _set_attributes(const, UnitOfPrecipitationDepth=types.SimpleNamespace(MILLIMETERS="mm"))
    _set_attributes(const, UnitOfSpeed=types.SimpleNamespace(METERS_PER_SECOND="m/s"))
    _set_attributes(const, UnitOfVolumetricFlux=types.SimpleNamespace(MILLIMETERS_PER_HOUR="mm/h"))
    _set_attributes(const, PERCENTAGE="%")


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
        self.data: dict[str, object] = {"area": area}
        if today is not _MISSING:
            self.data["today"] = today
        self.options = options or {}
        self.unique_id = unique_id
        self.entry_id = "entry"


class FakeHass:
    """Supply the state and config surfaces used by the API and coordinator."""

    config_entries = types.SimpleNamespace(async_update_entry=lambda **kwargs: None)

    def __init__(self):
        self.states: dict[str, types.SimpleNamespace] = {}
        self.data: dict[str, object] = {}
        self.config = types.SimpleNamespace(components=set())
        self.http = None


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

    def test_current_humidity_retains_only_last_valid_value(self):
        self.assertIsNone(api_module.retain_previous_humidity(None, None))
        self.assertEqual(api_module.retain_previous_humidity(None, "61"), "61")
        self.assertEqual(api_module.retain_previous_humidity("malformed", "61"), "61")
        self.assertEqual(api_module.retain_previous_humidity("-1", "61"), "61")
        self.assertEqual(api_module.retain_previous_humidity("101", "61"), "61")
        self.assertEqual(api_module.retain_previous_humidity("62", "61"), "62")
        self.assertEqual(api_module.retain_previous_humidity("0", "61"), "0")
        self.assertEqual(api_module.retain_previous_humidity("100", "61"), "100")
        self.assertEqual(api_module.retain_previous_humidity(None, "101"), None)
        tree = ast.parse(
            (INTEGRATION / "api_nweather.py").read_text(encoding="utf-8")
        )
        assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "Humidity"
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1)
        call = assignments[0].value
        assert isinstance(call, ast.Call)
        assert isinstance(call.func, ast.Name)
        self.assertEqual(call.func.id, "retain_previous_humidity")
        self.assertEqual(len(call.args), 2)
        current = call.args[0]
        assert isinstance(current, ast.Call)
        assert isinstance(current.func, ast.Name)
        self.assertEqual(current.func.id, "re2num")
        self.assertEqual(len(current.args), 1)
        current_key = current.args[0]
        assert isinstance(current_key, ast.Call)
        assert isinstance(current_key.func, ast.Name)
        self.assertEqual(current_key.func.id, "re2key")
        self.assertEqual(len(current_key.args), 2)
        assert isinstance(current_key.args[0], ast.Constant)
        self.assertEqual(current_key.args[0].value, "습도")
        assert isinstance(current_key.args[1], ast.Name)
        self.assertEqual(current_key.args[1].id, "summ")
        previous = call.args[1]
        assert isinstance(previous, ast.Name)
        self.assertEqual(previous.id, "previous_humidity")
        previous_assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "previous_humidity"
                for target in node.targets
            )
        ]
        self.assertEqual(len(previous_assignments), 1)
        conditional = previous_assignments[0].value
        assert isinstance(conditional, ast.IfExp)
        previous = conditional.body
        assert isinstance(previous, ast.Call)
        assert isinstance(previous.func, ast.Attribute)
        self.assertEqual(previous.func.attr, "get")
        assert isinstance(previous.func.value, ast.Attribute)
        self.assertEqual(previous.func.value.attr, "result")
        assert isinstance(previous.func.value.value, ast.Name)
        self.assertEqual(previous.func.value.value.id, "self")
        assert isinstance(previous.args[0], ast.Subscript)
        assert isinstance(previous.args[0].value, ast.Name)
        self.assertEqual(previous.args[0].value.id, "NOW_HUMI")
        assert isinstance(previous.args[0].slice, ast.Constant)
        self.assertEqual(previous.args[0].slice.value, 0)

    @patch.object(coordinator_module, "FETCH_GAP", 0)
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

    @patch.object(coordinator_module, "FETCH_GAP", 0)
    def test_failed_refreshes_keep_last_good_data_for_one_hour(self):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)
        fail = False

        async def update():
            if fail:
                raise RuntimeError("fixture refresh failure")
            api.result = {"NowTemp": "22"}

        api.update = update
        coordinator = coordinator_module.NWeatherDataUpdateCoordinator(
            FakeHass(), api, entry
        )
        self.assertFalse(coordinator.has_recent_data)
        with patch.object(coordinator_module, "monotonic", return_value=1000.0):
            asyncio.run(coordinator.async_config_entry_first_refresh())
        fail = True
        for now, recent in ((1000.0 + 3599, True), (1000.0 + 3600, False)):
            with self.subTest(age=now - 1000.0), patch.object(
                coordinator_module, "monotonic", return_value=now
            ):
                asyncio.run(coordinator.async_request_refresh())
                self.assertFalse(coordinator.last_update_success)
                self.assertEqual(coordinator.data, {"NowTemp": "22"})
                self.assertIs(coordinator.has_recent_data, recent)
                self.assertEqual(coordinator.listener_updates, 0 if recent else 1)

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
        coordinator = types.SimpleNamespace(
            last_update_success=True, has_recent_data=False
        )
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

        coordinator.has_recent_data = True
        self.assertTrue(device.available)

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

    def _restore_case(self, stored):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)

        async def update():
            raise RuntimeError("fixture refused")

        api.update = update
        coordinator = coordinator_module.NWeatherDataUpdateCoordinator(FakeHass(), api, entry)
        coordinator._store.data = stored
        return api, coordinator

    def test_successful_refresh_stores_a_recoverable_payload(self):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)
        moment = datetime(2026, 11, 11, 13, 0, tzinfo=api_module.KST)

        async def update():
            api.result = {"NowTemp": "13.8", "publicTimeC": moment}
            api.forecast = [{"datetime": moment, "templow": 2}]
            api.forecast_hour = [{"datetime": moment, "native_temperature": 13}]
            api.weathertype = "맑음"

        api.update = update
        coordinator = coordinator_module.NWeatherDataUpdateCoordinator(FakeHass(), api, entry)
        with patch.object(coordinator_module, "time", return_value=5000.0):
            asyncio.run(coordinator.async_config_entry_first_refresh())
        stored = coordinator._store.data
        self.assertEqual(stored["saved_at"], 5000.0)
        self.assertEqual(stored["result"]["publicTimeC"], {"__datetime__": moment.isoformat()})
        json.dumps(stored)
        restored = coordinator_module._decode(stored)
        self.assertEqual(restored["result"], api.result)
        self.assertEqual(restored["forecast"], api.forecast)
        self.assertEqual(restored["forecast_hour"], api.forecast_hour)

    def test_failed_first_refresh_starts_from_a_recent_stored_payload(self):
        payload = coordinator_module._encode({
            "saved_at": 10_000.0 - 600,
            "result": {"NowTemp": "13.8"},
            "forecast": [{"datetime": datetime(2026, 11, 12, tzinfo=api_module.KST)}],
            "forecast_hour": [],
            "weathertype": "맑음",
        })
        api, coordinator = self._restore_case(payload)
        with patch.object(coordinator_module, "time", return_value=10_000.0), patch.object(
            coordinator_module, "monotonic", return_value=50_000.0
        ):
            asyncio.run(coordinator.async_config_entry_first_refresh())
            self.assertFalse(coordinator.last_update_success)
            self.assertTrue(coordinator.has_recent_data)
        self.assertEqual(api.result, {"NowTemp": "13.8"})
        self.assertEqual(coordinator.data, {"NowTemp": "13.8"})
        self.assertIsInstance(api.forecast[0]["datetime"], datetime)
        self.assertEqual(api.weathertype, "맑음")
        self.assertEqual(coordinator.last_good_refresh, 50_000.0 - 600)

    def test_restore_accepts_a_payload_without_a_weather_type(self):
        payload = {"saved_at": 10_000.0 - 600, "result": {"NowTemp": "13.8"},
                   "forecast": [], "forecast_hour": [], "weathertype": None}
        api, coordinator = self._restore_case(payload)
        with patch.object(coordinator_module, "time", return_value=10_000.0):
            asyncio.run(coordinator.async_config_entry_first_refresh())
        self.assertIsNone(api.weathertype)
        self.assertEqual(api.result, {"NowTemp": "13.8"})

    def test_failed_first_refresh_without_usable_stored_payload_stays_not_ready(self):
        recent = {"saved_at": 10_000.0 - 600, "result": {}, "forecast": [],
                  "forecast_hour": [], "weathertype": ""}
        cases = {
            "nothing stored": None,
            "an hour old": {**recent, "saved_at": 10_000.0 - 3600},
            "from the future": {**recent, "saved_at": 10_000.0 + 1},
            "missing key": {key: value for key, value in recent.items() if key != "forecast"},
            "wrong type": {**recent, "result": []},
            "bad saved_at": {**recent, "saved_at": "soon"},
            "bad datetime": {**recent, "forecast": [{"datetime": {"__datetime__": "x"}}]},
            "not a dict": [recent],
        }
        for name, stored in cases.items():
            with self.subTest(name), patch.object(coordinator_module, "time", return_value=10_000.0):
                api, coordinator = self._restore_case(stored)
                with self.assertRaises(config_flow_module.config_entries.ConfigEntryNotReady):
                    asyncio.run(coordinator.async_config_entry_first_refresh())
                self.assertEqual(api.result, {})
                self.assertFalse(coordinator.has_recent_data)

    def test_direct_naver_requests_use_the_shared_session_defaults(self):
        source = (INTEGRATION / "api_nweather.py").read_text(encoding="utf-8")
        self.assertNotIn("client_context", source)
        self.assertNotIn("ssl=", source)
        self.assertEqual(source.count("session.get(url, headers=hdr, timeout="), 1)
        self.assertEqual(source.count("session.get(url_air, headers=hdr, timeout="), 1)

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
        new_flow._async_current_entries = list
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
        self.assertEqual(list(result["data_schema"]), ["today", "browser_url"])
        self.assertEqual(result["data_schema"], {"today": bool, "browser_url": str})
        self.assertTrue(next(iter(result["data_schema"])).default)
        saved = asyncio.run(options.async_step_init({"today": False}))
        self.assertEqual(saved["data"], {"today": False})

    def test_options_translations_match_the_area_immutable_form(self):
        for name in ("strings.json", "translations/en.json", "translations/ko.json"):
            with self.subTest(name=name):
                translations = json.loads((INTEGRATION / name).read_text(encoding="utf-8"))
                self.assertIn("area", translations["config"]["step"]["user"]["data"])
                self.assertEqual(
                    set(translations["options"]["step"]["init"]["data"]), {"today", "browser_url"}
                )

    def test_browser_option_translations_include_errors_and_korean_text(self):
        for name in ("strings.json", "translations/en.json", "translations/ko.json"):
            with self.subTest(name=name):
                options = json.loads((INTEGRATION / name).read_text(encoding="utf-8"))["options"]
                label = options["step"]["init"]["data"]["browser_url"]
                error = options["error"]["invalid_browser_url"]
                self.assertTrue(label)
                self.assertTrue(error)
                if name == "translations/ko.json":
                    self.assertTrue(any("가" <= char <= "힣" for char in label))
                    self.assertTrue(any("가" <= char <= "힣" for char in error))
                    self.assertIn("선택", label)
                    self.assertIn("직접 요청", label)

    def test_browser_address_is_read_from_current_options(self):
        entry = FakeEntry()
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)
        self.assertEqual(api.browser_url, "")
        for address in ("http://browser.invalid:8765", "https://browser.invalid"):
            entry.options["browser_url"] = address
            self.assertEqual(api.browser_url, address)
        entry.options.pop("browser_url")
        self.assertEqual(api.browser_url, "")

    def test_browser_helper_success_failure_cleanup_and_private_logs(self):
        entry = FakeEntry()
        entry.options["browser_url"] = "http://browser.invalid:8765"
        api = api_module.NWeatherAPI(FakeHass(), entry, 1)
        url = "https://search.naver.com/search.naver?query=private-area"
        response = Mock(status=200, text=AsyncMock(return_value="<html>weather</html>"))
        session = Mock(get=AsyncMock(return_value=response))
        self.assertEqual(asyncio.run(api._browser_page(session, url)), "<html>weather</html>")
        call = session.get.await_args
        assert call is not None
        self.assertEqual(call.args, (entry.options["browser_url"] + "/render",))
        self.assertEqual(call.kwargs["params"], {"url": url})
        self.assertEqual(call.kwargs["timeout"].total, 60)
        response.release.assert_called_once_with()
        for failure in (502, api_module.ClientError(url), TimeoutError(url)):
            with self.subTest(failure=type(failure).__name__):
                response.reset_mock()
                session.get.side_effect = failure if isinstance(failure, Exception) else None
                response.status = failure if isinstance(failure, int) else 200
                with self.assertLogs(api_module._LOGGER, level="DEBUG") as captured:
                    self.assertIsNone(asyncio.run(api._browser_page(session, url)))
                self.assertNotIn("private-area", " ".join(captured.output))
                self.assertNotIn(url, " ".join(captured.output))
                if isinstance(failure, int):
                    response.release.assert_called_once_with()

    def test_browser_options_drop_blanks_and_validate_service_origins(self):
        for address, expected in (
            ("", None), (" \t ", None),
            ("http://browser.invalid:8765/", "http://browser.invalid:8765"),
            (" https://browser.invalid/ ", "https://browser.invalid"),
            ("ftp://browser.invalid", False), ("http:///missing", False),
            ("http://user:pw@browser.invalid", False),
            ("https://browser.invalid/render", False),
            ("https://browser.invalid?query=area", False),
            ("https://browser.invalid#fragment", False),
            ("http://browser.invalid:bad", False),
            ("http://browser.invalid:99999", False),
        ):
            with self.subTest(address=address):
                flow = config_flow_module.OptionsFlowHandler(FakeEntry())
                result = asyncio.run(flow.async_step_init({"today": False, "browser_url": address}))
                if expected is False:
                    self.assertEqual(result["type"], "form")
                    self.assertEqual(result["errors"], {"browser_url": "invalid_browser_url"})
                else:
                    self.assertEqual(result["type"], "create_entry")
                    self.assertEqual(result["data"], {"today": False, **({"browser_url": expected} if expected else {})})

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
        self.assertTrue(all(left < right for left, right in pairwise(hourly)))

        rows = [{"datetime": timestamp, "value": index} for index, timestamp in enumerate(daily)]
        self.assertEqual(
            api_module.filter_daily_forecast_rows(rows, False, reference), rows[1:]
        )
        self.assertEqual(
            api_module.filter_daily_forecast_rows(rows, True, reference), rows
        )
        self.assertEqual(rows[0]["value"], 0)


class LocationForecastContractTest(unittest.TestCase):
    """Protect moving-location queries, stable identities and forecast sensors."""

    def _location_api(self, attributes=None):
        hass = FakeHass()
        if attributes is not None:
            hass.states["sensor.synthetic_location"] = types.SimpleNamespace(
                attributes=attributes
            )
        entry = FakeEntry()
        entry.data = {"location_entity": "sensor.synthetic_location", "today": True}
        return api_module.NWeatherAPI(hass, entry, 1)

    def _update_api(self, api, summary=None, on_request=None):
        soup = Mock()
        soup.select.return_value = []
        soup.find.return_value = None
        response = Mock(text=AsyncMock(return_value="<html></html>"))

        async def get(*args, **kwargs):
            if on_request is not None:
                on_request()
            return response

        session = Mock(get=AsyncMock(side_effect=get))

        def select_one(node, selector, *args):
            if selector == "div.weather_info > div > div > div.temperature_info > dl":
                return summary
            return None

        with patch.object(api_module, "async_get_clientsession", return_value=session), patch.object(
            api_module, "BeautifulSoup", return_value=soup
        ), patch.object(api, "_bs4_select_one", side_effect=select_one):
            asyncio.run(api.update())
        return session

    def test_location_parts_normalize_before_building_safe_queries(self):
        cases = [
            (None, None), (False, None), (27, None), ([], None),
            ("", None), (" \t\n ", None), ("N/A", None), (" n/a ", None),
            (" N/a ", None), ("& &", None), ("Seoul &", "Seoul"),
            ("  테스트시\t  가상구  ", "테스트시 가상구"),
            ("테스트·시-1.2\t#가상동?x=2", "테스트·시-1.2 가상동x2"),
            ("N / A", "N A"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(api_module.location_part(value), expected)

    def test_location_area_follows_live_attributes_and_keeps_last_valid_area(self):
        api = self._location_api()
        self.assertIsNone(api.area)
        self.assertEqual(api.entity_key, "location_entry")
        state = types.SimpleNamespace(attributes={
            "Locality": " 테스트시 & ", "Sub Locality": " 가상동# "
        })
        api.hass.states[api.location_entity] = state
        self.assertEqual(api.area, "테스트시 가상동 날씨")
        for locality in (None, "", "n/a", "& &", 1):
            state.attributes = {"Locality": locality, "Sub Locality": "다른동"}
            self.assertEqual(api.area, "테스트시 가상동 날씨")
        for sub_locality in (None, "N/A", 1, " "):
            state.attributes = {"Locality": "다른시", "Sub Locality": sub_locality}
            self.assertEqual(api.area, "다른시 날씨")
        api.hass.states.clear()
        self.assertEqual(api.area, "다른시 날씨")
        self.assertEqual(api.entity_key, "location_entry")
        no_city = self._location_api({"Sub Locality": "가상동"})
        self.assertIsNone(no_city.area)

    def test_location_entity_data_precedes_options_and_fixed_areas_stay_unchanged(self):
        api = self._location_api()
        api.entry.options["location_entity"] = "sensor.other_location"
        self.assertEqual(api.location_entity, "sensor.synthetic_location")
        api.entry.data.pop("location_entity")
        self.assertEqual(api.location_entity, "sensor.other_location")
        for area, options, expected in (
            ("날씨", {}, "날씨"),
            ("테스트시", {}, "테스트시 날씨"),
            ("테스트시", {"area": "다른시"}, "다른시 날씨"),
        ):
            with self.subTest(area=area, options=options):
                fixed = api_module.NWeatherAPI(FakeHass(), FakeEntry(area, options=options), 1)
                self.assertIsNone(fixed.location_entity)
                self.assertEqual(fixed.area, expected)
                self.assertEqual(fixed.entity_key, expected)

    def test_missing_initial_location_fails_before_requesting_any_page(self):
        api = self._location_api({"Locality": "N/A", "Sub Locality": "가상동"})
        with patch.object(api_module, "async_get_clientsession") as get_session:
            with self.assertRaisesRegex(ValueError, "sensor.synthetic_location"):
                asyncio.run(api.update())
            get_session.assert_not_called()
        self.assertEqual(api.result, {})
        self.assertIsNone(api.result_area)

    def test_update_reads_area_once_across_both_requests_and_records_that_area(self):
        api = self._location_api({"Locality": "테스트시", "Sub Locality": "첫동"})
        api.result = {"Humidity": "61"}
        api.result_area = "테스트시 첫동 날씨"

        def move():
            api.hass.states[api.location_entity].attributes = {
                "Locality": "다른시", "Sub Locality": "다음동"
            }

        area_getter = vars(type(api))["area"].fget
        with patch.object(type(api), "area", new_callable=PropertyMock) as area:
            area.side_effect = lambda: area_getter(api)
            session = self._update_api(api, on_request=move)
            self.assertEqual(area.call_count, 1)
        self.assertEqual(
            [call.args[0] for call in session.get.await_args_list],
            [const_module.BSE_URL.format("테스트시 첫동 날씨"),
             const_module.BSE_URL.format("테스트시 첫동 미세먼지")],
        )
        self.assertEqual(api.result_area, "테스트시 첫동 날씨")
        self.assertEqual(api.result["Humidity"], "61")
        self.assertEqual(api.area, "다른시 다음동 날씨")

    def test_missing_humidity_is_retained_only_for_the_same_location(self):
        for previous_area, summary, expected in (
            ("테스트시 가상동 날씨", None, "61"),
            ("다른시 다른동 날씨", None, None),
            (None, None, None),
            ("다른시 다른동 날씨", "습도 62", "62"),
            ("테스트시 가상동 날씨", "습도 101", "61"),
        ):
            with self.subTest(previous_area=previous_area, summary=summary):
                api = self._location_api({"Locality": "테스트시", "Sub Locality": "가상동"})
                api.result = {"Humidity": "61"}
                api.result_area = previous_area
                self._update_api(api, summary)
                self.assertEqual(api.result["Humidity"], expected)
                self.assertEqual(api.result_area, "테스트시 가상동 날씨")
        fixed = api_module.NWeatherAPI(FakeHass(), FakeEntry("테스트시"), 1)
        fixed.result = {"Humidity": "61"}
        fixed.result_area = "다른시 날씨"
        self._update_api(fixed)
        self.assertEqual(fixed.result["Humidity"], "61")

    def test_failed_location_refresh_keeps_the_last_successful_result_area(self):
        api = self._location_api({"Locality": "다른시"})
        previous_result = {"Humidity": "61"}
        api.result, api.result_area = previous_result, "테스트시 날씨"
        session = Mock(get=AsyncMock(side_effect=RuntimeError("synthetic failure")))
        with patch.object(api_module, "async_get_clientsession", return_value=session):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                asyncio.run(api.update())
        self.assertIs(api.result, previous_result)
        self.assertEqual(api.result_area, "테스트시 날씨")

    def test_restored_location_payload_does_not_inherit_humidity_without_a_known_area(self):
        api = self._location_api({"Locality": "테스트시"})
        coordinator = coordinator_module.NWeatherDataUpdateCoordinator(FakeHass(), api, api.entry)
        coordinator._store.data = {
            "saved_at": 1000.0, "result": {"Humidity": "61"},
            "forecast": [], "forecast_hour": [], "weathertype": "맑음",
        }
        with patch.object(coordinator_module, "time", return_value=1100.0):
            self.assertTrue(asyncio.run(coordinator._async_restore_recent()))
        self.assertEqual(api.result["Humidity"], "61")
        self.assertIsNone(api.result_area)
        self._update_api(api)
        self.assertIsNone(api.result["Humidity"])

    def test_location_ids_device_metadata_and_callbacks_do_not_follow_the_phone(self):
        api = self._location_api()
        coordinator = types.SimpleNamespace(last_update_success=True)
        sensor = sensor_module.NWeatherSensor(const_module.NOW_TEMP, api, coordinator)
        weather = weather_module.NWeatherMain(
            ["Naver Weather Custom", "네이버날씨Custom", "", ""], api, coordinator
        )
        self.assertEqual(sensor.unique_id, "location_entry:NowTemp")
        self.assertEqual(weather.unique_id, "location_entry:Naver Weather Custom")
        callback = Mock()
        api.register_update_state(sensor.unique_id, callback)
        for locality in ("테스트시", "다른시"):
            api.hass.states[api.location_entity] = types.SimpleNamespace(attributes={
                "Locality": locality, "Sub Locality": "가상동"
            })
            api.device_update("NowTemp")
            self.assertEqual(sensor.unique_id, "location_entry:NowTemp")
            self.assertEqual(sensor.device_info["identifiers"], {(const_module.DOMAIN, "location_entry")})
            self.assertEqual(sensor.device_info["name"], "Naver Weather Custom 현재 위치")
            self.assertNotIn("configuration_url", sensor.device_info)
        self.assertEqual(callback.call_count, 2)
        with patch.object(api, "set_data", side_effect=api.entry.data.__setitem__):
            self.assertEqual(weather.name, "Naver Weather Custom 1")
            self.assertEqual(weather.name, "현재 위치")

    def test_both_forecast_sensors_are_added_without_extending_weather_info(self):
        api = api_module.NWeatherAPI(FakeHass(), FakeEntry(), 3)
        coordinator = types.SimpleNamespace(last_update_success=True)
        hass = types.SimpleNamespace(data={const_module.DOMAIN: {
            "api": {api.entry.entry_id: api},
            "coordinators": {api.entry.entry_id: coordinator},
        }})
        add_entities = Mock()
        asyncio.run(sensor_module.async_setup_entry(hass, api.entry, add_entities))
        entities = add_entities.call_args.args[0]
        self.assertEqual(len(const_module.WEATHER_INFO), 31)
        self.assertEqual(len(entities), 33)
        self.assertEqual([entity.device[0] for entity in entities[:31]], list(const_module.WEATHER_INFO))
        for entity, key, name, icon in (
            (entities[-2], "ForecastHourly", "시간별 예보", "mdi:clock-outline"),
            (entities[-1], "ForecastDaily", "일별 예보", "mdi:calendar"),
        ):
            with self.subTest(key=key):
                self.assertIsInstance(entity, sensor_module.NWeatherSensor)
                self.assertIsInstance(entity, sensor_module.NWeatherForecastSensor)
                self.assertEqual(entity.unique_id, f"날씨:{key}")
                with patch.object(api, "set_data", side_effect=api.entry.data.__setitem__):
                    self.assertEqual(entity.name, f"naver_weather_custom {key} 3")
                    self.assertEqual(entity.name, name)
                self.assertEqual(entity.icon, icon)
                self.assertIsNone(entity.device_class)
                self.assertIsNone(entity.unit_of_measurement)
                self.assertEqual(entity._unrecorded_attributes, frozenset({"forecast"}))
                self.assertEqual(entity.extra_state_attributes, {"forecast": []})
                self.assertIsNone(entity.state)

    def test_forecast_sensors_use_the_registered_weather_converter_and_first_condition(self):
        api = self._location_api({"Locality": "테스트시"})
        api.forecast_hour = [{"datetime": "2030-01-01T00:00:00+00:00", "native_temperature": 20}]
        api.forecast = [{
            "datetime": "2030-01-01T00:00:00+00:00", "temperature": 22,
            "templow": 12, "condition_am": "sunny", "condition_pm": "rainy",
            "rain_rate_am": 20, "rain_rate_pm": 40,
            "weathertype_am": "wt1", "weathertype_pm": "wt9",
        }]
        coordinator = types.SimpleNamespace(last_update_success=True)
        weather = weather_module.NWeatherMain(
            ["Naver Weather Custom", "네이버날씨Custom", "", ""], api, coordinator
        )
        api.weather_entity = weather
        for key, native in (
            ("ForecastHourly", weather_module.build_hourly_forecast(api)),
            ("ForecastDaily", weather_module.build_daily_forecast(api, False)),
        ):
            entity = sensor_module.NWeatherForecastSensor([key, "예보"], api, coordinator)
            for converted in ([], [{}], [{"condition": None}], [{"condition": "rainy", "temperature": 71.6}]):
                with self.subTest(key=key, converted=converted), patch.object(
                    weather, "_convert_forecast", return_value=converted, create=True
                ) as convert:
                    self.assertIs(entity.extra_state_attributes["forecast"], converted)
                    convert.assert_called_once_with(native)
                    self.assertEqual(entity.state, converted[0].get("condition") if converted else None)
        twice_daily = weather_module.build_daily_forecast(api, True)
        self.assertEqual([row["condition"] for row in twice_daily], ["sunny", "rainy"])
        self.assertEqual([row["is_daytime"] for row in twice_daily], [True, False])
        self.assertEqual(weather._forecast(2), twice_daily)
        self.assertEqual(weather._condition_daily("sunny", "rainy"), "rainy")

    def test_weather_registration_updates_listeners_and_clears_only_its_own_converter(self):
        api = self._location_api()
        coordinator = types.SimpleNamespace(async_update_listeners=Mock())
        weather = weather_module.NWeatherMain(["Weather", "날씨"], api, coordinator)
        other = weather_module.NWeatherMain(["OtherWeather", "다른 날씨"], api, coordinator)
        asyncio.run(weather.async_added_to_hass())
        self.assertIs(api.weather_entity, weather)
        coordinator.async_update_listeners.assert_called_once_with()
        asyncio.run(other.async_added_to_hass())
        self.assertIs(api.weather_entity, other)
        asyncio.run(weather.async_will_remove_from_hass())
        self.assertIs(api.weather_entity, other)
        self.assertEqual(coordinator.async_update_listeners.call_count, 2)
        asyncio.run(other.async_will_remove_from_hass())
        self.assertIsNone(api.weather_entity)
        self.assertEqual(coordinator.async_update_listeners.call_count, 3)

    def test_location_user_flow_ignores_area_and_rejects_invalid_locality(self):
        hass = FakeHass()
        hass.states["sensor.synthetic_location"] = types.SimpleNamespace(attributes={"Locality": "테스트시 &"})
        flow = config_flow_module.ConfigFlow()
        with patch.object(flow, "hass", hass, create=True):
            result = asyncio.run(flow.async_step_user({
                "location_entity": "sensor.synthetic_location", "area": "ignored", "today": True,
            }))
        self.assertEqual(result, {
            "type": "create_entry", "title": "현재 위치",
            "data": {"location_entity": "sensor.synthetic_location", "today": True},
        })
        self.assertEqual(flow.unique_id, "location:sensor.synthetic_location")
        for attributes in (None, {}, {"Locality": "N/A"}, {"Locality": "& &"}, {"Locality": 1}):
            with self.subTest(attributes=attributes):
                hass.states.clear()
                if attributes is not None:
                    hass.states["sensor.synthetic_location"] = types.SimpleNamespace(attributes=attributes)
                with patch.object(flow, "hass", hass, create=True):
                    result = asyncio.run(flow.async_step_user({"location_entity": "sensor.synthetic_location"}))
                self.assertEqual(result["type"], "form")
                self.assertEqual(result["errors"], {"location_entity": "invalid_location_entity"})
                self.assertEqual(result["data_schema"]["location_entity"], {"domain": "sensor"})

    def test_area_duplicate_detection_skips_data_and_options_location_entries(self):
        for storage in ("data", "options"):
            entry = FakeEntry("날씨")
            getattr(entry, storage)["location_entity"] = "sensor.synthetic_location"
            flow = config_flow_module.ConfigFlow()
            with self.subTest(storage=storage), patch.object(flow, "_async_current_entries", return_value=[entry], create=True):
                self.assertFalse(flow._area_is_configured("날씨"))
                result = asyncio.run(flow.async_step_user({"area": " "}))
                self.assertEqual(result["type"], "create_entry")

    def test_location_config_translations_include_korean_field_and_error(self):
        for name in ("strings.json", "translations/en.json", "translations/ko.json"):
            with self.subTest(name=name):
                config = json.loads((INTEGRATION / name).read_text(encoding="utf-8"))["config"]
                label = config["step"]["user"]["data"]["location_entity"]
                error = config["error"]["invalid_location_entity"]
                self.assertTrue(label)
                self.assertIn("Locality", error)
                if name == "translations/ko.json":
                    self.assertIn("위치 센서", label)
                    self.assertIn("지역", label)
                    self.assertIn("무시", label)
                    self.assertTrue(any("가" <= char <= "힣" for char in error))


if __name__ == "__main__":
    unittest.main()
