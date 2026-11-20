"""Ponto de entrada da visualizacao meteorologica em OpenGL."""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


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
    parser.add_argument("--prepare-data", action="store_true", help="importa e valida os dados sem abrir a janela")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.prepare_data:
            import json
            from src.geodata import load_configured_dataset

            config_path = PROJECT_DIR / args.config
            terrain = json.loads(config_path.read_text(encoding="utf-8"))["terrain"]
            dataset = load_configured_dataset(PROJECT_DIR, terrain)
            print(f"Dados prontos | grade {dataset.elevation.shape}")
            if "weather" in dataset.metadata:
                weather = dataset.metadata["weather"]
                print(f"{len(weather.times)} horarios UTC: {weather.labels[0]} a {weather.labels[-1]}")
            else:
                print(f"Temperatura no mapa: {dataset.temperature.min():.2f} a {dataset.temperature.max():.2f} C")
            if count := dataset.metadata.get("temperature_sample_count"):
                period = " a ".join(dataset.metadata.get("temperature_period_utc", []))
                print(f"Media por localizacao de {count} amostras | {period}")
            return 0

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
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"\nFalha ao iniciar: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

