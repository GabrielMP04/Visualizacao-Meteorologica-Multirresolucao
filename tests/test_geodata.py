"""Regressoes de coordenadas, unidades, cache e dados reais."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rasterio
from rasterio.transform import from_origin

from src.dataset import MeteorologicalDataset, generate_fields, load_dataset, save_dataset
from src.geodata import (
    _resample, import_georeferenced, load_configured_dataset, to_celsius,
)

ROOT = Path(__file__).resolve().parents[1]


class GeodataTests(unittest.TestCase):
    def test_kelvin_conversion_without_normalizing_physical_values(self):
        values = np.array([[273.15, 293.15, 303.15]], dtype=np.float32)
        np.testing.assert_allclose(to_celsius(values, "[K]"), [[0, 20, 30]], atol=0.0001)
        np.testing.assert_array_equal(to_celsius(values, "[C]"), values)
        with self.assertRaisesRegex(ValueError, "Unidade"):
            to_celsius(values, "[m]")

    def test_geographic_alignment_orientation_and_nodata(self):
        # Campo analitico: interpolar o centro deve resultar em 11, e nao
        # inverter norte/sul nem apenas esticar toda a imagem para o recorte.
        with rasterio.io.MemoryFile() as memory:
            with memory.open(
                driver="GTiff", width=3, height=3, count=1, dtype="float32",
                crs="EPSG:4326", transform=from_origin(-48.5, -21.5, 1, 1),
                nodata=-9999,
            ) as source:
                source.write(np.array([[0, 1, 2], [10, 11, 12], [20, 21, 22]], dtype=np.float32), 1)
                target = from_origin(-47.75, -22.25, 0.5, 0.5)
                actual = _resample(source, 1, 3, target, source.crs)
                np.testing.assert_allclose(actual, [[5.5, 6, 6.5], [10.5, 11, 11.5], [15.5, 16, 16.5]])
                with self.assertRaisesRegex(ValueError, "cobertura"):
                    _resample(source, 1, 3, from_origin(10, 10, 0.1, 0.1), source.crs)
                source.write(np.full((3, 3), -9999, dtype=np.float32), 1)
                with self.assertRaisesRegex(ValueError, "NoData"):
                    _resample(source, 1, 3, target, source.crs)

    def test_metadata_roundtrip_and_legacy_npz(self):
        original = generate_fields(9)
        data = MeteorologicalDataset(original.elevation, original.temperature, {"valid_time": "2026-11-01 00:00 UTC"})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.npz"
            save_dataset(data, path)
            self.assertEqual(load_dataset(path).metadata, data.metadata)
            np.savez(path, elevation=original.elevation, temperature=original.temperature)
            self.assertEqual(load_dataset(path).metadata, {})

    def test_missing_real_source_never_generates_synthetic(self):
        config = {
            "source": "georeferenced", "dataset": "cache.npz", "grid_size": 33,
            "heightmap": "missing.tif", "temperature_file": "missing.grib",
        }
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                load_configured_dataset(Path(folder), config)
            self.assertFalse((Path(folder) / "cache.npz").exists())


@unittest.skipUnless(
    (ROOT / "data/S23W048.tif").exists() and list((ROOT / "data").glob("*.grib")),
    "Arquivos reais locais nao disponiveis",
)
class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.height = ROOT / "data/S23W048.tif"
        cls.grib = next((ROOT / "data").glob("*.grib"))
        cls.data = import_georeferenced(cls.height, cls.grib, size=33)

    def test_sources_time_and_units(self):
        data = self.data
        data.validate()
        self.assertEqual(data.metadata["height_source_shape"], [3601, 3601])
        self.assertEqual(data.metadata["temperature_source_shape"], [11, 11])
        self.assertEqual(data.metadata["temperature_sample_count"], 288)
        self.assertEqual(data.metadata["temperature_period_utc"], ["2026-11-01 00:00 UTC", "2026-11-12 23:00 UTC"])
        np.testing.assert_allclose(data.metadata["bounds_wgs84"], [-48, -23, -47, -22])
        self.assertGreater(float(data.temperature.min()), 19)
        self.assertLess(float(data.temperature.max()), 24)
        self.assertGreater(data.metadata["depth_m"], data.metadata["width_m"])
        self.assertGreaterEqual(float(data.elevation.min()), 0)
        self.assertLessEqual(float(data.elevation.max()), 1)

    def test_mean_matches_original_grib_nodes(self):
        with rasterio.Env(GRIB_NORMALIZE_UNITS="NO"):
            with rasterio.open(self.grib) as source:
                records = source.read()
        expected = np.mean(records, axis=0, dtype=np.float64) - 273.15
        for target, origin in [(0, 0), (16, 5), (32, 10)]:
            self.assertAlmostEqual(float(self.data.temperature[target, target]), float(expected[origin, origin]), places=3)
        self.assertFalse(np.allclose(self.data.temperature, self.data.temperature.mean()))

    def test_cache_reuse_and_invalidation(self):
        with tempfile.TemporaryDirectory() as folder:
            config = {
                "source": "georeferenced", "dataset": "cache.npz", "grid_size": 33,
                "heightmap": str(self.height), "temperature_file": str(self.grib),
            }
            first = load_configured_dataset(Path(folder), config)
            with patch("src.geodata.import_georeferenced", side_effect=AssertionError("cache ignorado")):
                second = load_configured_dataset(Path(folder), config)
            np.testing.assert_array_equal(first.temperature, second.temperature)
            config["grid_size"] = 17
            self.assertEqual(load_configured_dataset(Path(folder), config).elevation.shape, (17, 17))
            cache_path = Path(folder) / "cache.npz"
            cache_path.write_bytes(cache_path.read_bytes()[:100])
            self.assertEqual(load_configured_dataset(Path(folder), config).elevation.shape, (17, 17))


if __name__ == "__main__":
    unittest.main()
