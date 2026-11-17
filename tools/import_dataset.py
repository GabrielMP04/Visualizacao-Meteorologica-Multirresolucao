"""Converte heightmaps e campos de temperatura externos para o projeto."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.dataset import MeteorologicalDataset, save_dataset  # noqa: E402


def read_matrix(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        matrix = np.load(path, allow_pickle=False)
    elif suffix in {".csv", ".txt"}:
        delimiter = "," if suffix == ".csv" else None
        matrix = np.loadtxt(path, delimiter=delimiter)
    else:
        with Image.open(path) as image:
            matrix = np.asarray(image.convert("F"), dtype=np.float32)
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError(f"{path} nao representa uma matriz 2D")
    if not np.isfinite(matrix).all():
        raise ValueError(f"{path} contem valores invalidos")
    return matrix


def resize_matrix(matrix: np.ndarray, size: int) -> np.ndarray:
    if matrix.shape == (size, size):
        return matrix.astype(np.float32, copy=False)
    image = Image.fromarray(matrix.astype(np.float32), mode="F")
    resized = image.resize((size, size), resample=Image.Resampling.BILINEAR)
    return np.asarray(resized, dtype=np.float32)


def normalize(matrix: np.ndarray) -> np.ndarray:
    minimum = float(matrix.min())
    maximum = float(matrix.max())
    if maximum - minimum < 1e-8:
        return np.zeros_like(matrix, dtype=np.float32)
    return ((matrix - minimum) / (maximum - minimum)).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importar um heightmap e, opcionalmente, um campo de temperatura"
    )
    parser.add_argument("--height", type=Path, required=True, help="PNG/JPG/TIF/NPY/CSV")
    parser.add_argument("--temperature", type=Path, help="PNG/JPG/TIF/NPY/CSV opcional")
    parser.add_argument("--size", type=int, default=257, help="lado da grade de saida")
    parser.add_argument("--temperature-min", type=float, default=8.0)
    parser.add_argument("--temperature-max", type=float, default=36.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_DIR / "data" / "meteorologia_importada.npz",
    )
    args = parser.parse_args()
    if args.size < 3:
        raise ValueError("--size deve ser pelo menos 3")

    elevation = normalize(resize_matrix(read_matrix(args.height), args.size))
    if args.temperature is None:
        # Campo plausivel para demonstracao: a temperatura cai com a altitude.
        temperature = 31.0 - 14.0 * elevation
    else:
        raw_temperature = resize_matrix(read_matrix(args.temperature), args.size)
        scaled = normalize(raw_temperature)
        temperature = args.temperature_min + scaled * (
            args.temperature_max - args.temperature_min
        )

    dataset = MeteorologicalDataset(
        elevation=elevation.astype(np.float32),
        temperature=np.asarray(temperature, dtype=np.float32),
    )
    destination = save_dataset(dataset, args.output)
    print(f"Dados importados: {destination}")
    print(f"Grade: {args.size} x {args.size}")
    print("Atualize terrain.dataset em config.json para usar este arquivo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
