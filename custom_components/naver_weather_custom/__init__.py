"""Naver Weather Sensor for Homeassistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api_nweather import NWeatherAPI as API
from .const import DOMAIN, PLATFORMS
from .coordinator import NWeatherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up naver_weather from configuration.yaml."""
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
