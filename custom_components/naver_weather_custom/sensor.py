"""Support for Naver Weather Sensors."""
import logging
from typing import cast

from homeassistant.components.weather import Forecast

from .const import DOMAIN, WEATHER_INFO
from .nweather_device import NWeatherDevice
from .weather import build_daily_forecast, build_hourly_forecast

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor for Naver Weather sensors."""

    api = hass.data[DOMAIN]["api"][config_entry.entry_id]
    coordinator = hass.data[DOMAIN]["coordinators"][config_entry.entry_id]

    def async_add_entity():
        """Add sensor from sensor."""
        entities = []
        for device in WEATHER_INFO.values():
            entities.append(NWeatherSensor(device, api, coordinator))
        for device in (["ForecastHourly", "시간별 예보"], ["ForecastDaily", "일별 예보"]):
            entities.append(NWeatherForecastSensor(device, api, coordinator))

        if entities:
            async_add_entities(entities)

    async_add_entity()


class NWeatherSensor(NWeatherDevice):
    """Defines a NaverWeather Device entity."""

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def state(self) -> str | int | float | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state of the sensor."""
        value = self.api.result.get(self.device[0])
        if isinstance(value, str) and value.isdecimal():
            return int(value)
        return value

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def name(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the name of the device."""
        if not self.api.get_data(self.unique_id):
            self.api.set_data(self.unique_id, True)
            return DOMAIN + " " + self.device[0] + " " + str(self.api.count)
        else:
            return self.device[1]

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def icon(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the icon of the sensor."""
        dicon = WEATHER_INFO[self.device[0]][3]
        if dicon != "":
            return dicon

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def device_class(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the class of the sensor."""
        dclass = WEATHER_INFO[self.device[0]][4]
        if dclass != "":
            return dclass

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def unit_of_measurement(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the unit of measurement of this sensor."""
        unit = WEATHER_INFO[self.device[0]][2]
        if unit != "":
            return unit


class NWeatherForecastSensor(NWeatherSensor):
    """Expose the weather service's converted forecasts without recording them."""

    _unrecorded_attributes = frozenset({"forecast"})

    @property
    def state(self) -> str | None:
        """Return the first forecast condition, if present."""
        forecast = cast(list[Forecast], self.extra_state_attributes["forecast"])
        return forecast[0].get("condition") if forecast else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return forecasts converted with the weather entity's units and precision."""
        weather_entity = self.api.weather_entity
        if weather_entity is None:
            return {"forecast": []}
        forecast = (
            build_hourly_forecast(self.api) if self.device[0] == "ForecastHourly"
            else build_daily_forecast(self.api, False)
        )
        return {"forecast": weather_entity._convert_forecast(forecast)}

    @property
    def icon(self) -> str:
        """Return the forecast period's icon."""
        return "mdi:clock-outline" if self.device[0] == "ForecastHourly" else "mdi:calendar"

    @property
    def device_class(self) -> None:
        """Forecast conditions have no sensor device class."""
        return None

    @property
    def unit_of_measurement(self) -> None:
        """Forecast conditions have no measurement unit."""
        return None
