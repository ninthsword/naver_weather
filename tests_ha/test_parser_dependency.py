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
