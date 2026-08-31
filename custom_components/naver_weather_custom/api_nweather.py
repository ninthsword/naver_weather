"""API for naver weather component."""

import logging
import re
from datetime import datetime, timedelta, timezone

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .bs4_compat import BeautifulSoup
from .const import (
    BRAND,
    BSE_URL,
    CAI_GRADE,
    CO_GRADE,
    CONDITION,
    CONDITIONS,
    CONF_AREA,
    CONF_TODAY,
    DEVICE_REG,
    DEVICE_UNREG,
    DEVICE_UPDATE,
    FEEL_TEMP,
    LOCATION,
    MAX_TEMP,
    MIN_TEMP,
    MODEL,
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
    SW_VERSION,
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

_LOGGER = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def _as_kst(reference: datetime) -> datetime:
    """Return a timezone-aware reference time in Korea Standard Time."""
    if reference.tzinfo is None:
        return reference.replace(tzinfo=KST)
    return reference.astimezone(KST)


def resolve_daily_timestamp_kst(label: str | None, reference: datetime) -> datetime | None:
    """Resolve Naver's displayed ``M.D.`` label to a KST midnight timestamp."""
    match = re.search(r"(\d{1,2})\.(\d{1,2})\.?", label or "")
    if match is None:
        return None

    reference_kst = _as_kst(reference)
    month, day = (int(value) for value in match.groups())
    candidates = []
    for year in range(reference_kst.year - 1, reference_kst.year + 2):
        try:
            candidates.append(datetime(year, month, day, tzinfo=KST))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs(candidate.date() - reference_kst.date()))


def resolve_hourly_timestamps_kst(
    labels: list[str | None], reference: datetime
) -> list[datetime | None]:
    """Resolve displayed hourly labels into strictly increasing KST timestamps."""
    reference_kst = _as_kst(reference)
    current_date = reference_kst.date()
    previous = None
    timestamps = []

    for label in labels:
        text = (label or "").strip()
        explicit_date = resolve_daily_timestamp_kst(text, reference_kst)
        if explicit_date is not None:
            current_date = explicit_date.date()
        elif "모레" in text:
            current_date = reference_kst.date() + timedelta(days=2)
        elif "내일" in text:
            current_date = reference_kst.date() + timedelta(days=1)

        hour_match = re.search(r"(?:^|\s)(\d{1,2})\s*시", text)
        if hour_match is not None:
            hour = int(hour_match.group(1))
        elif explicit_date is not None or "내일" in text or "모레" in text:
            hour = 0
        else:
            timestamps.append(None)
            continue

        if hour > 23:
            timestamps.append(None)
            continue

        timestamp = datetime.combine(current_date, datetime.min.time(), tzinfo=KST)
        timestamp += timedelta(hours=hour)
        while previous is not None and timestamp <= previous:
            timestamp += timedelta(days=1)
        current_date = timestamp.date()
        previous = timestamp
        timestamps.append(timestamp)

    return timestamps


PUBLICATION_TIME_SELECTOR = (
    "div.api_subject_bx._weekly_weather_wrap "
    "div.notice_area._related_info._info_layer_wrap "
    "div.layer_pop._select_panel > p.desc"
)
PUBLICATION_TIME_LABELS = (
    ("현재 및 1시간예보", PUBLIC_TIME_C[0]),
    ("시간별예보", PUBLIC_TIME_H[0]),
    ("주간예보", PUBLIC_TIME_W[0]),
)
PUBLICATION_TIME_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2})\.(\d{1,2})\.?\s*(\d{1,2}):(\d{2})(?!\d)"
)
PUBLICATION_LABEL_PATTERN = re.compile(
    r"(?P<label>현재 및 1시간예보|시간별예보|주간예보)"
    r"(?P<body>.*?)(?=(?:현재 및 1시간예보|시간별예보|주간예보)|$)",
    re.DOTALL,
)
HOURLY_ROW_SELECTOR = "div.graph_inner._hourly_weather li._li"
HOURLY_RAIN_PERCENT_SELECTOR = (
    "div._hourly_rain div.climate_box div.icon_wrap ul li.data em.value"
)
HOURLY_RAINFALL_SELECTOR = (
    "div._hourly_rain div.climate_box div.rainfall ul li.data div.data_inner"
)
HOURLY_HUMIDITY_SELECTOR = (
    "div._hourly_humidity div.climate_box div.graph_wrap ul li.data "
    "div.data_inner span.base_bar span.num"
)
HOURLY_WIND_DIRECTION_SELECTOR = (
    "div._hourly_wind div.icon_wrap "
    "ul li.data em.value"
)
HOURLY_WIND_SPEED_SELECTOR = (
    "div._hourly_wind div.graph_wrap "
    "ul li.data span.num"
)


