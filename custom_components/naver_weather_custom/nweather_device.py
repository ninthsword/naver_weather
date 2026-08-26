"""Device class."""

import logging

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_REG, DEVICE_UNREG, DOMAIN, BSE_URL

_LOGGER = logging.getLogger(__name__)


class NWeatherBase:
    """Base class."""

    def __init__(self, device, api):
        """Init device class."""
        self.device = device
        self.api = api
        self.area = api.area
        self._attr_unique_id = f"{self.area}:{self.device[0]}"
        self.api.init_device(self.unique_id)
        self.register = self.api.get_device(self.unique_id, DEVICE_REG)
        self.unregister = self.api.get_device(self.unique_id, DEVICE_UNREG)

    @property
    def unique_id(self) -> str:
        """Get unique ID."""
        return self.area + ":" + self.device[0]

    @property
    def device_info(self):
        """Return device registry information for this entity."""
        return {
            "connections": {(self.area, self.unique_id)},
            "identifiers": {
                (
                    DOMAIN,
                    self.area,
                )
            },
            "manufacturer": f"{self.api.brand_name}",
            "model": f"{self.api.model}_{self.api.version}",
            "name": f"{self.api.brand_name} {self.area}",
            "sw_version": self.api.version,
            "configuration_url": BSE_URL.format(self.area),
        }


class NWeatherDevice(CoordinatorEntity, NWeatherBase):
    """Defines a Pad Device entity."""

    TYPE = ""

    def __init__(self, device, api, coordinator):
        """Initialize the instance."""
        CoordinatorEntity.__init__(self, coordinator)
        NWeatherBase.__init__(self, device, api)

    @property
    def entity_registry_enabled_default(self):
        """entity_registry_enabled_default."""
        return True

    async def async_added_to_hass(self):
        """Subscribe this entity to the shared coordinator."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe this entity from the shared coordinator."""
        await super().async_will_remove_from_hass()

    @property
    def available(self):
        """Expose coordinator refresh failures instead of stale data."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No polling needed for this device."""
        return False

    @property
    def extra_state_attributes (self):
        """Return the state attributes of the sensor."""
        attr = {}
        return attr
