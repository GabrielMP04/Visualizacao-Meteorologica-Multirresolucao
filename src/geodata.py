"""Leitura georreferenciada de relevo GeoTIFF e temperatura GRIB."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from pathlib import Path
from zipfile import BadZipFile

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.warp import Resampling, reproject, transform_bounds

from .dataset import MeteorologicalDataset, load_dataset, save_dataset


def to_celsius(values: np.ndarray, unit: str) -> np.ndarray:
    """A leitura GRIB usa NORMALIZE_UNITS=NO, evitando conversao implicita."""
    unit = unit.strip().strip("[]").lower()
    values = np.asarray(values, dtype=np.float32)
    if unit in {"k", "kelvin"}:
        return values - np.float32(273.15)
    if unit in {"c", "celsius", "degc", "\u00b0c"}:
        return values
    raise ValueError(f"Unidade de temperatura nao suportada: {unit!r}")


def _resample(
    source, band: int, size: int, target_transform, target_crs,
    *, values: np.ndarray | None = None,
) -> np.ndarray:
    destination = np.full((size, size), np.nan, dtype=np.float32)
    reproject(
        source=rasterio.band(source, band) if values is None else values,
        src_transform=source.transform,
        src_crs=source.crs,
        destination=destination,
        src_nodata=source.nodata if values is None else None,
        dst_transform=target_transform,
        dst_crs=target_crs,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    if not np.isfinite(destination).all():
        raise ValueError(
            f"{Path(source.name).name}: existem lacunas/NoData ou "
            "a cobertura geografica nao inclui todo o terreno."
        )
    return destination


def _mean_temperature(source) -> tuple[np.ndarray, dict]:
    total = np.zeros(source.shape, dtype=np.float64)
    timestamps = []
    count = 0
    for band in source.indexes:
        tags = source.tags(band)
        element = tags.get("GRIB_ELEMENT", "").upper()
        level = tags.get("GRIB_SHORT_NAME", "")
        if element not in {"2T", "T2M"} and not (
            element in {"T", "TMP"} and level == "2-HTGL"
        ):
            continue
        raw = source.read(band, masked=True).astype(np.float32).filled(np.nan)
        values = to_celsius(raw, tags.get("GRIB_UNIT", ""))
        if not np.isfinite(values).all():
            raise ValueError(f"GRIB: a banda {band} contem NoData ou temperaturas invalidas.")
        total += values
        count += 1
        if timestamp := tags.get("GRIB_VALID_TIME"):
            timestamps.append(int(timestamp.split()[0]))
    if not count:
        raise ValueError("O GRIB nao contem bandas de temperatura do ar a 2 metros.")
    metadata = {
        "temperature_sample_count": count,
        "temperature_source_shape": [source.height, source.width],
    }
    if len(timestamps) == count:
        metadata["temperature_period_utc"] = [
            datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            for t in (min(timestamps), max(timestamps))
        ]
    return (total / count).astype(np.float32), metadata


def import_georeferenced(
    height_path: str | Path,
    temperature_path: str | Path,
    size: int = 513,
) -> MeteorologicalDataset:
    if size < 3:
        raise ValueError("A grade precisa ter pelo menos 3 x 3 amostras.")
    height_path, temperature_path = Path(height_path), Path(temperature_path)
    with rasterio.open(height_path) as height:
        if height.crs is None:
            raise ValueError("O GeoTIFF nao possui CRS; nao e possivel alinhar o GRIB.")
        if height.transform.b != 0 or height.transform.d != 0:
            raise ValueError("O GeoTIFF deve estar orientado ao norte, sem rotacao.")
        if height.transform.a <= 0 or height.transform.e >= 0:
            raise ValueError("O GeoTIFF deve ter colunas oeste-leste e linhas norte-sul.")
        # Os vertices extremos coincidem com os centros das amostras extremas
        # do DEM (neste SRTM: -48/-47 longitude, -22/-23 latitude).
        west = height.transform.c + 0.5 * height.transform.a
        north = height.transform.f + 0.5 * height.transform.e
        east = height.transform.c + (height.width - 0.5) * height.transform.a
        south = height.transform.f + (height.height - 0.5) * height.transform.e
        dx, dy = (east - west) / (size - 1), (south - north) / (size - 1)
        target_transform = Affine(dx, 0, west - dx / 2, 0, dy, north - dy / 2)
        elevation_m = _resample(height, 1, size, target_transform, height.crs)
        # Aplicar scale/offset declarados pelo raster, preservando altitude fisica.
        elevation_m = elevation_m * height.scales[0] + height.offsets[0]
        bounds = transform_bounds(height.crs, "EPSG:4326", west, south, east, north)
        west_deg, south_deg, east_deg, north_deg = bounds
        mean_lat = math.radians((south_deg + north_deg) / 2)
        width_m = math.radians(east_deg - west_deg) * 6371000 * math.cos(mean_lat)
        depth_m = math.radians(north_deg - south_deg) * 6371000
        low, high = float(elevation_m.min()), float(elevation_m.max())
        metadata = {
            "height_source": height_path.name,
            "temperature_source": temperature_path.name,
            "height_source_shape": [height.height, height.width],
            "crs": height.crs.to_string(),
            "transform": list(target_transform)[:6],
            "bounds_wgs84": list(bounds),
            "width_m": width_m,
            "depth_m": depth_m,
            "elevation_min_m": low,
            "elevation_max_m": high,
            "orientation": "columns west-east; rows north-south",
        }

    with rasterio.Env(GRIB_NORMALIZE_UNITS="NO", GRIB_ADJUST_LONGITUDE_RANGE="YES"):
        with rasterio.open(temperature_path) as source:
            if source.crs is None:
                raise ValueError("O arquivo de temperatura nao possui CRS.")
            mean, temperature_metadata = _mean_temperature(source)
            temperature_c = _resample(
                source, 1, size, target_transform, metadata["crs"], values=mean,
            )
    metadata.update(temperature_metadata)
    normalized = (elevation_m - low) / (high - low) if high > low else np.zeros_like(elevation_m)
    dataset = MeteorologicalDataset(
        elevation=normalized.astype(np.float32),
        temperature=temperature_c,
        metadata=metadata,
    )
    dataset.validate()
    return dataset


def load_configured_dataset(project_dir: Path, terrain: dict) -> MeteorologicalDataset:
    """Modo real nunca recorre silenciosamente a dados sinteticos."""
    if terrain.get("source") == "state":
        from .state_data import load_state
        return load_state(project_dir, terrain)
    mode = terrain.get("source", "npz")
    destination = project_dir / terrain["dataset"]
    if mode == "synthetic":
        from .dataset import load_or_create
        return load_or_create(destination, int(terrain["grid_size"]), int(terrain.get("seed", 113142)))
    if mode == "npz":
        return load_dataset(destination)
    if mode != "georeferenced":
        raise ValueError(f"terrain.source desconhecido: {mode}")

    height = project_dir / terrain["heightmap"]
    temperature = project_dir / terrain["temperature_file"]
    size = int(terrain["grid_size"])
    fingerprint = {"version": 2, "size": size, "sources": []}
    for source in (height, temperature):
        if not source.is_file():
            raise FileNotFoundError(f"Arquivo de dados reais nao encontrado: {source}")
        stat = source.stat()
        fingerprint["sources"].append([str(source.resolve()), stat.st_size, stat.st_mtime_ns])
    if destination.is_file():
        try:
            cached = load_dataset(destination)
            if cached.metadata.get("fingerprint") == fingerprint:
                return cached
        except (ValueError, OSError, EOFError, BadZipFile):
            pass  # Cache incompleto ou antigo: reconstruir usando os originais.
    dataset = import_georeferenced(height, temperature, size)
    dataset.metadata["fingerprint"] = fingerprint
    save_dataset(dataset, destination)
    return dataset
