"""Envio dos patches para a GPU e chamadas de desenho OpenGL."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes

from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_ELEMENT_ARRAY_BUFFER,
    GL_FLOAT,
    GL_STATIC_DRAW,
    GL_TRIANGLES,
    GL_UNSIGNED_INT,
    glBindBuffer,
    glBindVertexArray,
    glBufferData,
    glDeleteBuffers,
    glDeleteVertexArrays,
    glDrawElements,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glVertexAttribPointer,
)

from .terrain_cpu import TerrainCPU


def _as_id(value: int | list[int]) -> int:
    if isinstance(value, (list, tuple)):
        return int(value[0])
    return int(value)


@dataclass
class PatchGL:
    vao: int
    vbo: int
    ebos: tuple[int, ...]
    index_counts: tuple[int, ...]

    def draw(self, level: int) -> int:
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebos[level])
        count = self.index_counts[level]
        glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)
        return count // 3

    def delete(self) -> None:
        glDeleteBuffers(1, [self.vbo])
        glDeleteBuffers(len(self.ebos), list(self.ebos))
        glDeleteVertexArrays(1, [self.vao])


class TerrainGL:
    def __init__(self, terrain: TerrainCPU) -> None:
        self.terrain = terrain
        self.patches = tuple(self._upload_patch(patch) for patch in terrain.patches)

    @staticmethod
    def _upload_patch(patch) -> PatchGL:
        vao = _as_id(glGenVertexArrays(1))
        vbo = _as_id(glGenBuffers(1))
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, patch.vertices.nbytes, patch.vertices, GL_STATIC_DRAW)

        stride = 7 * 4
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, False, stride, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 1, GL_FLOAT, False, stride, ctypes.c_void_p(6 * 4))

        ebos: list[int] = []
        counts: list[int] = []
        for indices in patch.indices_by_lod:
            ebo = _as_id(glGenBuffers(1))
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
            ebos.append(ebo)
            counts.append(int(indices.size))

        glBindVertexArray(0)
        return PatchGL(vao=vao, vbo=vbo, ebos=tuple(ebos), index_counts=tuple(counts))

    def draw(self, levels: tuple[int, ...]) -> tuple[int, tuple[int, ...]]:
        if len(levels) != len(self.patches):
            raise ValueError("um nivel deve ser informado para cada patch")
        histogram = [0] * len(self.terrain.lod_strides)
        triangles = 0
        for patch, level in zip(self.patches, levels, strict=True):
            histogram[level] += 1
            triangles += patch.draw(level)
        glBindVertexArray(0)
        return triangles, tuple(histogram)

    def delete(self) -> None:
        for patch in self.patches:
            patch.delete()

