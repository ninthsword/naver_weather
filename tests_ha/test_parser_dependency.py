"""Synthetic parser regressions using fresh real HA and Beautiful Soup imports."""

import subprocess
import sys
import unittest
from pathlib import Path
from textwrap import dedent

REPOSITORY = Path(__file__).resolve().parents[1]

# Keep the subprocess free of the lightweight suite's HA and parser shims.
PARSER_SETUP = """
from datetime import datetime
from html import escape
from pathlib import Path

import homeassistant.helpers.aiohttp_client as ha_client
import homeassistant.util.ssl as ssl_util
from bs4 import BeautifulSoup
from bs4.element import Tag
from custom_components.naver_weather_custom import api_nweather as api

assert api.BeautifulSoup is BeautifulSoup
assert api.async_get_clientsession is ha_client.async_get_clientsession
assert Path(api.__file__).resolve() == (
    Path(sys.path[0]) / "custom_components/naver_weather_custom/api_nweather.py"
)
assert ha_client.__file__ and BeautifulSoup.__module__ == "bs4"

REFERENCE = datetime(2025, 12, 31, 23, 30, tzinfo=api.KST)


def weather_rows(temperatures=("-2.5", "-1", "0")):
    rows = []
    for label, temperature, icon in zip(
        ("23시", "내일", "01시"), temperatures, ("wt1", "wt9", None)
    ):
        icon_html = (
            f'<i class="wt_icon ico_{icon}"><span>날씨</span></i>'
            if icon else ""
        )
        rows.append(
            '<li class="_li"><dl><dt class="time">'
            f'{escape(label)}</dt><dd class="weather_box">{icon_html}</dd>'
            f'<dd><span class="num">{escape(temperature)}</span></dd></dl></li>'
        )
    return '<div class="graph_inner _hourly_weather"><ul>' + ''.join(rows) + '</ul></div>'


def values(items, wrapper):
    return '<ul>' + ''.join(
        '<li class="data">' + wrapper.format(escape(item)) + '</li>'
        for item in items
    ) + '</ul>'


def optional_arrays(probabilities=(), rainfall=(), humidity=(), directions=(), speeds=()):
    return (
        '<div class="_hourly_rain"><div class="climate_box">'
        '<div class="icon_wrap">'
        + values(probabilities, '<em class="value">{}</em>')
        + '</div><div class="rainfall">'
        + values(rainfall, '<div class="data_inner">{}</div>')
        + '</div></div></div>'
        '<div class="_hourly_humidity"><div class="climate_box"><div class="graph_wrap">'
        + values(humidity, '<div class="data_inner"><span class="base_bar">'
                 '<span class="num">{}</span></span></div>')
        + '</div></div></div><div class="_hourly_wind"><div class="icon_wrap">'
        + values(directions, '<em class="value">{}</em>')
        + '</div><div class="graph_wrap">'
        + values(speeds, '<span class="num">{}</span>')
        + '</div></div>'
    )


def parse_panel(optional="", temperatures=("-2.5", "-1", "0")):
    # An unrelated open panel and a closed weather panel must not supply data.
    html = (
        '<div class="open"><span>다른 패널</span></div>'
        '<div class="closed">' + weather_rows(("90", "91", "92"))
        + optional_arrays(probabilities=("99%", "99%", "99%")) + '</div>'
        '<div id="selected" class="weather open">'
        + weather_rows(temperatures) + optional + '</div>'
    )
    soup = BeautifulSoup(html, "html.parser")
    panel = api._open_hourly_panel(soup)
    assert isinstance(panel, Tag) and panel.get("id") == "selected"
    rows = api.parse_hourly_forecast(panel, REFERENCE)
    return [{**row, "datetime": row["datetime"].isoformat()} for row in rows]


def expected_row(timestamp, temperature, condition, icon, **optional):
    return {
        "datetime": timestamp,
        "native_temperature": temperature,
        "condition": condition,
        "weathertype_hour": icon,
        "precipitation_probability": None,
        "native_precipitation": None,
        "humidity": None,
        "wind_bearing": None,
        "wind_speed": None,
        **optional,
    }


def base_rows():
    return [
        expected_row("2025-12-31T23:00:00+09:00", -2.5, "sunny", "wt1"),
        expected_row("2026-01-01T00:00:00+09:00", -1.0, "rainy", "wt9"),
        expected_row("2026-01-01T01:00:00+09:00", 0.0, None, None),
    ]


def publication_soup(body):
    return BeautifulSoup(
        '<p class="desc">현재 및 1시간예보 01.01. 12:00</p>'
        '<div class="api_subject_bx _weekly_weather_wrap">'
        '<div class="notice_area _related_info _info_layer_wrap">'
        '<div class="layer_pop _select_panel"><p class="desc">'
        + body + '</p></div></div></div>',
        "html.parser",
    )
"""


