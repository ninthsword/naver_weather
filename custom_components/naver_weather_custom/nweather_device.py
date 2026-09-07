"""Device class."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.helpers.device_registry import DeviceInfo

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BSE_URL, DEVICE_REG, DEVICE_UNREG, DOMAIN
from .coordinator import NWeatherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class NWeatherBase:
    """Base class."""

    def __init__(self, device, api):
        """Init device class."""
        self.device = device
        self.api = api
        self.area = api.area
        self._attr_unique_id = f"{self.area}:{self.device[0]}"
        # CoordinatorEntity's Entity MRO supplies the public ``device_info``
        # property.  Set its native attribute explicitly so the coordinator
        # base cannot hide this integration's device metadata.
        self._attr_device_info: DeviceInfo | None = {
            "identifiers": {(DOMAIN, self.area)},
            "manufacturer": self.api.brand_name,
            "model": f"{self.api.model}_{self.api.version}",
            "name": f"{self.api.brand_name} {self.area}",
            "sw_version": self.api.version,
            "configuration_url": BSE_URL.format(self.area),
        }
        self.api.init_device(self.unique_id)
        self.register = self.api.get_device(self.unique_id, DEVICE_REG)
        self.unregister = self.api.get_device(self.unique_id, DEVICE_UNREG)

    @property
    def unique_id(self) -> str:
        """Get unique ID."""
        return self.area + ":" + self.device[0]

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device registry information for this entity."""
        return self._attr_device_info


# Preserve the supported HA MRO mixing cached descriptors and dynamic properties.
class NWeatherDevice(CoordinatorEntity[NWeatherDataUpdateCoordinator], NWeatherBase):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Defines a Pad Device entity."""

    TYPE = ""

    def __init__(self, device, api, coordinator):
        """Initialize the instance."""
        CoordinatorEntity.__init__(self, coordinator)
        NWeatherBase.__init__(self, device, api)

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def entity_registry_enabled_default(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """entity_registry_enabled_default."""
        return True

    async def async_added_to_hass(self):
        """Subscribe this entity to the shared coordinator."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe this entity from the shared coordinator."""
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Expose coordinator refresh failures instead of stale data."""
        return self.coordinator.last_update_success

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def should_poll(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """No polling needed for this device."""
        return False

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def extra_state_attributes(self) -> dict[str, object]:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the state attributes of the sensor."""
        attr = {}
        return attr
