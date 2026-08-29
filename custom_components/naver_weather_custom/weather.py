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
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
)

from .api_nweather import KST, filter_daily_forecast_rows
from .const import (
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


class NWeatherMain(NWeatherDevice, WeatherEntity):
    """Representation of a weather condition."""
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_supported_features = ( WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY | WeatherEntityFeature.FORECAST_HOURLY )
    
    @property
    def name(self) -> str:
        """Return the name of the device."""
        if not self.api.get_data(self.unique_id):
            self.api.set_data(self.unique_id, True)
            return self.device[0] + " " + str(self.api.count)
        elif self.area != "날씨":
            return self.area.split(" 날씨")[0]
        else:
            return self.device[1]

    @property
    def native_temperature(self):
        """Return the temperature."""
        try:
            return float(self.api.result.get(NOW_TEMP[0]))
        except (AttributeError, KeyError, TypeError, ValueError):
            return

    @property
    def humidity(self):
        """Return the humidity."""
        try:
            return int(self.api.result.get(NOW_HUMI[0]))
        except (AttributeError, KeyError, TypeError, ValueError):
            return

    @property
    def native_wind_speed(self):
        """Return the wind speed."""
        try:
            return float(self.api.result.get(WIND_SPEED[0]))
        except (AttributeError, KeyError, TypeError, ValueError):
            return

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        return self.api.result.get(WIND_DIR[0])

    @property
    def condition(self):
        """Return the weather condition."""
        return self.api.result.get(CONDITION[0])

    @property
    def state(self):
        """Return the weather state."""
        return self.api.result.get(CONDITION[0])

    @property
    def attribution(self):
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
        forecast = []

        daily_rows = filter_daily_forecast_rows(
            self.api.forecast, bool(self.api.today), datetime.now(KST)
        )
        for data in daily_rows:
            #주간
            next_day = {
                ATTR_FORECAST_TIME: _forecast_datetime(data.get("datetime")),
                ATTR_FORECAST_CONDITION: self._condition_daily(data["condition_am"], data["condition_pm"]),
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

            if feature == WeatherEntityFeature.FORECAST_TWICE_DAILY:
                next_day[ATTR_FORECAST_CONDITION] = data["condition_am"]
                next_day["is_daytime"] = True

            forecast.append(next_day)

            # FORECAST_TWICE_DAILY 일때만
            if feature == WeatherEntityFeature.FORECAST_TWICE_DAILY:
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


    def _forecast_hour(self, feature) -> list[Forecast] | None:
        forecast = []

        for data in self.api.forecast_hour:
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

    def _condition_daily(self, am, pm):

        list = ["snowy", "pouring", "rainy", "cloudy", "windy"]
        
        for feature in list:
            if ( feature in am or feature in pm ):
                if feature in am:
                    return am
                else:
                    return pm

        return am