UPDATE_SETUP = """
import asyncio
from tempfile import TemporaryDirectory
from types import MappingProxyType
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.naver_weather_custom.const import (
    DOMAIN, NDUST, NOW_TEMP, RAIN_PERCENT, UDUST, WEATHER_INFO, WIND_DIR,
)
from custom_components.naver_weather_custom.coordinator import NWeatherDataUpdateCoordinator
from custom_components.naver_weather_custom.sensor import NWeatherSensor


def air_markup(fine=None, ultrafine=None):
    return ''.join(
        '<div class="state_info"><div class="grade"><div class="text_box">'
        + (f'<span class="num">{escape(value)}</span>' if value is not None else '')
        + '</div></div></div>'
        for value in (fine, ultrafine)
    )


def weather_markup(probabilities=(), temperature="-2.5", direction="북서"):
    return (
        f'<div class="temperature_text">{escape(temperature)}°</div>'
        '<div class="weather_info"><div><div><div class="temperature_info">'
        f'<dl>체감 -3.5 습도 0 바람({escape(direction)}풍) 2.5m/s</dl>'
        '</div></div></div></div>'
        + optional_arrays(probabilities=probabilities)
    )


async def update_from_markup(client, weather, air):
    responses = [Mock(), Mock()]
    for response, markup in zip(responses, (weather, air)):
        response.text = AsyncMock(return_value=markup)
    session = Mock(get=AsyncMock(side_effect=responses))
    with patch.object(api, "async_get_clientsession", return_value=session):
        await client.update()
    assert session.get.await_count == 2
    for response in responses:
        response.raise_for_status.assert_called_once_with()
    no_alpn = ssl_util.client_context()
    assert no_alpn is not ssl_util.client_context(
        ssl_util.SSLCipherList.PYTHON_DEFAULT, ssl_util.SSL_ALPN_HTTP11
    )
    assert [call.kwargs["ssl"] for call in session.get.await_args_list] == [no_alpn, no_alpn]


def make_entities(directory):
    hass = HomeAssistant(directory)
    entry = ConfigEntry(
        version=1, minor_version=1, domain=DOMAIN, title="Synthetic weather",
        data={"area": "Synthetic"}, options={}, source="user",
        unique_id="synthetic-weather", discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )
    client = api.NWeatherAPI(hass, entry, 1)
    coordinator = NWeatherDataUpdateCoordinator(hass, client, entry)
    entities = {
        key: NWeatherSensor(WEATHER_INFO[key], client, coordinator)
        for key in (NDUST[0], UDUST[0], NOW_TEMP[0], RAIN_PERCENT[0], WIND_DIR[0])
    }
    assert all(isinstance(entity, CoordinatorEntity) for entity in entities.values())
    return client, entities
"""


BROWSER_SETUP = """
SERVICE = "http://browser.invalid:8765"


def browser_client(directory):
    hass = HomeAssistant(directory)
    entry = ConfigEntry(
        version=1, minor_version=1, domain=DOMAIN, title="Synthetic weather",
        data={"area": "Synthetic"}, options={"browser_url": SERVICE}, source="user",
        unique_id="synthetic-browser-weather", discovery_keys=MappingProxyType({}),
        subentries_data=None,
    )
    return api.NWeatherAPI(hass, entry, 1)


def browser_reply(markup, status=200):
    return Mock(status=status, text=AsyncMock(return_value=markup))
"""


