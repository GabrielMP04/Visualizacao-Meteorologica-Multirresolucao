"""Geracao, importacao e armazenamento dos campos meteorologicos."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import numpy as np


@dataclass(frozen=True)
class MeteorologicalDataset:
    elevation: np.ndarray
    temperature: np.ndarray
    metadata: dict = field(default_factory=dict)

    def validate(self) -> None:
        if self.elevation.ndim != 2 or self.temperature.ndim != 2:
            raise ValueError("elevation e temperature devem ser matrizes 2D")
        if self.elevation.shape != self.temperature.shape:
            raise ValueError("elevation e temperature devem possuir o mesmo tamanho")
        if self.elevation.shape[0] != self.elevation.shape[1]:
            raise ValueError("a grade deve ser quadrada")
        if self.elevation.shape[0] < 3:
            raise ValueError("a grade precisa ter pelo menos 3 x 3 amostras")
        if not np.isfinite(self.elevation).all() or not np.isfinite(self.temperature).all():
            raise ValueError("o conjunto de dados contem valores invalidos")


def generate_fields(size: int = 257, seed: int = 113142) -> MeteorologicalDataset:
    if size < 3:
        raise ValueError("size deve ser maior ou igual a 3")
    rng = np.random.default_rng(seed)
    z, x = np.mgrid[0:size, 0:size]
    xn = x.astype(np.float32) / float(size - 1)
    zn = z.astype(np.float32) / float(size - 1)

    elevation = (
        0.70 * np.exp(-((xn - 0.30) ** 2 / 0.030 + (zn - 0.38) ** 2 / 0.060))
        + 0.52 * np.exp(-((xn - 0.73) ** 2 / 0.052 + (zn - 0.66) ** 2 / 0.030))
        + 0.13 * np.sin(3.2 * np.pi * xn) * np.cos(2.4 * np.pi * zn)
        + 0.08 * np.sin(7.0 * np.pi * (xn + 0.35 * zn))
    )
    noise = rng.normal(0.0, 1.0, elevation.shape).astype(np.float32)
    for _ in range(7):
        noise = (
            noise
            + np.roll(noise, 1, axis=0)
            + np.roll(noise, -1, axis=0)
            + np.roll(noise, 1, axis=1)
            + np.roll(noise, -1, axis=1)
        ) / 5.0
    elevation = elevation + 0.025 * noise
    elevation -= elevation.min()
    maximum = float(elevation.max())
    if maximum > 0:
        elevation /= maximum

    warm_anomaly = np.exp(-((xn - 0.77) ** 2 + (zn - 0.25) ** 2) / 0.018)
    cold_anomaly = np.exp(-((xn - 0.24) ** 2 + (zn - 0.78) ** 2) / 0.025)
    temperature = (
        31.0
        - 9.5 * elevation
        - 7.0 * zn
        + 6.5 * warm_anomaly
        - 3.2 * cold_anomaly
        + 1.4 * np.sin(4.0 * np.pi * xn + 1.2 * zn)
    )

    dataset = MeteorologicalDataset(
        elevation=np.asarray(elevation, dtype=np.float32),
        temperature=np.asarray(temperature, dtype=np.float32),
    )
    dataset.validate()
    return dataset


def save_dataset(dataset: MeteorologicalDataset, path: str | Path) -> Path:
    dataset.validate()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        elevation=dataset.elevation.astype(np.float32),
        temperature=dataset.temperature.astype(np.float32),
        metadata=np.array(json.dumps(dataset.metadata, ensure_ascii=True)),
    )
    return destination


def load_dataset(path: str | Path) -> MeteorologicalDataset:
    source = Path(path)
    with source.open("rb") as handle, np.load(handle, allow_pickle=False) as data:
        if "elevation" not in data or "temperature" not in data:
            raise ValueError("o arquivo NPZ precisa conter elevation e temperature")
        dataset = MeteorologicalDataset(
            elevation=np.asarray(data["elevation"], dtype=np.float32),
            temperature=np.asarray(data["temperature"], dtype=np.float32),
            metadata=json.loads(str(data["metadata"].item())) if "metadata" in data else {},
        )
    dataset.validate()
    return dataset


def load_or_create(path: str | Path, size: int, seed: int) -> MeteorologicalDataset:
    source = Path(path)
    if source.is_file():
        return load_dataset(source)
    dataset = generate_fields(size=size, seed=seed)
    save_dataset(dataset, source)
    return dataset

