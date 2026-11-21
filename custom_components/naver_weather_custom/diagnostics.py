"""Privacy-safe diagnostics for a Naver Weather config entry."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LocationMethod
from .coordinator import NWeatherDataUpdateCoordinator

_LOCATION_LABELS = {
    LocationMethod.FIXED_AREA: "고정 지역",
    LocationMethod.COORDINATE_BOUNDARY: "좌표 기반 행정구역",
    LocationMethod.SENSOR_ADDRESS: "센서의 현재 주소",
    LocationMethod.REMEMBERED_ADDRESS: "센서의 마지막 주소",
    None: "알 수 없음",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, str]:
    """Report only the strategy of the last committed payload."""
    coordinator: NWeatherDataUpdateCoordinator | None = (
        hass.data.get(DOMAIN, {}).get("coordinators", {}).get(entry.entry_id)
    )
    method = coordinator.last_location_method if coordinator is not None else None
    return {"location_method": _LOCATION_LABELS[method]}
