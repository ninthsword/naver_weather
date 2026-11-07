"""Shared update coordinator for the Naver Weather integration."""

from datetime import timedelta
from time import monotonic

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_nweather import NWeatherAPI
from .const import BRAND

UPDATE_INTERVAL = timedelta(minutes=10)
# How long entities keep the last good payload while refreshes fail.
STALE_DATA_LIMIT = timedelta(hours=1)


class NWeatherDataUpdateCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Fetch one Naver Weather payload for all entities in a config entry."""

    def __init__(self, hass: HomeAssistant, api: NWeatherAPI, entry: ConfigEntry) -> None:
        """Initialize the shared refresh coordinator."""
        super().__init__(
            hass,
            logger=api.logger,
            name=BRAND,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.api = api
        self.last_good_refresh: float | None = None

    async def _async_update_data(self) -> dict[str, object]:
        """Refresh the API payload and expose it to all subscribed entities."""
        try:
            await self.api.update()
        except Exception:
            # HA notifies entities only on the first of consecutive failures;
            # tell them once the last good payload has expired.
            if not self.has_recent_data:
                self.async_update_listeners()
            raise
        self.last_good_refresh = monotonic()
        return self.api.result

    @property
    def has_recent_data(self) -> bool:
        """Return whether the last good payload is within the stale-data limit."""
        if self.last_good_refresh is None:
            return False
        age = monotonic() - self.last_good_refresh
        return age < STALE_DATA_LIMIT.total_seconds()
