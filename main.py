"""Ponto de entrada da visualizacao meteorologica em OpenGL."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualizacao meteorologica com heightmap, patches e LOD em OpenGL"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_DIR / "config.json",
        help="arquivo JSON de configuracao",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="executa comparacao automatica sem LOD e com LOD",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=12.0,
        help="duracao de cada modo no benchmark",
    )
    parser.add_argument(
        "--no-vsync",
        action="store_true",
        help="desativa sincronizacao vertical",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from src.application import MeteorologicalApp

        app = MeteorologicalApp(
            project_dir=PROJECT_DIR,
            config_path=args.config,
            benchmark=args.benchmark,
            benchmark_seconds=max(2.0, args.seconds),
            force_no_vsync=args.no_vsync,
        )
        app.run()
        return 0
    except ModuleNotFoundError as exc:
        missing = exc.name or "uma dependencia"
        print(f"\nBiblioteca ausente: {missing}")
        print("Execute instalar_windows.bat antes de iniciar o projeto.\n")
        return 1
    except RuntimeError as exc:
        print(f"\nFalha ao iniciar: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

