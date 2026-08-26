"""Shared update coordinator for the Naver Weather integration."""

from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_nweather import NWeatherAPI
from .const import BRAND


UPDATE_INTERVAL = timedelta(minutes=10)


class NWeatherDataUpdateCoordinator(DataUpdateCoordinator):
    """Fetch one Naver Weather payload for all entities in a config entry."""

    def __init__(self, hass, api: NWeatherAPI, entry) -> None:
        """Initialize the shared refresh coordinator."""
        super().__init__(
            hass,
            logger=api.logger,
            name=BRAND,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.api = api

    async def _async_update_data(self):
        """Refresh the API payload and expose it to all subscribed entities."""
        await self.api.update()
        return self.api.result
