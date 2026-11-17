"""Construcao da malha em patches e indices para os niveis de detalhe."""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .dataset import MeteorologicalDataset


@dataclass(frozen=True)
class PatchCPU:
    vertices: np.ndarray
    indices_by_lod: tuple[np.ndarray, ...]
    center: np.ndarray
    row: int
    column: int

    @property
    def triangle_counts(self) -> tuple[int, ...]:
        return tuple(int(indices.size // 3) for indices in self.indices_by_lod)


def compute_normals(height_world: np.ndarray, cell_size: float) -> np.ndarray:
    dz, dx = np.gradient(height_world, cell_size, cell_size)
    normals = np.stack((-dx, np.ones_like(height_world), -dz), axis=-1)
    lengths = np.linalg.norm(normals, axis=-1, keepdims=True)
    normals /= np.maximum(lengths, 1e-8)
    return normals.astype(np.float32)


def choose_lod(distance: float, thresholds: tuple[float, ...], levels: int) -> int:
    level = int(np.searchsorted(np.asarray(thresholds), float(distance), side="right"))
    return int(np.clip(level, 0, levels - 1))


class TerrainCPU:
    """Malha regular dividida em patches reutilizaveis pela GPU."""

    def __init__(
        self,
        dataset: MeteorologicalDataset,
        world_size: float,
        vertical_scale: float,
        patch_size: int,
        lod_strides: list[int] | tuple[int, ...],
        lod_distances: list[float] | tuple[float, ...],
        skirt_depth: float,
    ) -> None:
        dataset.validate()
        self.dataset = dataset
        self.grid_size = int(dataset.elevation.shape[0])
        self.world_size = float(world_size)
        self.vertical_scale = float(vertical_scale)
        self.patch_size = int(patch_size)
        self.lod_strides = tuple(int(value) for value in lod_strides)
        self.lod_distances = tuple(float(value) for value in lod_distances)
        self.skirt_depth = float(skirt_depth)
        self.cell_size = self.world_size / float(self.grid_size - 1)

        if self.patch_size <= 0:
            raise ValueError("patch_size deve ser positivo")
        if (self.grid_size - 1) % self.patch_size:
            raise ValueError("grid_size - 1 deve ser divisivel por patch_size")
        if not self.lod_strides or self.lod_strides[0] != 1:
            raise ValueError("lod_strides precisa comecar em 1")
        if any(value <= 0 or self.patch_size % value for value in self.lod_strides):
            raise ValueError("cada stride deve dividir patch_size")
        if tuple(sorted(self.lod_strides)) != self.lod_strides:
            raise ValueError("lod_strides deve estar em ordem crescente")
        if len(self.lod_distances) != len(self.lod_strides) - 1:
            raise ValueError("lod_distances deve ter um valor a menos que lod_strides")
        if tuple(sorted(self.lod_distances)) != self.lod_distances:
            raise ValueError("lod_distances deve estar em ordem crescente")

        self.height_world = dataset.elevation.astype(np.float32) * self.vertical_scale
        self.normals = compute_normals(self.height_world, self.cell_size)
        self.patches = self._build_patches()
        self.center = np.array(
            [self.world_size / 2.0, float(self.height_world.mean()), self.world_size / 2.0],
            dtype=np.float32,
        )

    def _base_vertex_index(self, local_row: int, local_column: int) -> int:
        width = self.patch_size + 1
        return local_row * width + local_column

    def _build_patch(self, row: int, column: int) -> PatchCPU:
        size = self.patch_size
        vertices: list[list[float]] = []
        for local_row in range(size + 1):
            global_row = row + local_row
            z = global_row * self.cell_size
            for local_column in range(size + 1):
                global_column = column + local_column
                x = global_column * self.cell_size
                y = float(self.height_world[global_row, global_column])
                nx, ny, nz = self.normals[global_row, global_column]
                temperature = float(self.dataset.temperature[global_row, global_column])
                vertices.append([x, y, z, float(nx), float(ny), float(nz), temperature])

        # Cada lado possui vertices duplicados e rebaixados, formando uma saia.
        side_base_indices: list[list[int]] = [
            [self._base_vertex_index(0, c) for c in range(size + 1)],
            [self._base_vertex_index(r, size) for r in range(size + 1)],
            [self._base_vertex_index(size, c) for c in range(size, -1, -1)],
            [self._base_vertex_index(r, 0) for r in range(size, -1, -1)],
        ]
        side_skirt_indices: list[list[int]] = []
        for base_side in side_base_indices:
            skirt_side: list[int] = []
            for base_index in base_side:
                skirt_vertex = list(vertices[base_index])
                skirt_vertex[1] -= self.skirt_depth
                skirt_side.append(len(vertices))
                vertices.append(skirt_vertex)
            side_skirt_indices.append(skirt_side)

        levels: list[np.ndarray] = []
        for stride in self.lod_strides:
            indices: list[int] = []
            for local_row in range(0, size, stride):
                for local_column in range(0, size, stride):
                    a = self._base_vertex_index(local_row, local_column)
                    b = self._base_vertex_index(local_row, local_column + stride)
                    c = self._base_vertex_index(local_row + stride, local_column)
                    d = self._base_vertex_index(local_row + stride, local_column + stride)
                    indices.extend((a, c, b, b, c, d))

            for base_side, skirt_side in zip(side_base_indices, side_skirt_indices, strict=True):
                for offset in range(0, size, stride):
                    base_a = base_side[offset]
                    base_b = base_side[offset + stride]
                    skirt_a = skirt_side[offset]
                    skirt_b = skirt_side[offset + stride]
                    indices.extend((base_a, skirt_a, base_b, base_b, skirt_a, skirt_b))
            levels.append(np.asarray(indices, dtype=np.uint32))

        center_row = row + size / 2.0
        center_column = column + size / 2.0
        center_y = float(
            self.height_world[
                min(int(round(center_row)), self.grid_size - 1),
                min(int(round(center_column)), self.grid_size - 1),
            ]
        )
        center = np.array(
            [center_column * self.cell_size, center_y, center_row * self.cell_size],
            dtype=np.float32,
        )
        return PatchCPU(
            vertices=np.asarray(vertices, dtype=np.float32),
            indices_by_lod=tuple(levels),
            center=center,
            row=row,
            column=column,
        )

    def _build_patches(self) -> tuple[PatchCPU, ...]:
        patches: list[PatchCPU] = []
        for row in range(0, self.grid_size - 1, self.patch_size):
            for column in range(0, self.grid_size - 1, self.patch_size):
                patches.append(self._build_patch(row, column))
        return tuple(patches)

    def select_levels(self, camera_position: np.ndarray, lod_enabled: bool) -> tuple[int, ...]:
        if not lod_enabled:
            return tuple(0 for _ in self.patches)
        camera = np.asarray(camera_position, dtype=np.float32)
        levels: list[int] = []
        for patch in self.patches:
            horizontal_distance = float(np.linalg.norm((patch.center - camera)[[0, 2]]))
            levels.append(choose_lod(horizontal_distance, self.lod_distances, len(self.lod_strides)))
        return tuple(levels)

    def triangle_summary(self, levels: tuple[int, ...]) -> tuple[int, tuple[int, ...]]:
        if len(levels) != len(self.patches):
            raise ValueError("um nivel deve ser informado para cada patch")
        histogram = [0] * len(self.lod_strides)
        triangles = 0
        for patch, level in zip(self.patches, levels, strict=True):
            histogram[level] += 1
            triangles += patch.triangle_counts[level]
        return triangles, tuple(histogram)