class ParserDependencyTest(unittest.TestCase):
    """Keep identical behavior expectations across supported parser environments."""

    def _run_parser(self, script: str) -> None:
        program = (
            f"import sys\nsys.path.insert(0, {str(REPOSITORY)!r})\n"
            + dedent(PARSER_SETUP)
            + dedent(script)
        )
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", program],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def _run_update(self, script: str) -> None:
        self._run_parser(UPDATE_SETUP + dedent(script))

    def test_browser_service_fetches_weather_and_selected_air_page(self) -> None:
        self._run_update(BROWSER_SETUP + dedent("""
            async def check():
                weather_url = api.BSE_URL.format("Synthetic 날씨")
                local_air_url = "https://search.naver.com/search.naver?query=local-air"
                weather = browser_reply(
                    weather_markup()
                    + '<div class="report_card_wrap"><ul class="today_chart_list">'
                    '<li class="item_today"><strong class="title">미세먼지</strong>'
                    f'<a href="{local_air_url}">대기질</a></li></ul></div>'
                )
                air = browser_reply(air_markup("12", "6"))
                session = Mock(get=AsyncMock(side_effect=[weather, air]))
                with TemporaryDirectory() as directory:
                    client = browser_client(directory)
                    with patch.object(api, "async_get_clientsession", return_value=session):
                        await client.update()
                    calls = session.get.await_args_list
                    assert len(calls) == 2, calls
                    assert [call.args for call in calls] == [(SERVICE + "/render",)] * 2
                    assert [call.kwargs["params"] for call in calls] == [
                        {"url": weather_url}, {"url": local_air_url},
                    ]
                    assert all(call.kwargs["timeout"].total == 60 for call in calls)
                    assert all("ssl" not in call.kwargs for call in calls)
                    for response in (weather, air):
                        response.raise_for_status.assert_not_called()
                        response.release.assert_called_once_with()
                    assert float(client.result[NOW_TEMP[0]]) == -2.5
                    assert float(client.result[NDUST[0]]) == 12
                    assert float(client.result[UDUST[0]]) == 6
            asyncio.run(check())
        """))

    def test_browser_service_failure_falls_back_only_for_that_page(self) -> None:
        self._run_update(BROWSER_SETUP + dedent("""
            async def check():
                weather_url = api.BSE_URL.format("Synthetic 날씨")
                air_url = weather_url.replace("날씨", "미세먼지")
                for failed_page in (0, 1):
                    for failure_kind in ("client", "timeout", "status"):
                        weather = browser_reply(weather_markup())
                        air = browser_reply(air_markup("12", "6"))
                        failure = (
                            api.ClientError("private-area") if failure_kind == "client"
                            else TimeoutError("private-area") if failure_kind == "timeout"
                            else browser_reply("private-area", status=502)
                        )
                        replies = [failure, weather, air] if failed_page == 0 else [weather, failure, air]
                        session = Mock(get=AsyncMock(side_effect=replies))
                        with TemporaryDirectory() as directory:
                            client = browser_client(directory)
                            with patch.object(api, "async_get_clientsession", return_value=session):
                                await client.update()
                            calls = session.get.await_args_list
                            expected = (
                                [SERVICE + "/render", weather_url, SERVICE + "/render"]
                                if failed_page == 0 else [SERVICE + "/render", SERVICE + "/render", air_url]
                            )
                            assert [call.args[0] for call in calls] == expected, calls
                            direct_index = 1 if failed_page == 0 else 2
                            direct = calls[direct_index]
                            assert direct.kwargs["ssl"] is ssl_util.client_context()
                            assert direct.kwargs["timeout"].total == 30
                            assert "headers" in direct.kwargs and "params" not in direct.kwargs
                            (weather if failed_page == 0 else air).raise_for_status.assert_called_once_with()
                            for index, call in enumerate(calls):
                                if index != direct_index:
                                    assert call.kwargs["timeout"].total == 60
                                    assert "ssl" not in call.kwargs
                            assert float(client.result[NOW_TEMP[0]]) == -2.5
                            assert float(client.result[NDUST[0]]) == 12
                            assert float(client.result[UDUST[0]]) == 6
            asyncio.run(check())
        """))

    def test_failed_direct_fallback_preserves_the_previous_complete_payload(self) -> None:
        self._run_update(BROWSER_SETUP + dedent("""
            async def check():
                with TemporaryDirectory() as directory:
                    client = browser_client(directory)
                    session = Mock(get=AsyncMock(side_effect=[
                        browser_reply(weather_markup()), browser_reply(air_markup("12", "6")),
                    ]))
                    with patch.object(api, "async_get_clientsession", return_value=session):
                        await client.update()
                    previous = (client.result, client.forecast, client.forecast_hour, client.weathertype)
                    direct = browser_reply("")
                    direct.raise_for_status.side_effect = api.ClientError("direct request failed")
                    session.get = AsyncMock(side_effect=[
                        browser_reply(weather_markup(temperature="99")),
                        browser_reply("unavailable", status=502), direct,
                    ])
                    with patch.object(api, "async_get_clientsession", return_value=session):
                        try:
                            await client.update()
                        except api.ClientError:
                            pass
                        else:
                            raise AssertionError("A failed direct fallback must fail the refresh")
                    assert len(session.get.await_args_list) == 3
                    assert client.result is previous[0]
                    assert client.forecast is previous[1]
                    assert client.forecast_hour is previous[2]
                    assert client.weathertype == previous[3]
                    assert float(client.result[NOW_TEMP[0]]) == -2.5
            asyncio.run(check())
        """))

    def test_summary_probability_average_uses_first_twelve_valid_count(self) -> None:
        self._run_update("""
            async def check():
                cases = [
                    (("100%",) * 12, 100.0),
                    (("20%", "40%"), 30.0),
                    (("0%", "100%"), 50.0),
                    (("0%",), 0.0),
                    ((), None),
                    (("bad%", "-1%", "101%", "20% extra", "—", "", "-"), None),
                    (("bad%", "0%", "100%", "101%", "-20%", "50%"), 50.0),
                    (("bad%",) * 12 + ("100%",), None),
                    (("0%",) * 12 + ("100%",), 0.0),
                    (("bad%",) * 11 + ("20%", "100%"), 20.0),
                    ((" 25% ", "75.5%"), 50.2),
                ]
                with TemporaryDirectory() as directory:
                    client, entities = make_entities(directory)
                    for probabilities, expected in cases:
                        await update_from_markup(client, weather_markup(probabilities), "")
                        result = client.result[RAIN_PERCENT[0]]
                        state = entities[RAIN_PERCENT[0]].state
                        if expected is None:
                            assert result is None and state is None, (probabilities, result, state)
                        else:
                            assert float(result) == expected, (probabilities, result)
                            assert float(state) == expected, (probabilities, state)
            asyncio.run(check())
        """)

    def test_missing_dust_stays_unknown_through_real_sensor_and_recovers(self) -> None:
        self._run_update("""
            async def check():
                with TemporaryDirectory() as directory:
                    client, entities = make_entities(directory)
                    cases = [
                        (None, None), ("12", "7"), (None, "7"),
                        ("12", None), ("0", "0"), (None, None), ("18", "9"),
                    ]
                    for fine, ultrafine in cases:
                        await update_from_markup(
                            client, weather_markup(), air_markup(fine, ultrafine)
                        )
                        for key, expected in ((NDUST[0], fine), (UDUST[0], ultrafine)):
                            assert client.result[key] == expected, (key, client.result[key])
                            expected_state = int(expected) if expected is not None else None
                            assert entities[key].state == expected_state, (key, entities[key].state)
                    await update_from_markup(client, weather_markup(), "")
                    assert all(entities[key].state is None for key in (NDUST[0], UDUST[0]))
            asyncio.run(check())
        """)

    def test_air_request_follows_only_the_naver_search_link(self) -> None:
        self._run_update("""
            from yarl import URL

            def card(title, href):
                anchor = f'<a href="{escape(href)}">x</a>' if href is not None else ''
                return (
                    '<div class="report_card_wrap"><ul class="today_chart_list">'
                    f'<li class="item_today"><strong class="title">{title}</strong>{anchor}</li>'
                    '</ul></div>'
                )

            async def air_url(client, markup):
                responses = [Mock(), Mock()]
                responses[0].text = AsyncMock(return_value=weather_markup() + markup)
                responses[1].text = AsyncMock(return_value="")
                session = Mock(get=AsyncMock(side_effect=responses))
                with patch.object(api, "async_get_clientsession", return_value=session):
                    await client.update()
                return session.get.await_args_list[1].args[0]

            async def check():
                local = "https://search.naver.com/search.naver?where=nexearch&query=local"
                default = api.BSE_URL.format("Synthetic 미세먼지")
                cases = [
                    (card("미세먼지", "?where=nexearch&query=local"), local),
                    (card("미세먼지", local), local),
                    ("", default),
                    (card("초미세먼지", local), default),
                    (card("미세먼지", None), default),
                    (card("미세먼지", "https://example.invalid/air"), default),
                    (card("미세먼지", "http://search.naver.com/air"), default),
                    (card("미세먼지", "//example.invalid/air"), default),
                    (card("미세먼지", "https://[bad/air"), default),
                    (card("미세먼지", "https://search.naver.com:abc/air"), default),
                    (card("미세먼지", "https://search.naver.com:99999/air"), default),
                    (card("미세먼지", "https://search.naver.com:8443/air"), default),
                    (card("미세먼지", "https://user:pw@search.naver.com/air"), default),
                    (card("미세먼지", ""), default),
                    (card("미세먼지", "#top"), default),
                ]
                with TemporaryDirectory() as directory:
                    client, _ = make_entities(directory)
                    for markup, expected in cases:
                        actual = await air_url(client, markup)
                        assert actual == expected, (markup, actual)
                        URL(actual)
            asyncio.run(check())
        """)

    def test_summary_numbers_accept_optional_colon_and_spacing(self) -> None:
        self._run_parser("""
            for text, feel, humidity in (
                ("체감 -3.5 습도 60", "-3.5", "60"),
                ("체감: -3.5 습도: 60", "-3.5", "60"),
                ("체감-3.5 습도60", "-3.5", "60"),
                ("바람 2m/s", None, None),
            ):
                assert api.re2key("체감", text) == feel, text
                assert api.re2key("습도", text) == humidity, text
            assert api.re2key("습도", None) is None
        """)

    def test_sensor_preserves_numeric_text_and_unknown_values(self) -> None:
        self._run_update("""
            async def check():
                with TemporaryDirectory() as directory:
                    client, entities = make_entities(directory)
                    sensor = entities[NOW_TEMP[0]]
                    for temperature in ("-2.5", "-1", "0", "3.5"):
                        await update_from_markup(client, weather_markup(temperature=temperature), "")
                        expected = 0 if temperature == "0" else temperature
                        assert sensor.state == expected, (temperature, sensor.state)
                    for value, expected in (
                        (None, None), (0, 0), (0.0, 0.0), (-2.5, -2.5),
                        ("0", 0), ("12", 12), ("-2", "-2"), ("2.5", "2.5"),
                        ("맑음", "맑음"), ("", ""), ("²", "²"),
                    ):
                        client.result[NOW_TEMP[0]] = value
                        assert sensor.state == expected, (value, sensor.state)
                        assert type(sensor.state) is type(expected), (value, sensor.state)
                    del client.result[NOW_TEMP[0]]
                    assert sensor.state is None
            asyncio.run(check())
        """)

    def test_current_wind_direction_does_not_capture_literal_pipe(self) -> None:
        self._run_update("""
            async def check():
                with TemporaryDirectory() as directory:
                    client, entities = make_entities(directory)
                    for direction, expected in (("|", None), ("북서", "북서"), ("남동", "남동")):
                        await update_from_markup(client, weather_markup(direction=direction), "")
                        assert client.result[WIND_DIR[0]] == expected
                        assert entities[WIND_DIR[0]].state == expected
            asyncio.run(check())
        """)

    def test_hourly_rollover_css_scope_and_unicode_alignment(self) -> None:
        self._run_parser("""
            rows = parse_panel(optional_arrays(
                probabilities=("20%", "40%", "60%"),
                rainfall=("0.5mm", "1.5mm", "2.5mm"),
                humidity=("60", "61", "62"),
                directions=("북서풍", "남동풍", "북북동풍"),
                speeds=("3 m/s", "4 m/s", "2.5 m/s"),
            ))
            expected = base_rows()
            for row, probability, rain, humidity, bearing, speed in zip(
                expected, (20, 40, 60), (0.5, 1.5, 2.5), (60.0, 61.0, 62.0),
                (315, 135, 22.5), (3.0, 4.0, 2.5),
            ):
                row.update(precipitation_probability=probability,
                           native_precipitation=rain, humidity=humidity,
                           wind_bearing=bearing, wind_speed=speed)
            assert rows == expected, rows
        """)

    def test_missing_and_short_optional_arrays_preserve_rows(self) -> None:
        self._run_parser("""
            assert parse_panel() == base_rows()
            rows = parse_panel(optional_arrays(
                probabilities=("30%",), rainfall=("0.5mm",), directions=("동풍",),
            ))
            expected = base_rows()
            expected[0].update(precipitation_probability=30,
                               native_precipitation=0.5, wind_bearing=90)
            assert rows == expected, rows
            assert api.parse_hourly_forecast(None, REFERENCE) == []
            empty = BeautifulSoup('<div class="open">자료 없음</div>', "html.parser")
            assert api._open_hourly_panel(empty) is None
        """)

    def test_malformed_optional_values_keep_safe_per_row_defaults(self) -> None:
        self._run_parser("""
            rows = parse_panel(optional_arrays(
                probabilities=("-", "—", "자료 없음"),
                rainfall=("없음", "오류", "—"),
                humidity=("오류", "—", "62%"),
                directions=("알 수 없음", "?", "NW"),
                speeds=("오류", "없음", "2.5 m/s"),
            ), temperatures=("-2.5", "자료 없음", "0"))
            expected = base_rows()
            expected[0]["precipitation_probability"] = 0
            expected[1]["native_temperature"] = None
            expected[2].update(humidity=62.0, wind_bearing=315, wind_speed=2.5)
            assert rows == expected, rows
        """)

    def test_publication_nested_unicode_markup_rollover_and_invalid_labels(self) -> None:
        self._run_parser("""
            reference = datetime(2026, 1, 1, 0, 30, tzinfo=api.KST)
            soup = publication_soup(
                '<b>현재 및 1시간예보</b>&nbsp;발표시간 : <span>12.31. 23:45</span><br>'
                '<b>시간별예보</b> 발표시간 : 01.01. 00:00<br>'
                '<b>주간예보</b> 발표시간 : 12.30. 18:00'
            )
            assert api.parse_publication_times(soup, reference) == {
                "publicTimeC": "2025-12-31T23:45:00+09:00",
                "publicTimeH": "2026-01-01T00:00:00+09:00",
                "publicTimeW": "2025-12-30T18:00:00+09:00",
            }
            malformed = publication_soup(
                '현재 및 1시간예보 발표시간 : 02.31. 25:99<br>'
                '시간별예보 발표시간 : 01.01 00:15<br>주간예보 자료 없음'
            )
            assert api.parse_publication_times(malformed, reference) == {
                "publicTimeC": None,
                "publicTimeH": "2026-01-01T00:15:00+09:00",
                "publicTimeW": None,
            }
            empty = BeautifulSoup('<p class="desc">주간예보 01.01. 12:00</p>', "html.parser")
            assert api.parse_publication_times(empty, reference) == {
                "publicTimeC": None, "publicTimeH": None, "publicTimeW": None,
            }
        """)


if __name__ == "__main__":
    unittest.main()
