"""Support for Naver Weather Sensors."""
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    Forecast,
    WeatherEntity,
)
from homeassistant.components.weather.const import WeatherEntityFeature
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import callback

from .api_nweather import KST, filter_daily_forecast_rows
from .const import (
    ATTR_RETAINED_WEATHER_UPDATED_AT,
    CONDITION,
    DOMAIN,
    LOCATION,
    NOW_HUMI,
    NOW_TEMP,
    WIND_DIR,
    WIND_SPEED,
)
from .nweather_device import NWeatherDevice

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=10)


def _forecast_datetime(value) -> str | None:
    """Return a forecast timestamp as a UTC RFC3339 string for Home Assistant."""
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=KST)
    return timestamp.astimezone(timezone.utc).isoformat()


def build_daily_forecast(api, twice_daily: bool) -> list[Forecast]:
    forecast = []

    daily_rows = filter_daily_forecast_rows(
        api.forecast, bool(api.today), datetime.now(KST)
    )
    for data in daily_rows:
        #주간
        next_day = {
            ATTR_FORECAST_TIME: _forecast_datetime(data.get("datetime")),
            ATTR_FORECAST_CONDITION: condition_daily(data["condition_am"], data["condition_pm"]),
            ATTR_FORECAST_NATIVE_TEMP_LOW: data["templow"],
            ATTR_FORECAST_NATIVE_TEMP: data["temperature"],
            ATTR_FORECAST_PRECIPITATION_PROBABILITY: data["rain_rate_am"],
            #ATTR_FORECAST_WIND_BEARING: data[""],
            #ATTR_FORECAST_WIND_SPEED: data[""],

            # Not officially supported, but nice additions.
            "condition_am": data["condition_am"],
            "condition_pm": data["condition_pm"],
            "weathertype_am": data["weathertype_am"],
            "weathertype_pm": data["weathertype_pm"],

            "rain_rate_am": data["rain_rate_am"],
            "rain_rate_pm": data["rain_rate_pm"]
        }

        if twice_daily:
            next_day[ATTR_FORECAST_CONDITION] = data["condition_am"]
            next_day["is_daytime"] = True

        forecast.append(next_day)

        # FORECAST_TWICE_DAILY 일때만
        if twice_daily:
            #야간
            next_day = {
                ATTR_FORECAST_TIME: _forecast_datetime(data.get("datetime")),
                ATTR_FORECAST_CONDITION: data["condition_pm"],
                ATTR_FORECAST_NATIVE_TEMP_LOW: data["templow"],
                ATTR_FORECAST_NATIVE_TEMP: data["temperature"],
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: data["rain_rate_pm"],
                #ATTR_FORECAST_WIND_BEARING: data[""],
                #ATTR_FORECAST_WIND_SPEED: data[""],
                "is_daytime" : False,

                # Not officially supported, but nice additions.
                "condition_am": data["condition_am"],
                "condition_pm": data["condition_pm"],
                "weathertype_am": data["weathertype_am"],
                "weathertype_pm": data["weathertype_pm"],

                "rain_rate_am": data["rain_rate_am"],
                "rain_rate_pm": data["rain_rate_pm"]
            }
            forecast.append(next_day)

    return forecast


def build_hourly_forecast(api) -> list[Forecast]:
    forecast = []

    for data in api.forecast_hour:
        # Hourly parser data stays in native units until this HA boundary.
        native_wind_speed = data.get("native_wind_speed")
        if native_wind_speed is None:
            native_wind_speed = data.get("wind_speed")
        next_day = {
            ATTR_FORECAST_TIME: _forecast_datetime(data.get("datetime")),
            ATTR_FORECAST_CONDITION: data.get("condition"),
            ATTR_FORECAST_NATIVE_TEMP: data.get("native_temperature"),
            ATTR_FORECAST_PRECIPITATION_PROBABILITY: data.get("precipitation_probability"),
            ATTR_FORECAST_WIND_BEARING: data.get("wind_bearing"),
            ATTR_FORECAST_NATIVE_WIND_SPEED: native_wind_speed,
            ATTR_FORECAST_NATIVE_PRECIPITATION: data.get("native_precipitation"),

            # Not officially supported, but nice additions.
            "weathertype_hour": data.get("weathertype_hour"),
            #"condition_pm": data["condition_pm"],
            "humidity": data.get("humidity"),
        }

        forecast.append(next_day)

    return forecast


