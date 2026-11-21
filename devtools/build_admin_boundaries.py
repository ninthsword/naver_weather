"""Build the bundled boundary database offline from the June 2025 SGIS release."""

import argparse
import hashlib
import io
import sqlite3
import struct
import tempfile
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import numpy as np
import pyproj
import shapefile
import shapely
from numpy.typing import NDArray
from pyproj.network import (
    set_network_enabled,  # pyright: ignore[reportPrivateImportUsage]
)
from shapely.geometry import MultiPolygon, Polygon, shape

_ARCHIVE_BYTES = 269_032_521
_ARCHIVE_SHA256 = "f1cf0f9de453ac7eaacb273f39cee52851183372b9ddfda428a967c3a670b2c6"
_SIMPLIFY_METRES = 2


def _reader(bundle: zipfile.ZipFile, layer: str, *, geometry: bool = False) -> shapefile.Reader:
    """Open only the required files from the release archive."""
    stem = f"bnd_{layer}_00_2025_2Q"
    members = {Path(member).name: member for member in bundle.namelist()}
    dbf = io.BytesIO(bundle.read(members[f"{stem}.dbf"]))
    if geometry:
        shp = io.BytesIO(bundle.read(members[f"{stem}.shp"]))
        return shapefile.Reader(shp=shp, dbf=dbf, encoding="utf-8")
    return shapefile.Reader(dbf=dbf, encoding="utf-8")


def _names(bundle: zipfile.ZipFile, layer: str) -> dict[str, str]:
    with _reader(bundle, layer) as reader:
        return {row[f"{layer.upper()}_CD"]: row[f"{layer.upper()}_NM"] for row in reader.records()}


def _geometry(
    boundary: Polygon | MultiPolygon, transformer: pyproj.Transformer
) -> tuple[bytes, tuple[float, float, float, float]]:
    """Encode quantized WGS84 rings as compressed starting points and signed deltas."""
    def to_wgs84(coordinates: NDArray[np.float64]) -> NDArray[np.float64]:
        longitude, latitude = transformer.transform(coordinates[:, 0], coordinates[:, 1])
        return np.column_stack((longitude, latitude))

    simplified = boundary.simplify(_SIMPLIFY_METRES, preserve_topology=True)
    for precision in (5, 6, 7):
        scale = 10 ** precision
        # Densify long projected lines before converting their vertices to WGS84.
        projected = simplified.segmentize(100 if precision == 7 else 1_000)
        wgs84 = shapely.transform(projected, to_wgs84)
        quantized = shapely.transform(wgs84, lambda coordinates, scale=scale: np.rint(coordinates * scale))
        if not isinstance(quantized, (MultiPolygon, Polygon)) or not quantized.is_valid:
            continue
        polygons = quantized.geoms if isinstance(quantized, MultiPolygon) else (quantized,)
        data = bytearray([precision])
        for polygon in polygons:
            for ring in (polygon.exterior, *polygon.interiors):
                points = np.asarray(ring.coords, dtype=np.int32)
                differences = np.diff(points, axis=0)[:-1]
                differences = differences[np.any(differences != 0, axis=1)]
                if differences.min() < -32768 or differences.max() > 32767:
                    raise ValueError("Boundary delta outside its integer range")
                data.extend(struct.pack("<Iii", len(differences) + 1, *points[0]))
                data.extend(differences.astype("<i2").tobytes())
        west, south, east, north = quantized.bounds
        return zlib.compress(data, level=9), (west / scale, south / scale, east / scale, north / scale)
    raise ValueError("Quantization changed boundary topology")


def _rows(bundle: zipfile.ZipFile) -> Iterator[tuple[str, str, float, float, float, float, bytes]]:
    province, district = _names(bundle, "sido"), _names(bundle, "sigungu")
    transformer = pyproj.Transformer.from_crs(5179, 4326, always_xy=True)
    with _reader(bundle, "dong", geometry=True) as reader:
        records = []
        for row in reader.iterShapeRecords():
            if row.record is None or row.shape is None:
                raise ValueError("SGIS area without a record or boundary")
            records.append((row.record["ADM_CD"], row.record["ADM_NM"], row.shape))
    if len(records) != 3559:
        raise ValueError("Unexpected number of SGIS areas")
    for code, name, stored_shape in sorted(records, key=lambda row: row[0]):
        region = f"{province[code[:2]]} {district[code[:5]]} {name}"
        boundary = shape(stored_shape.__geo_interface__)
        if not isinstance(boundary, (Polygon, MultiPolygon)) or not boundary.is_valid:
            raise ValueError(f"Invalid SGIS polygon for {code}")
        geometry, bounds = _geometry(boundary, transformer)
        yield code, region, *bounds, geometry


def _write_database(bundle: zipfile.ZipFile, destination: Path) -> None:
    """Build the database in a transaction and replace the destination on success."""
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        output = Path(temporary) / destination.name
        with closing(sqlite3.connect(output)) as database, database:
            database.execute("PRAGMA page_size = 1024")
            database.execute("PRAGMA user_version = 1")
            database.execute(
                """CREATE TABLE areas (
                    code TEXT NOT NULL PRIMARY KEY,
                    region TEXT NOT NULL,
                    min_lon REAL NOT NULL, min_lat REAL NOT NULL,
                    max_lon REAL NOT NULL, max_lat REAL NOT NULL,
                    geometry BLOB NOT NULL
                )"""
            )
            database.executemany("INSERT INTO areas VALUES (?, ?, ?, ?, ?, ?, ?)", _rows(bundle))
        output.replace(destination)


def main() -> None:
    """Convert the exact published SGIS archive to a reproducible SQLite file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryFile() as snapshot:
        remaining = _ARCHIVE_BYTES
        with args.archive.open("rb") as stream:
            while chunk := stream.read(min(1024 * 1024, remaining + 1)):
                if len(chunk) > remaining:
                    parser.error("Unexpected SGIS archive size")
                snapshot.write(chunk)
                remaining -= len(chunk)
        if remaining:
            parser.error("Unexpected SGIS archive size")
        snapshot.seek(0)
        if hashlib.file_digest(snapshot, "sha256").hexdigest() != _ARCHIVE_SHA256:
            parser.error("Unexpected SGIS archive SHA256")
        snapshot.seek(0)
        # PyProj's public network module re-exports this function from its extension.
        set_network_enabled(False)
        with zipfile.ZipFile(snapshot) as bundle:
            _write_database(bundle, args.output)


if __name__ == "__main__":
    main()
