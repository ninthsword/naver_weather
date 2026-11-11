"""Shared update coordinator for the Naver Weather integration."""

from datetime import datetime, timedelta
from time import monotonic, time
from typing import cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_nweather import NWeatherAPI
from .const import BRAND, DOMAIN

UPDATE_INTERVAL = timedelta(minutes=10)
# How long entities keep the last good payload while refreshes fail.
STALE_DATA_LIMIT = timedelta(hours=1)
STORAGE_VERSION = 1
_DATETIME_KEY = "__datetime__"


def _encode(value: object) -> object:
    """Make a payload JSON-safe, keeping datetimes recoverable."""
    if isinstance(value, datetime):
        return {_DATETIME_KEY: value.isoformat()}
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    return value


def _decode(value: object) -> object:
    """Invert _encode; raise ValueError or TypeError on a malformed payload."""
    if isinstance(value, dict):
        if set(value) == {_DATETIME_KEY}:
            return datetime.fromisoformat(value[_DATETIME_KEY])
        return {key: _decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode(item) for item in value]
    return value


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
        self._store: Store[dict[str, object]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )

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
        payload = cast(dict[str, object], _encode({
            "saved_at": time(),
            "result": self.api.result,
            "forecast": self.api.forecast,
            "forecast_hour": self.api.forecast_hour,
            "weathertype": self.api.weathertype,
        }))
        self._store.async_delay_save(lambda: payload, 1)
        return self.api.result

    async def async_config_entry_first_refresh(self) -> None:
        """Start from the stored payload when the first refresh fails within the limit."""
        try:
            await super().async_config_entry_first_refresh()
        except ConfigEntryNotReady:
            if not await self._async_restore_recent():
                raise

    async def _async_restore_recent(self) -> bool:
        """Load the last good payload saved before a restart if it is recent enough."""
        try:
            stored = _decode(await self._store.async_load())
            if not isinstance(stored, dict):
                return False
            age = time() - float(stored["saved_at"])
            result, forecast = stored["result"], stored["forecast"]
            forecast_hour, weathertype = stored["forecast_hour"], stored["weathertype"]
        except (KeyError, TypeError, ValueError):
            return False
        if not (
            0 <= age < STALE_DATA_LIMIT.total_seconds()
            and isinstance(result, dict)
            and isinstance(forecast, list)
            and isinstance(forecast_hour, list)
            and (weathertype is None or isinstance(weathertype, str))
        ):
            return False
        self.api.result, self.api.forecast = result, forecast
        self.api.forecast_hour, self.api.weathertype = forecast_hour, weathertype
        self.last_good_refresh = monotonic() - age
        self.data = result
        return True

    @property
    def has_recent_data(self) -> bool:
        """Return whether the last good payload is within the stale-data limit."""
        if self.last_good_refresh is None:
            return False
        age = monotonic() - self.last_good_refresh
        return age < STALE_DATA_LIMIT.total_seconds()
