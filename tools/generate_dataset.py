"""Gera o conjunto sintetico usado pela demonstracao."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.dataset import generate_fields, save_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gerar heightmap e temperatura sinteticos")
    parser.add_argument("--size", type=int, default=257, help="lado da grade")
    parser.add_argument("--seed", type=int, default=113142, help="semente aleatoria")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_DIR / "data" / "meteorologia_sintetica.npz",
        help="arquivo NPZ de destino",
    )
    args = parser.parse_args()
    dataset = generate_fields(args.size, args.seed)
    destination = save_dataset(dataset, args.output)
    print(f"Dados gerados: {destination}")
    print(f"Grade: {dataset.elevation.shape[0]} x {dataset.elevation.shape[1]}")
    print(
        f"Temperatura: {dataset.temperature.min():.2f} a "
        f"{dataset.temperature.max():.2f} graus C"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