def resolve_public_timestamp_kst(
    label: str | None, reference: datetime
) -> datetime | None:
    """Resolve Naver's ``MM.DD. HH:MM`` publication label to KST."""
    match = PUBLICATION_TIME_PATTERN.search(label or "")
    if match is None:
        return None
    month, day, hour, minute = (int(value) for value in match.groups())
    reference_kst = _as_kst(reference)
    candidates = []
    for year in range(reference_kst.year - 1, reference_kst.year + 2):
        try:
            candidates.append(
                datetime(year, month, day, hour, minute, tzinfo=KST)
            )
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs(candidate - reference_kst))


def _node_text(node: object) -> str:
    """Return a node's visible text without making malformed HTML fatal."""
    try:
        get_text = getattr(node, "get_text", None)
        if callable(get_text):
            return str(get_text("\n", strip=True) or "").strip()
        return str(getattr(node, "text", "") or "").strip()
    except (AttributeError, TypeError, ValueError):
        return ""


def format_weather_cast(text: str | None, blind: str | None) -> str | None:
    """Format a weather-cast label without making optional markup fatal."""
    if text is None:
        return None
    original = text.strip() if isinstance(text, str) else str(text).strip()
    if not isinstance(blind, str) or not blind:
        return original
    parts = original.split(blind, 1)
    if len(parts) != 2:
        return original
    return f"{parts[1].strip()}, {parts[0]}{blind}"


def parse_publication_times(
    soup: object, reference: datetime
) -> dict[str, str | None]:
    """Parse the three weather-panel publication lines into ISO-8601 KST."""
    publication_times = {key: None for _, key in PUBLICATION_TIME_LABELS}
    try:
        notices = soup.select(PUBLICATION_TIME_SELECTOR)
    except (AttributeError, TypeError, ValueError):
        return publication_times
    for notice in notices or []:
        text = " ".join(_node_text(notice).split())
        for match in PUBLICATION_LABEL_PATTERN.finditer(text):
            key = dict(PUBLICATION_TIME_LABELS).get(match.group("label"))
            timestamp = resolve_public_timestamp_kst(match.group("body"), reference)
            if timestamp is not None:
                publication_times[key] = timestamp.isoformat()
    return publication_times


WIND_DIRECTION_DEGREES = {
    "북": 0,
    "북북동": 22.5,
    "북동": 45,
    "동북동": 67.5,
    "동": 90,
    "동남동": 112.5,
    "남동": 135,
    "남남동": 157.5,
    "남": 180,
    "남남서": 202.5,
    "남서": 225,
    "서남서": 247.5,
    "서": 270,
    "서북서": 292.5,
    "북서": 315,
    "북북서": 337.5,
}
WIND_DIRECTION_ALIASES = {
    "N": 0,
    "NNE": 22.5,
    "NE": 45,
    "ENE": 67.5,
    "E": 90,
    "ESE": 112.5,
    "SE": 135,
    "SSE": 157.5,
    "S": 180,
    "SSW": 202.5,
    "SW": 225,
    "WSW": 247.5,
    "W": 270,
    "WNW": 292.5,
    "NW": 315,
    "NNW": 337.5,
}


