"""Run a real Home Assistant process with the Naver weather source replaced by synthetic data.

Usage: python devtools/ui_check/run_hass.py CONFIG_DIR
NWeatherAPI.update, the integration's only network call, is replaced as tests_ha's
test_setup_lifecycle does: it fills the same result keys and forecast rows the parser fills,
with synthetic values, and never opens a session. Home Assistant itself (core, frontend,
config and options flows, registries) runs unmodified through its own entry point.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from custom_components.naver_weather_custom.api_nweather import (  # noqa: E402
    KST,
    NWeatherAPI,
)
from custom_components.naver_weather_custom.const import (  # noqa: E402
    CAI_GRADE,
    CO_GRADE,
    CONDITION,
    FEEL_TEMP,
    LOCATION,
    MAX_TEMP,
    MIN_TEMP,
    NDUST,
    NDUST_GRADE,
    NO2_GRADE,
    NOW_CAST,
    NOW_HUMI,
    NOW_TEMP,
    NOW_WEATHER,
    OZON_GRADE,
    PUBLIC_TIME_C,
    PUBLIC_TIME_H,
    PUBLIC_TIME_W,
    RAIN_PERCENT,
    RAINFALL,
    RAINY_START,
    RAINY_START_TMR,
    SO2_GRADE,
    TOMORROW_AM,
    TOMORROW_MAX,
    TOMORROW_MIN,
    TOMORROW_PM,
    UDUST,
    UDUST_GRADE,
    UV_GRADE,
    WIND_DIR,
    WIND_SPEED,
)


async def _synthetic_update(api: NWeatherAPI) -> None:
    """Fill the parser's result keys and forecast rows with synthetic values; opens no session."""
    now = datetime.now(KST).replace(minute=0, second=0, microsecond=0)
    published = now.isoformat()
    api.weathertype = "wt1"
    api.result = {
        LOCATION[0]: "검증시 검증구",
        NOW_CAST[0]: "어제보다 1° 높아요",
        NOW_WEATHER[0]: "맑음",
        NOW_TEMP[0]: "21.5",
        NOW_HUMI[0]: "55",
        CONDITION[0]: "sunny",
        WIND_SPEED[0]: "2.1",
        WIND_DIR[0]: "북서",
        MIN_TEMP[0]: "14",
        MAX_TEMP[0]: "24",
        FEEL_TEMP[0]: "21.0",
        RAINFALL[0]: "0",
        UV_GRADE[0]: "보통",
        NDUST[0]: "28",
        NDUST_GRADE[0]: "좋음",
        UDUST[0]: "12",
        UDUST_GRADE[0]: "좋음",
        OZON_GRADE[0]: "보통",
        CO_GRADE[0]: "좋음",
        SO2_GRADE[0]: "좋음",
        NO2_GRADE[0]: "좋음",
        CAI_GRADE[0]: "좋음",
        TOMORROW_AM[0]: "맑음",
        TOMORROW_MIN[0]: "13",
        TOMORROW_PM[0]: "구름많음",
        TOMORROW_MAX[0]: "23",
        RAINY_START[0]: "비 소식 없음",
        RAINY_START_TMR[0]: "비 소식 없음",
        RAIN_PERCENT[0]: "10.0",
        PUBLIC_TIME_C[0]: published,
        PUBLIC_TIME_H[0]: published,
        PUBLIC_TIME_W[0]: published,
    }
    api.forecast = [
        {
            "datetime": (now + timedelta(days=day)).replace(hour=0),
            "templow": 13.0 + day,
            "temperature": 23.0 + day,
            "condition": "partlycloudy",
            "condition_am": "sunny",
            "condition_pm": "partlycloudy",
            "weathertype_am": "wt1",
            "weathertype_pm": "wt5",
            "rain_rate_am": 10,
            "rain_rate_pm": 20,
        }
        for day in range(7)
    ]
    api.forecast_hour = [
        {
            "datetime": now + timedelta(hours=hour),
            "native_temperature": 21.0 - hour % 6,
            "condition": "sunny",
            "weathertype_hour": "wt1",
            "precipitation_probability": 10,
            "native_precipitation": 0.0,
            "humidity": 55.0,
            "wind_speed": 2.0,
            "wind_bearing": 315.0,
        }
        for hour in range(24)
    ]


def main() -> int:
    config_dir = sys.argv[1]
    with patch.object(NWeatherAPI, "update", _synthetic_update):
        from homeassistant.__main__ import main as hass_main

        sys.argv = ["hass", "--config", config_dir, "--skip-pip"]
        return hass_main()


if __name__ == "__main__":
    sys.exit(main())
