"""Exercise the offline administrative geometry and the bundled SGIS data."""

import importlib.util
import sqlite3
import struct
import tempfile
import unittest
import zlib
from contextlib import closing
from itertools import pairwise
from pathlib import Path
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "naver_weather_custom"
SPEC = importlib.util.spec_from_file_location("isolated_admin_area", COMPONENT / "admin_area.py")
assert SPEC is not None and SPEC.loader is not None
admin_area = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admin_area)


def _square(west, south, east, north):
    return ((west, south), (east, south), (east, north), (west, north))


def _geometry(*rings):
    data = bytearray([5])
    for ring in rings:
        data.extend(struct.pack("<Iii", len(ring), *ring[0]))
        for (x, y), (next_x, next_y) in pairwise(ring):
            data.extend(struct.pack("<hh", next_x - x, next_y - y))
    return zlib.compress(data)


class AdminAreaTest(unittest.TestCase):
    def test_bundled_database_has_all_areas_and_resolves_public_eungam_points(self):
        uri = (COMPONENT / "admin_boundaries.sqlite3").as_uri()
        with closing(sqlite3.connect(uri + "?mode=ro", uri=True)) as database:
            self.assertEqual(
                database.execute("SELECT count(*), count(DISTINCT code) FROM areas").fetchone(),
                (3559, 3559),
            )
            self.assertEqual(
                [row[1] for row in database.execute("PRAGMA table_info(areas)") if row[5]],
                ["code"],
            )
        for number, coordinates in enumerate(
            ((37.60069, 126.92676), (37.59460, 126.92307), (37.59223, 126.91573)), start=1
        ):
            with self.subTest(number=number):
                self.assertEqual(
                    admin_area.resolve_admin_area(*coordinates),
                    f"서울특별시 은평구 응암{number}동",
                )

    def test_location_pair_rejects_invalid_and_unsupported_inputs(self):
        for value in (
            None, {"latitude": 37, "longitude": 127}, "37,127", [], [37],
            [37, 127, 0], ["37", 127], [37, None], [True, 127], [37, False],
            [float("nan"), 127], [37, float("inf")], [-91, 127], [37, -181],
            [10 ** 1000, 127],
        ):
            with self.subTest(value=value):
                self.assertIsNone(admin_area.location_coordinates(value))
        self.assertEqual(admin_area.location_coordinates([37, 127.5]), (37.0, 127.5))
        self.assertEqual(admin_area.location_coordinates((-90, 180)), (-90.0, 180.0))
        for coordinates in ((True, 127), (float("nan"), 127), (0, 0), (90, 180)):
            with self.subTest(coordinates=coordinates):
                self.assertIsNone(admin_area.resolve_admin_area(*coordinates))

    def test_shared_edges_holes_and_overlap_leave_no_match(self):
        x, y = 12_700_000, 3_700_000
        outer = _square(x, y, x + 100, y + 100)
        hole = _square(x + 30, y + 30, x + 70, y + 70)
        island = _square(x + 120, y, x + 140, y + 20)
        neighbor = _square(x - 100, y, x, y + 100)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.sqlite3"
            with closing(sqlite3.connect(path)) as database, database:
                database.execute("PRAGMA user_version = 1")
                database.execute(
                    "CREATE TABLE areas (region, min_lon, min_lat, max_lon, max_lat, geometry)"
                )
                database.executemany(
                    "INSERT INTO areas VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        ("첫동", 127.0, 37.0, 127.0014, 37.001, _geometry(outer, hole, island)),
                        ("이웃동", 126.999, 37.0, 127.0, 37.001, _geometry(neighbor)),
                        ("겹친동", 127.0008, 37.0001, 127.00095, 37.0003,
                         _geometry(_square(x + 80, y + 10, x + 95, y + 30))),
                    ],
                )
            with patch.object(admin_area, "_DATABASE", path):
                for latitude, longitude, expected in (
                    (37.00020, 127.00010, "첫동"),
                    (37.00050, 127.00000, None),  # Shared edge.
                    (37.00050, 127.000044, None),  # About 3.90 m inside, below 4 m.
                    (37.00050, 127.000046, "첫동"),  # About 4.08 m inside.
                    (37.00050, 126.999954, "이웃동"),
                    (37.00050, 127.00050, None),  # Hole interior.
                    (37.00050, 127.00029, None),  # Near the hole from outside.
                    (37.00010, 127.00130, "첫동"),  # Disconnected island.
                    (37.00020, 127.00088, None),  # Two containing areas.
                ):
                    with self.subTest(latitude=latitude, longitude=longitude):
                        self.assertEqual(admin_area.resolve_admin_area(latitude, longitude), expected)

    def test_unavailable_or_corrupt_database_returns_no_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.sqlite3"
            with patch.object(admin_area, "_DATABASE", path):
                self.assertIsNone(admin_area.resolve_admin_area(37.6, 126.9))
                self.assertFalse(path.exists())
                path.write_bytes(b"not a database")
                self.assertIsNone(admin_area.resolve_admin_area(37.6, 126.9))
                path.unlink()
                with closing(sqlite3.connect(path)) as database, database:
                    database.execute("PRAGMA user_version = 1")
                    database.execute(
                        "CREATE TABLE areas (region, min_lon, min_lat, max_lon, max_lat, geometry)"
                    )
                    database.execute(
                        "INSERT INTO areas VALUES (?, ?, ?, ?, ?, ?)",
                        ("가상동", 126.0, 37.0, 128.0, 38.0, b"corrupt blob"),
                    )
                self.assertIsNone(admin_area.resolve_admin_area(37.6, 126.9))