def parse_wind_direction(value: str | None) -> float | None:
    """Map Korean or compass wind-direction variants to degrees."""
    if not isinstance(value, str):
        return None
    text = "".join((value or "").split())
    for direction in sorted(WIND_DIRECTION_DEGREES, key=len, reverse=True):
        if direction in text:
            return WIND_DIRECTION_DEGREES[direction]
    upper = text.upper()
    for direction, degrees in WIND_DIRECTION_ALIASES.items():
        if re.search(rf"(?<![A-Z]){direction}(?![A-Z])", upper):
            return degrees
    return None


def parse_wind_text(value: str | None) -> tuple[float | None, float | None]:
    """Parse one wind label as ``(bearing_degrees, native_meters_per_second)``."""
    text = value if isinstance(value, str) else ""
    bearing = parse_wind_direction(text)
    speed_match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*(?:m\s*/\s*s|미터/?초)", text, re.IGNORECASE
    )
    if speed_match is None:
        speed_text = re2float(text)
    else:
        speed_text = speed_match.group(1)
    try:
        speed = float(speed_text) if speed_text is not None else None
    except (TypeError, ValueError):
        speed = None
    return bearing, speed


def _select_nodes(container: object, selector: str) -> list[object]:
    try:
        return list(container.select(selector) or [])
    except (AttributeError, TypeError, ValueError):
        return []


def _node_classes(node: object) -> list[str]:
    try:
        classes = node.get("class", [])
    except (AttributeError, KeyError, TypeError):
        try:
            classes = node["class"]
        except (AttributeError, KeyError, TypeError):
            classes = []
    if isinstance(classes, str):
        return classes.split()
    return [item for item in classes if isinstance(item, str)]


def _condition_from_node(node: object) -> tuple[str | None, str | None]:
    for class_name in _node_classes(node):
        if not class_name.startswith("ico_"):
            continue
        weathertype = class_name[4:]
        condition = CONDITIONS.get(weathertype, [None])[0]
        if condition is not None:
            return weathertype, condition
    return None, None


def _hourly_condition_values(rows: list[object]) -> list[tuple[str | None, str | None]]:
    values = []
    for row in rows:
        icons = _select_nodes(row, "dd.weather_box > i")
        values.append(_condition_from_node(icons[0]) if icons else (None, None))
    return values


def _hourly_wind_values(
    panel: object, row_count: int
) -> list[tuple[float | None, float | None]]:
    """Align independent direction and speed arrays to hourly weather rows."""
    directions = _select_nodes(panel, HOURLY_WIND_DIRECTION_SELECTOR)
    speeds = _select_nodes(panel, HOURLY_WIND_SPEED_SELECTOR)
    values = []
    for index in range(row_count):
        direction = (
            parse_wind_direction(_node_text(directions[index]))
            if index < len(directions)
            else None
        )
        speed = (
            _optional_float(_node_text(speeds[index]))
            if index < len(speeds)
            else None
        )
        values.append((direction, speed))
    return values


def _optional_float(value: str | None) -> float | None:
    if not value or value.strip() in {"-", "—", "없음"}:
        return None
    try:
        parsed = re2float(value)
        return float(parsed) if parsed is not None else None
    except (TypeError, ValueError):
        return None


def _optional_probability(value: str | None) -> int | None:
    if not value or value.strip() in {"-", "—", "없음"}:
        return 0 if value and value.strip() == "-" else None
    parsed = re2num(value)
    try:
        return int(parsed) if parsed is not None else None
    except (TypeError, ValueError):
        return None


