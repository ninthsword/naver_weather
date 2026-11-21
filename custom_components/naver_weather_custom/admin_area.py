"""Resolve an administrative area from the bundled offline SGIS boundaries."""

import math
import sqlite3
import struct
import zlib
from contextlib import closing
from pathlib import Path

_DATABASE = Path(__file__).resolve().with_name("admin_boundaries.sqlite3")
_FORMAT_VERSION = 1
_EDGE_MARGIN_METRES = 4
_LAT_METRES_PER_DEGREE = 110_500
_MAX_GEOMETRY_BYTES = 4 * 1024 * 1024
_RING_HEADER = struct.Struct("<Iii")
_DELTA = struct.Struct("<hh")


def location_coordinates(value: object) -> tuple[float, float] | None:
    """Read a finite WGS84 pair from the Companion sensor's Location attribute."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    latitude, longitude = value
    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None
    return float(latitude), float(longitude)


def _contains(
    blob: bytes, latitude: float, longitude: float, lon_metres: float
) -> bool | None:
    """Return containment, or None within the margin of any polygon edge."""
    stream = zlib.decompressobj()
    data = stream.decompress(blob, _MAX_GEOMETRY_BYTES)
    if not stream.eof or stream.unused_data or not data or data[0] not in (5, 6, 7):
        raise ValueError("Invalid boundary geometry")
    scale = 10 ** data[0]
    east = longitude * scale
    north = latitude * scale
    x_metres = lon_metres / scale
    y_metres = _LAT_METRES_PER_DEGREE / scale
    margin = _EDGE_MARGIN_METRES
    inside = False
    offset = 1
    if offset == len(data):
        raise ValueError("Empty boundary geometry")
    while offset < len(data):
        count, x, y = _RING_HEADER.unpack_from(data, offset)
        offset += _RING_HEADER.size
        end = offset + _DELTA.size * (count - 1)
        if count < 3 or end > len(data):
            raise ValueError("Invalid boundary ring")
        start_x = previous_x = (x - east) * x_metres
        start_y = previous_y = (y - north) * y_metres

        # A ray from the origin toggles containment on every crossing, including holes.
        for edge in range(count):
            if edge == count - 1:
                next_x, next_y = start_x, start_y
            else:
                dx, dy = _DELTA.unpack_from(data, offset)
                offset += _DELTA.size
                x += dx
                y += dy
                next_x = (x - east) * x_metres
                next_y = (y - north) * y_metres
            vx, vy = next_x - previous_x, next_y - previous_y
            if (previous_y > 0) != (next_y > 0) and previous_x - previous_y * vx / vy > 0:
                inside = not inside
            if (
                min(previous_x, next_x) <= margin and max(previous_x, next_x) >= -margin
                and min(previous_y, next_y) <= margin and max(previous_y, next_y) >= -margin
            ):
                length_squared = vx * vx + vy * vy
                fraction = -(previous_x * vx + previous_y * vy) / length_squared if length_squared else 0
                fraction = min(1, max(0, fraction))
                nearest_x = previous_x + fraction * vx
                nearest_y = previous_y + fraction * vy
                if nearest_x * nearest_x + nearest_y * nearest_y <= margin * margin:
                    return None
            previous_x, previous_y = next_x, next_y
    return inside


def resolve_admin_area(latitude: float, longitude: float) -> str | None:
    """Return the full official name only for a unique interior point."""
    coordinates = location_coordinates((latitude, longitude))
    if coordinates is None:
        return None
    latitude, longitude = coordinates
    lon_metres = 111_000 * math.cos(math.radians(latitude))
    dx = _EDGE_MARGIN_METRES / lon_metres
    dy = _EDGE_MARGIN_METRES / _LAT_METRES_PER_DEGREE
    match = None
    try:
        with closing(sqlite3.connect(_DATABASE.as_uri() + "?mode=ro&immutable=1", uri=True)) as database:
            if database.execute("PRAGMA user_version").fetchone() != (_FORMAT_VERSION,):
                return None
            for region, geometry in database.execute(
                """SELECT region, geometry FROM areas
                   WHERE min_lon <= ? AND max_lon >= ? AND min_lat <= ? AND max_lat >= ?""",
                (longitude + dx, longitude - dx, latitude + dy, latitude - dy),
            ):
                contains = _contains(geometry, latitude, longitude, lon_metres)
                if contains is None or (contains and match is not None):
                    return None
                if contains:
                    match = region
    except (sqlite3.Error, OSError, TypeError, ValueError, struct.error, zlib.error):
        return None
    return match
