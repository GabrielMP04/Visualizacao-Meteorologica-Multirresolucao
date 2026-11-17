"""Gera novamente o grafico de um resumo de benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.charts import create_comparison_chart  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gerar grafico do benchmark")
    parser.add_argument("summary", type=Path, help="arquivo *_resumo.csv")
    parser.add_argument("--output", type=Path, help="PNG de destino")
    args = parser.parse_args()
    destination = create_comparison_chart(args.summary, args.output)
    print(f"Grafico gerado: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