def parse_hourly_forecast(panel: object | None, reference: datetime) -> list[dict]:
    """Parse one open hourly panel, preserving rows when optional arrays are short."""
    if panel is None:
        return []
    rows = _select_nodes(panel, HOURLY_ROW_SELECTOR)
    if not rows:
        return []
    labels = []
    temperatures = []
    for row in rows:
        time_node = _select_nodes(row, "dt.time")
        temp_node = _select_nodes(row, "span.num")
        labels.append(_node_text(time_node[0]) if time_node else None)
        temperatures.append(
            _optional_float(_node_text(temp_node[0]) if temp_node else None)
        )
    timestamps = resolve_hourly_timestamps_kst(labels, reference)
    conditions = _hourly_condition_values(rows)
    rain_percent = [
        _node_text(node)
        for node in _select_nodes(panel, HOURLY_RAIN_PERCENT_SELECTOR)
    ]
    rainfall = [
        _node_text(node)
        for node in _select_nodes(panel, HOURLY_RAINFALL_SELECTOR)
    ]
    humidity = [
        _node_text(node)
        for node in _select_nodes(panel, HOURLY_HUMIDITY_SELECTOR)
    ]
    winds = _hourly_wind_values(panel, len(rows))
    forecast = []
    for index, timestamp in enumerate(timestamps):
        if timestamp is None:
            continue
        # Naver's condition and rain values on the row labelled T describe
        # the interval immediately preceding that timestamp.  Keep the row
        # timestamp (and temperature/wind/humidity) at its exact T index.
        row_condition = conditions[index] if index < len(conditions) else (None, None)
        row_percent = (
            _optional_probability(rain_percent[index])
            if index < len(rain_percent)
            else None
        )
        row_rainfall = (
            _optional_float(rainfall[index]) if index < len(rainfall) else None
        )
        bearing, speed = winds[index] if index < len(winds) else (None, None)
        forecast.append(
            {
                "datetime": timestamp,
                "native_temperature": temperatures[index],
                "condition": row_condition[1],
                "weathertype_hour": row_condition[0],
                "precipitation_probability": row_percent,
                "native_precipitation": row_rainfall,
                "humidity": _optional_float(humidity[index])
                if index < len(humidity)
                else None,
                "wind_bearing": bearing,
                "wind_speed": speed,
            }
        )
    return forecast


def _open_hourly_panel(soup: object) -> object | None:
    """Return the open weather panel that owns all hourly arrays."""
    try:
        panels = soup.select("div.open")
    except (AttributeError, TypeError, ValueError):
        return None
    for panel in panels or []:
        if _select_nodes(panel, HOURLY_ROW_SELECTOR):
            return panel
    return None


def filter_daily_forecast_rows(
    rows: list[dict], include_today: bool, reference: datetime
) -> list[dict]:
    """Return a presentation-only daily subset without mutating the source rows."""
    if include_today:
        return list(rows)

    today = _as_kst(reference).date()
    return [
        row
        for row in rows
        if not isinstance(row.get("datetime"), datetime)
        or _as_kst(row["datetime"]).date() != today
    ]


def re2num(val):
    if val is None:
        return None

    r = re.compile(r"-?\d+")
    rtn = r.findall(val)

    if len(rtn) > 0:
        return rtn[0]
    else:
        return None


def retain_previous_humidity(
    current: object, previous: object
) -> str | int | float | None:
    """Keep the last valid humidity when Naver omits the current summary value.

    The API result has no timestamp for the current humidity observation, so this is a
    deliberately small last-known-value fallback, not a freshly measured reading. Startup
    remains unknown until a valid value is observed; the next valid current value replaces it.
    """
    for value in (current, previous):
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            if 0 <= value <= 100:
                return value
            continue
        if (
            isinstance(value, str)
            and re.fullmatch(r"\d{1,3}", value.strip())
            and int(value) <= 100
        ):
            return value
    return None

def re2float(val):
    if val is None:
        return None

    r = re.compile(r"-?\d+(?:\.\d+)?")
    rtn = r.findall(val)

    if len(rtn) > 0:
        return rtn[0]
    else:
        return None


def re2key(key,val):
    if val is None:
        return None
        
    r = re.compile(f"{key} -?\\d+\\.?\\d?")
    rtn = r.findall(val)

    if len(rtn) > 0:
        return rtn[0]
    else:
        return None

def re2keyW(val):
    if val is None:
        return None

    r = re.compile(r"바람\(\w+풍\) \d+\.?\d?m/s")
    rtn = r.findall(val)

    if len(rtn) > 0:
        return rtn[0]
    else:
        r = re.compile(r"\d+\.?\d?m/s")
        rtn = r.findall(val)

        if len(rtn) > 0:
            return rtn[0]
        else:
            return None

