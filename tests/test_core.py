"""Testes das partes independentes da janela OpenGL."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.dataset import generate_fields, load_dataset, save_dataset
from src.math3d import look_at, perspective
from src.terrain_cpu import TerrainCPU, choose_lod, compute_normals


class DatasetTests(unittest.TestCase):
    def test_generation_is_deterministic_and_valid(self) -> None:
        first = generate_fields(33, seed=42)
        second = generate_fields(33, seed=42)
        first.validate()
        np.testing.assert_allclose(first.elevation, second.elevation)
        np.testing.assert_allclose(first.temperature, second.temperature)
        self.assertGreaterEqual(float(first.elevation.min()), 0.0)
        self.assertLessEqual(float(first.elevation.max()), 1.0)

    def test_npz_round_trip(self) -> None:
        dataset = generate_fields(17, seed=9)
        with tempfile.TemporaryDirectory() as folder:
            path = save_dataset(dataset, Path(folder) / "sample.npz")
            loaded = load_dataset(path)
        np.testing.assert_array_equal(dataset.elevation, loaded.elevation)
        np.testing.assert_array_equal(dataset.temperature, loaded.temperature)


class TerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.terrain = TerrainCPU(
            generate_fields(65, seed=5),
            world_size=64.0,
            vertical_scale=12.0,
            patch_size=16,
            lod_strides=[1, 2, 4, 8],
            lod_distances=[20.0, 40.0, 60.0],
            skirt_depth=2.0,
        )

    def test_patch_and_triangle_counts(self) -> None:
        self.assertEqual(len(self.terrain.patches), 16)
        patch = self.terrain.patches[0]
        self.assertEqual(patch.vertices.shape, (357, 7))
        self.assertEqual(patch.triangle_counts, (640, 192, 64, 24))

    def test_lod_reduces_geometry(self) -> None:
        detailed = tuple(0 for _ in self.terrain.patches)
        coarse = tuple(3 for _ in self.terrain.patches)
        detailed_triangles, _ = self.terrain.triangle_summary(detailed)
        coarse_triangles, _ = self.terrain.triangle_summary(coarse)
        self.assertEqual(detailed_triangles, 10240)
        self.assertLess(coarse_triangles, detailed_triangles)

    def test_lod_thresholds(self) -> None:
        thresholds = (20.0, 40.0, 60.0)
        self.assertEqual(choose_lod(0.0, thresholds, 4), 0)
        self.assertEqual(choose_lod(20.0, thresholds, 4), 1)
        self.assertEqual(choose_lod(45.0, thresholds, 4), 2)
        self.assertEqual(choose_lod(999.0, thresholds, 4), 3)

    def test_flat_normals_point_up(self) -> None:
        normals = compute_normals(np.zeros((9, 9), dtype=np.float32), 1.0)
        expected = np.zeros_like(normals)
        expected[:, :, 1] = 1.0
        np.testing.assert_allclose(normals, expected)


class MatrixTests(unittest.TestCase):
    def test_projection_and_view_are_finite(self) -> None:
        projection = perspective(60.0, 16.0 / 9.0, 0.1, 1000.0)
        view = look_at(
            np.array([0.0, 2.0, 5.0], dtype=np.float32),
            np.zeros(3, dtype=np.float32),
        )
        self.assertEqual(projection.shape, (4, 4))
        self.assertEqual(view.shape, (4, 4))
        self.assertTrue(np.isfinite(projection).all())
        self.assertTrue(np.isfinite(view).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
