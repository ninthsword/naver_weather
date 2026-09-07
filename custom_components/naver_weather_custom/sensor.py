"""Support for Naver Weather Sensors."""
import logging

from .const import DOMAIN, WEATHER_INFO
from .nweather_device import NWeatherDevice

_LOGGER = logging.getLogger(__name__)


def isInt(v):
    """Check number is integer."""
    try:
        int(v)
        return True
    except ValueError:
        return False


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up sensor for Naver Weather sensors."""

    api = hass.data[DOMAIN]["api"][config_entry.entry_id]
    coordinator = hass.data[DOMAIN]["coordinators"][config_entry.entry_id]

    def async_add_entity():
        """Add sensor from sensor."""
        entities = []
        for device in WEATHER_INFO.values():
            entities.append(NWeatherSensor(device, api, coordinator))

        if entities:
            async_add_entities(entities)

    async_add_entity()


class NWeatherSensor(NWeatherDevice):
    """Defines a NaverWeather Device entity."""

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def state(self) -> str | int | float:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state of the sensor."""
        value = self.api.result.get(self.device[0]) or ""
        if value.isdigit():
            if isInt(value):
                return int(value)
            else:
                return float(value)
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
