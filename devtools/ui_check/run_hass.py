"""Run a real Home Assistant process with the Naver weather source replaced by synthetic data.

Usage: python devtools/ui_check/run_hass.py CONFIG_DIR
Fixed entries use synthetic payloads. The current-location entry parses synthetic weather
and air responses keyed by its real queries. Home Assistant itself runs unmodified through
its own entry point.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Import Home Assistant first, as its own entry point does: it installs probatio as voluptuous, so the
# integration's websocket command schema resolves to the same validator HA uses for every message.
import homeassistant  # noqa: E402, F401

from custom_components.naver_weather_custom import api_nweather  # noqa: E402
from custom_components.naver_weather_custom.api_nweather import (  # noqa: E402
    KST,
    NWeatherAPI,
)
from custom_components.naver_weather_custom.const import (  # noqa: E402
    BSE_URL,
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

_REAL_UPDATE = NWeatherAPI.update


def _location_session() -> Mock:
    """Return raw responses only for the supported synthetic Companion queries."""
    pages = {}
    for query, title, temp, dust in (
        ("서울특별시 은평구 응암2동", "은평구 응암2동", 21, 24),
        ("서울특별시 은평구", "서울특별시 은평구", 26, 35),
    ):
        pages[BSE_URL.format(f"{query} 날씨")] = f"""
          <div class="title_area _area_panel"><h2 class="title">{title}</h2></div>
          <div class="temperature_text">{temp}°</div>
          <div class="weather_info"><div><div><div class="weather_graphic">
            <div class="weather_main"><i class="wt_icon ico_wt1"><span class="blind">맑음</span></i></div>
          </div></div></div></div>
          <div class="open"><div class="graph_inner _hourly_weather"><ul>
            <li class="_li"><dl><dt class="time">12시</dt>
              <dd class="weather_box"><i class="wt_icon ico_wt1"><span>맑음</span></i></dd>
              <dd><span class="num">{temp + 1}</span></dd>
            </dl></li>
          </ul></div></div>
        """
        pages[BSE_URL.format(f"{query} 미세먼지")] = (
            '<div class="state_info"><div class="grade"><div class="text_box">'
            f'<span class="num">{dust}</span></div></div></div>'
        )

    return Mock(get=AsyncMock(side_effect=lambda url, **_: Mock(text=AsyncMock(return_value=pages[url]))))


async def _synthetic_update(api: NWeatherAPI, area: str | None = None) -> None:
    """Leave the moving entry on the normal update path."""
    if api.location_entity is not None:
        await _REAL_UPDATE(api, area)
        return
    now = datetime.now(KST).replace(minute=0, second=0, microsecond=0)
    published = now.isoformat()
    second = "검증2동" in (api.area or "")
    offset = 50 if second else 0
    api.weathertype = "wt1"
    api.result = {
        LOCATION[0]: "검증시 검증2동" if second else "검증시 검증구",
        NOW_CAST[0]: "어제보다 1° 높아요",
        NOW_WEATHER[0]: "맑음",
        NOW_TEMP[0]: f"{21.5 + offset:.1f}",
        NOW_HUMI[0]: "55",
        CONDITION[0]: "sunny",
        WIND_SPEED[0]: "2.1",
        WIND_DIR[0]: "북서",
        MIN_TEMP[0]: str(14 + offset),
        MAX_TEMP[0]: str(24 + offset),
        FEEL_TEMP[0]: f"{21.0 + offset:.1f}",
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
        TOMORROW_MIN[0]: str(13 + offset),
        TOMORROW_PM[0]: "구름많음",
        TOMORROW_MAX[0]: str(23 + offset),
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
            "templow": 13.0 + day + offset,
            "temperature": 23.0 + day + offset,
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
            "native_temperature": 21.0 - hour % 6 + offset,
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
    with (
        patch.object(NWeatherAPI, "update", _synthetic_update),
        patch.object(api_nweather, "async_get_clientsession", return_value=_location_session()),
    ):
        from homeassistant.__main__ import main as hass_main

        sys.argv = ["hass", "--config", config_dir, "--skip-pip"]
        return hass_main()


if __name__ == "__main__":
    sys.exit(main())
