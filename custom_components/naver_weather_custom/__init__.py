"""Naver Weather Sensor for Homeassistant."""
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.components.http.server import StaticPathConfig
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import websocket_command
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .api_nweather import NWeatherAPI as API
from .const import DOMAIN, PLATFORMS, SW_VERSION, WEATHER_INFO
from .coordinator import NWeatherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
_CARD_PATH = f"/{DOMAIN}/frontend"


@websocket_command(
    {vol.Required("type"): f"{DOMAIN}/card_entities", vol.Required("entity_id"): str}
)
@callback
def _card_entities(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict
) -> None:
    """Return the readable companion entities of a loaded weather entity."""
    entity_id = msg["entity_id"]
    can_read = connection.user.permissions.check_entity
    registry = er.async_get(hass)
    weather = registry.async_get(entity_id)
    entry = (
        hass.config_entries.async_get_entry(weather.config_entry_id)
        if weather and weather.config_entry_id
        else None
    )
    if (
        not entity_id.startswith("weather.")
        or not weather
        or weather.platform != DOMAIN
        or entry is None
        or entry.state is not ConfigEntryState.LOADED
        or not can_read(entity_id, POLICY_READ)
    ):
        connection.send_error(msg["id"], "not_found", "날씨 엔티티를 찾을 수 없습니다")
        return

    prefix = weather.unique_id.rpartition(":")[0]
    entities = {}
    for key in (*WEATHER_INFO, "ForecastHourly", "ForecastDaily"):
        sensor_id = registry.async_get_entity_id("sensor", DOMAIN, f"{prefix}:{key}")
        if (
            sensor_id
            and (sensor := registry.async_get(sensor_id))
            and sensor.config_entry_id == entry.entry_id
            and can_read(sensor_id, POLICY_READ)
        ):
            entities[key] = sensor_id
    connection.send_result(msg["id"], {"entities": entities})


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up naver_weather from configuration.yaml."""
    websocket_api.async_register_command(hass, _card_entities)
    if "frontend" in hass.config.components and hass.http is not None:
        try:
            from homeassistant.components import frontend

            await hass.http.async_register_static_paths(
                [StaticPathConfig(_CARD_PATH, str(Path(__file__).parent / "frontend"), cache_headers=False)]
            )
            frontend.add_extra_js_url(hass, f"{_CARD_PATH}/naver-weather-card.js?v={SW_VERSION}")
        except Exception:
            _LOGGER.warning("네이버 날씨 카드의 프런트엔드 등록에 실패했습니다")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up naver_weather from a config entry."""
    hass.data.setdefault(DOMAIN, {"api": {}, "coordinators": {}})
    api = API(hass, entry, len(hass.data[DOMAIN]["api"]) + 1)
    hass.data[DOMAIN]["api"][entry.entry_id] = api
    coordinator = NWeatherDataUpdateCoordinator(hass, api, entry)
    hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry and clean up only after platforms unload."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    domain_data = hass.data.get(DOMAIN)
    if isinstance(domain_data, dict):
        for collection_name in ("api", "coordinators"):
            collection = domain_data.get(collection_name)
            if isinstance(collection, dict):
                collection.pop(entry.entry_id, None)
    return True