def re2keyWD(val):
    if val is None:
        return None

    r = re.compile(r"[동|서|남|북]+")
    rtn = r.findall(val)

    if len(rtn) > 0:
        return rtn[0]
    else:
        return None

def eLog(val):
    _LOGGER.error(f"[{BRAND}] error : {val}")

class NWeatherAPI:
    """NWeather API."""

    def __init__(self, hass, entry, count):
        """Initialize the NWeather API.."""
        self.hass = hass
        self.entry = entry
        self.count = count
        self.result = {}
        self.forecast = []
        self.forecast_hour = []
        self.weathertype = ""
        self.version = SW_VERSION
        self.model = MODEL
        self.brand = BRAND.lower()
        self.brand_name = BRAND
        self.unique = {}

        _LOGGER.debug(f"[{BRAND}] Initialize -> {self.area}")

    @property
    def logger(self):
        """Return the integration logger for the update coordinator."""
        return _LOGGER

    @property
    def area(self):
        """Return area."""
        data = self.entry.options.get(CONF_AREA, self.entry.data.get(CONF_AREA))
        if data == "날씨":
            return data
        else:
            return data + " 날씨"

    def set_data(self, name, value):
        """Set entry data."""
        self.hass.config_entries.async_update_entry(
            entry=self.entry, data={**self.entry.data, name: value}
        )

    def get_data(self, name, default=False):
        """Get entry data."""
        return self.entry.data.get(name, default)

    @property
    def today(self):
        """Return area."""
        today = self.entry.options.get(
            CONF_TODAY, self.entry.data.get(CONF_TODAY, True)
        )

        return today


    def init_device(self, unique_id):
        """Initialize device."""
        self.unique[unique_id] = {
            DEVICE_UPDATE: None,
            DEVICE_REG: self.register_update_state,
            DEVICE_UNREG: self.unregister_update_state,
        }

    def get_device(self, unique_id, key):
        """Get device info."""
        return self.unique.get(unique_id, {}).get(key)

    def device_update(self, device_id):
        """Update device state."""
        unique_id = self.area + ":" + device_id
        device_update = self.unique.get(unique_id, {}).get(DEVICE_UPDATE)
        if device_update is not None:
            device_update()

    def register_update_state(self, unique_id, cb):
        """Register device update function to update entity state."""
        if not self.unique[unique_id].get(DEVICE_UPDATE):
            _LOGGER.info(f"[{BRAND}] Register device => {unique_id} [{self.area}]")
            self.unique[unique_id][DEVICE_UPDATE] = cb

    def unregister_update_state(self, unique_id):
        """Unregister device update function."""
        if self.unique[unique_id][DEVICE_UPDATE] is not None:
            _LOGGER.info(f"[{BRAND}] Unregister device => {unique_id} [{self.area}]")
            self.unique[unique_id][DEVICE_UPDATE] = None
            
    def _bs4_select_one(self, bs4, selector, bText=True, tag=""):

        try:
            tmp = bs4.select_one(selector)

            if tmp is not None:
                if bText:
                    val = tmp.text.strip()
                else:
                    val = tmp
            else:
                val = None

            return val;
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            _LOGGER.error( f"[{BRAND}] _bs4_select_one Error {tag} : {e}" )

    
    async def update(self):
        """Update function for updating api information."""
        try:
            url = BSE_URL.format(self.area)
            url_air = url.replace("날씨", "미세먼지")

            hdr = {
                "User-Agent": (
                    "mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) chrome/78.0.3904.70 safari/537.36"
                ),
                "Referer": (
                    "https://naver.com"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
                ),
                "Accept-Language": (
                    "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,de;q=0.6,id;q=0.5,ja;q=0.4,zh-CN;q=0.3,zh;q=0.2"
                )
            }

            session = async_get_clientsession(self.hass)

            response = await session.get(url, headers=hdr, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(await response.text(), "html.parser")

            #미세먼지
            air = await session.get(url_air, headers=hdr, timeout=30)
            air.raise_for_status()

            bs4air = BeautifulSoup(await air.text(), "html.parser")
            reference_time = datetime.now(KST)

            # 지역
            LocationInfo = self._bs4_select_one(soup, "div.title_area._area_panel > h2.title")

            # 현재 온도
            NowTempRaw = self._bs4_select_one(soup, "div.temperature_text")
            NowTemp    = re2float(NowTempRaw)

            # 날씨 캐스트
            WeatherCast = None
            NowWeather  = None

            wCast = self._bs4_select_one(soup, "div.temperature_info > p", False)

            if wCast is not None:
                cWeather = self._bs4_select_one(wCast, "span.weather")
                blind    = self._bs4_select_one(wCast, "span.blind")

                WeatherCast = format_weather_cast(wCast.text, blind)

                #현재날씨
                NowWeather = cWeather

            # 오늘 오전온도, 오후온도
            TodayMinTemp = self._bs4_select_one(soup, "div.list_box > ul > li.week_item.today > div > div.cell_temperature > span > span.lowest")
            TodayMaxTemp = self._bs4_select_one(soup, "div.list_box > ul > li.week_item.today > div > div.cell_temperature > span > span.highest")

            TodayMinTemp = re2num(TodayMinTemp)
            TodayMaxTemp = re2num(TodayMaxTemp)
            
            # 요약
            summ = self._bs4_select_one(soup, "div.weather_info > div > div > div.temperature_info > dl")

            # 체감온도
            TodayFeelTemp = re2float(re2key("체감", summ))

            # 습도
            Humidity      = retain_previous_humidity(
                re2num(re2key("습도", summ)), self.result.get(NOW_HUMI[0])
            )

            # 현재풍속/풍향
            wind      = re2keyW(summ)
            WindSpeed = re2float(wind)
            WindState = re2keyWD(summ)

            # 강수
            Rainfall    = self._bs4_select_one(soup, "div.climate_box > div.graph_wrap > ul > li > div")
            
            # 자외선 지수
            rainPercentVal = soup.select("div.climate_box > div.icon_wrap > ul > li > em")

            nCnt = 0
            rainSum = 0

            for em in rainPercentVal:

                if nCnt > 11:
                    continue

                if '%' in em.text:
                    rainSum += int(em.text[:-1])

                nCnt += 1

            rainPercent = str( round(rainSum/11, 1) if rainSum > 0 else 0 )
            
            # 미세먼지/초미세먼지/자외선(등급)/일몰일출
            reportCardWrap = soup.select("div.report_card_wrap > ul.today_chart_list > li.item_today")
           
            arrReportCard = []

            TodayUVGrade = "데이터 없음"

            for li in reportCardWrap:
                gb    = self._bs4_select_one(li, "strong.title")
                gbVal = self._bs4_select_one(li, "span.txt")
            
                tmp = {"id": gb, "val": gbVal}

                arrReportCard.append(tmp)

                if "자외선" in gb:
                    TodayUVGrade = gbVal

            # condition
            condition_raw = soup.select(
                "div.weather_info > div > div > div.weather_graphic > "
                "div.weather_main > i.wt_icon"
            )
            if condition_raw:
                weathertype, condition = _condition_from_node(condition_raw[0])
            else:
                weathertype = None
                condition = None
                
            self._bs4_select_one(soup, "div.weather_info > div > div > div.weather_graphic > div.weather_main > i > span.blind")
            #eLog(contdition_blind_text)
            
            # 비시작시간
            rainyStart    = "비안옴"
            rainyStartTmr = "비안옴"

            # 시간별 날씨 is limited to the active/open weather panel.
            hourly_panel = _open_hourly_panel(soup)
            hourly = (
                _select_nodes(hourly_panel, HOURLY_ROW_SELECTOR)
                if hourly_panel is not None
                else []
            )
            hourly_today = True
            hourly_tmr = True
            tomorrow = False
            for h in hourly:
                time_text = self._bs4_select_one(h, "dt.time") or ""
                if "내일" in time_text:
                    hourly_today = False
                    tomorrow = True
                if "모레" in time_text:
                    hourly_tmr = False
                    tomorrow = False
                if "시" not in time_text and "내일" not in time_text and "모레" not in time_text:
                    continue
                wt = self._bs4_select_one(h, "i.wt_icon") or ""
                if "비" not in wt and "소나기" not in wt:
                    continue
                if hourly_today:
                    hourly_today = False
                    rainyStart = time_text
                if hourly_tmr:
                    hourly_tmr = False
                    if "내일" in time_text:
                        rainyStartTmr = "내일 00시"
                    elif tomorrow:
                        rainyStartTmr = f"내일 {time_text}"
                    else:
                        rainyStartTmr = time_text

            # 내일 오전/오후 온도와 상태
            tomorrowMTemp = "-"
            tomorrowMState = "-"
            tomorrowATemp = "-"
            tomorrowAState = "-"

            weekly = soup.find("div", {"class": "weekly_forecast_area _toggle_panel"})
            date_info = weekly.find_all("li", {"class": "week_item"}) if weekly else []
            forecast = []
            forecast_hour = parse_hourly_forecast(hourly_panel, reference_time)

            bStart = False
            
            for di in date_info:
                data = {}

                # day
                dayDesc = self._bs4_select_one(di, "div > div.cell_date > span > strong.day")

                if (dayDesc == "오늘"):
                    bStart = True

                if ( not bStart ):
                    continue

                dayInfo = self._bs4_select_one(
                    di, "div > div.cell_date > span > span.date"
                )
                daily_timestamp = resolve_daily_timestamp_kst(dayInfo, reference_time)
                if daily_timestamp is None:
                    continue
                data["datetime"] = daily_timestamp
                    
                try:
                    # temp
                    low  = re2num(self._bs4_select_one(di, "span.lowest"))
                    high = re2num(self._bs4_select_one(di, "span.highest"))
                    data["templow"]     = float(low)
                    data["temperature"] = float(high)

                    # condition
                    cell_w = di.select("div.cell_weather > span > i.wt_icon > span")

                    conditionRaw = di.select("div.cell_weather > span > i")

                    condition_am = conditionRaw[0]["class"][1].replace("ico_", "")
                    condition_pm = conditionRaw[1]["class"][1].replace("ico_", "")

                    data["condition"]    = CONDITIONS[condition_pm][0]
                    data["condition_am"] = CONDITIONS[condition_am][0]
                    data["condition_pm"] = CONDITIONS[condition_pm][0]
                    data["weathertype_am"] = condition_am
                    data["weathertype_pm"] = condition_pm

                    # rain_rate
                    rainRaw = di.select("div.cell_weather > span > span.weather_left > span.rainfall")

                    rain_m = rainRaw[0].text
                    data["rain_rate_am"] = int(re2num(rain_m))

                    rain_a = rainRaw[1].text
                    data["rain_rate_pm"] = int(re2num(rain_a))

                    forecast.append(data)
                        
                    #내일 날씨
                    if di.select_one("div > div.cell_date > span > strong.day").text == "내일":
                        # 내일 오전온도
                        tomorrowMTemp = low

                        # 내일 오전상태
                        rain_a = rainRaw[1].text

                        # 내일 오후온도
                        tomorrowATemp = high

                        # 내일 오후상태
                        tomorrowAState = cell_w[1].text

                except (AttributeError, IndexError, KeyError, TypeError, ValueError) as ex:
                    eLog(ex)


            publication_times = parse_publication_times(soup, reference_time)

            # 미세먼지, 초미세먼지, 오존 지수
            FineDust           = self._bs4_select_one(bs4air, "div.state_info:nth-of-type(1) div.grade div.text_box > span.num")
            FineDustGrade      = self._bs4_select_one(bs4air, "div.state_info:nth-of-type(1) div.grade > span.text")
            UltraFineDust      = self._bs4_select_one(bs4air, "div.state_info:nth-of-type(2) div.grade div.text_box > span.num")
            UltraFineDustGrade = self._bs4_select_one(bs4air, "div.state_info:nth-of-type(2) div.grade > span.text")

            # 오염물질(오존/일산화탄소/아황산가스/이산화질소/통합대기)
            pollution = bs4air.find("div", {"class": "other_air_info"})

            # 초기화
            OzonGrade = None
            coGrade = None
            so2Grade = None
            no2Grade = None
            caiGrade = None

            if pollution is not None:
                survey = pollution.select("ul.air_info_list > li")

                arrSurveyRslt = []

                for li in survey:
                    tmp1 = self._bs4_select_one(li, "span.info_title") #구분
                    tmp2 = self._bs4_select_one(li, "span.state") #등급

                    tmpDict = { "id": tmp1, "grd": tmp2}   
            
                    arrSurveyRslt.append(tmpDict)

                for arr in arrSurveyRslt:
                    if arr["id"] == OZON_GRADE[1]:
                        OzonGrade = arr["grd"]

                    if arr["id"] == CO_GRADE[1]:
                        coGrade = arr["grd"]

                    if arr["id"] == SO2_GRADE[1]:
                        so2Grade = arr["grd"]

                    if arr["id"] == NO2_GRADE[1]:
                        no2Grade = arr["grd"]

                    if arr["id"] == CAI_GRADE[1]:
                        caiGrade = arr["grd"]

            # 오염물질 제공
            offerInfo = self._bs4_select_one(bs4air, "div.inner > div.offer_info > span.update")

            if FineDust is None:
                FineDust = '0'

            if UltraFineDust is None:
                UltraFineDust = '0'

            if Rainfall is None:
                Rainfall = '0'

            self.forecast = forecast
            self.forecast_hour = forecast_hour
            self.weathertype = weathertype

            self.result = {
                LOCATION[0]: LocationInfo,
                NOW_CAST[0]: WeatherCast,
                NOW_WEATHER[0]: NowWeather,
                NOW_TEMP[0]: NowTemp,
                NOW_HUMI[0]: Humidity,
                CONDITION[0]: condition,
                WIND_SPEED[0]: WindSpeed,
                WIND_DIR[0]: WindState,
                MIN_TEMP[0]: TodayMinTemp,
                MAX_TEMP[0]: TodayMaxTemp,
                FEEL_TEMP[0]: TodayFeelTemp,
                RAINFALL[0]: Rainfall,
                UV_GRADE[0]: TodayUVGrade,
                NDUST[0]: FineDust,
                NDUST_GRADE[0]: FineDustGrade,
                UDUST[0]: UltraFineDust,
                UDUST_GRADE[0]: UltraFineDustGrade,
                OZON_GRADE[0]: OzonGrade,
                CO_GRADE[0]: coGrade,
                SO2_GRADE[0]: so2Grade,
                NO2_GRADE[0]: no2Grade,
                CAI_GRADE[0]: caiGrade,
                TOMORROW_AM[0]: tomorrowMState,
                TOMORROW_MIN[0]: tomorrowMTemp,
                TOMORROW_PM[0]: tomorrowAState,
                TOMORROW_MAX[0]: tomorrowATemp,
                RAINY_START[0]: rainyStart,
                RAINY_START_TMR[0]: rainyStartTmr,
                RAIN_PERCENT[0]: rainPercent,
                PUBLIC_TIME_C[0]: publication_times[PUBLIC_TIME_C[0]],
                PUBLIC_TIME_H[0]: publication_times[PUBLIC_TIME_H[0]],
                PUBLIC_TIME_W[0]: publication_times[PUBLIC_TIME_W[0]],
                "airOfferInfoUpdate": offerInfo
            }
            
            _LOGGER.info(f"[{BRAND}] Update weather information -> {self.result}")
            
        except Exception as ex:
            _LOGGER.error(f"[{BRAND}] Failed to update NWeather API status Error: {ex}")
            raise