def condition_daily(am, pm):

    list = ["snowy", "pouring", "rainy", "cloudy", "windy"]

    for feature in list:
        if ( feature in am or feature in pm ):
            if feature in am:
                return am
            else:
                return pm

    return am


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a entity from a config_entry."""

    api = hass.data[DOMAIN]["api"][config_entry.entry_id]
    coordinator = hass.data[DOMAIN]["coordinators"][config_entry.entry_id]

    def async_add_entity():
        """Add sensor from sensor."""
        entities = []
        device = ["Naver Weather Custom", "네이버날씨Custom", "", ""]
        entities.append(NWeatherMain(device, api, coordinator))

        if entities:
            async_add_entities(entities)

    async_add_entity()


# Preserve the supported HA MRO mixing cached descriptors and dynamic properties.
class NWeatherMain(NWeatherDevice, WeatherEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a weather condition."""
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = ( WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY | WeatherEntityFeature.FORECAST_HOURLY )
    
    async def async_added_to_hass(self):
        """Expose HA's forecast conversion to this entry's forecast sensors."""
        await super().async_added_to_hass()
        self.api.weather_entity = self
        self.coordinator.async_update_listeners()

    async def async_will_remove_from_hass(self) -> None:
        """Clear the converter and update sensors when this weather entity leaves."""
        await super().async_will_remove_from_hass()
        if self.api.weather_entity is self:
            self.api.weather_entity = None
            self.coordinator.async_update_listeners()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write the weather state and send refreshed forecasts to subscribers."""
        super()._handle_coordinator_update()
        self.hass.async_create_task(self.async_update_listeners(None))

    # HA declares a cached descriptor; this status follows every coordinator update.
    @property
    def extra_state_attributes(self) -> dict[str, object]:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Expose the real refresh time only while showing retained weather."""
        updated_at = self.coordinator.retained_weather_updated_at
        return {ATTR_RETAINED_WEATHER_UPDATED_AT: updated_at.isoformat()} if updated_at else {}

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def name(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the name of the device."""
        if not self.api.get_data(self.unique_id):
            self.api.set_data(self.unique_id, True)
            return self.device[0] + " " + str(self.api.count)
        elif self.api.location_entity is not None:
            return "현재 위치"
        elif self.area != "날씨":
            return self.area.split(" 날씨")[0]
        else:
            return self.device[1]

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def native_temperature(self) -> float | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the temperature."""
        try:
            return float(self.api.result.get(NOW_TEMP[0]))
        except (AttributeError, KeyError, TypeError, ValueError):
            return

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def humidity(self) -> int | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the humidity."""
        try:
            return int(self.api.result.get(NOW_HUMI[0]))
        except (AttributeError, KeyError, TypeError, ValueError):
            return

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def native_wind_speed(self) -> float | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the wind speed."""
        try:
            return float(self.api.result.get(WIND_SPEED[0]))
        except (AttributeError, KeyError, TypeError, ValueError):
            return

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def wind_bearing(self) -> float | str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the wind bearing."""
        return self.api.result.get(WIND_DIR[0])

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def condition(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the weather condition."""
        return self.api.result.get(CONDITION[0])

    # HA declares a cached descriptor; retain this integration's property semantics.
    @property
    def attribution(self) -> str:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the attribution."""
        #return f"{self.api.result.get(LOCATION[0])} - Weather forecast from Naver, Powered by miumida, Custom by ninthsword"
        return f"{self.api.weathertype}, {self.api.result.get(LOCATION[0])} - Weather forecast from Naver, Powered by miumida, Custom by ninthsword"

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units.
        
        Only implement this method if `WeatherEntityFeature.FORECAST_DAILY` is set
        """
        return self._forecast(WeatherEntityFeature.FORECAST_DAILY)

    async def async_forecast_twice_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units.
        
        Only implement this method if `WeatherEntityFeature.FORECAST_DAILY` is set
        """
        return self._forecast(WeatherEntityFeature.FORECAST_TWICE_DAILY)

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast in native units.
        
        Only implement this method if `WeatherEntityFeature.FORECAST_HOURLY` is set
        """
        return self._forecast_hour(WeatherEntityFeature.FORECAST_HOURLY)
        
    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the forecast."""
        return self._forecast(WeatherEntityFeature.FORECAST_DAILY)

    def _forecast(self, feature) -> list[Forecast] | None:
        return build_daily_forecast(self.api, feature == WeatherEntityFeature.FORECAST_TWICE_DAILY)

    def _forecast_hour(self, feature) -> list[Forecast] | None:
        return build_hourly_forecast(self.api)

    def _condition_daily(self, am, pm):
        return condition_daily(am, pm)
