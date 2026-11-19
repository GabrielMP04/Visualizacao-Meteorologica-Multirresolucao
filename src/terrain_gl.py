"""Envio dos patches para a GPU e chamadas de desenho OpenGL."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
from pathlib import Path

from PIL import Image

from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_CLAMP_TO_EDGE,
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_RGB,
    GL_RGB8,
    GL_TEXTURE0,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNPACK_ALIGNMENT,
    GL_UNSIGNED_BYTE,
    glActiveTexture,
    glBindTexture,
    glDeleteTextures,
    glGenerateMipmap,
    glGenTextures,
    glGetIntegerv,
    glPixelStorei,
    glTexImage2D,
    glTexParameteri,
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

from .terrain_cpu import PatchCPU, TerrainCPU


class TerrainTexture:
    def __init__(self, path: Path) -> None:
        with Image.open(path) as source:
            image = source.convert("RGB")
        self.texture = int(glGenTextures(1))
        self.bind()
        alignment = glGetIntegerv(GL_UNPACK_ALIGNMENT)
        try:
            glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
            # A primeira linha do JPG e o norte, amostrado em v=0 no shader.
            glTexImage2D(
                GL_TEXTURE_2D, 0, GL_RGB8, image.width, image.height,
                0, GL_RGB, GL_UNSIGNED_BYTE, image.tobytes(),
            )
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glGenerateMipmap(GL_TEXTURE_2D)
        except Exception:
            self.delete()
            raise
        finally:
            glPixelStorei(GL_UNPACK_ALIGNMENT, alignment)

    def bind(self) -> None:
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture)

    def delete(self) -> None:
        glDeleteTextures([self.texture])


@dataclass
class PatchGL:
    vao: int
    vbo: int

    def delete(self) -> None:
        glDeleteBuffers(1, [self.vbo])
        glDeleteVertexArrays(1, [self.vao])


class TerrainGL:
    def __init__(self, terrain: TerrainCPU) -> None:
        self.terrain = terrain
        self.patches = tuple(self._upload_patch(patch) for patch in terrain.patches)
        index_buffers = []
        for indices in terrain.indices_by_lod:
            buffer = int(glGenBuffers(1))
            # O destino no upload nao fixa o uso futuro do buffer.
            glBindBuffer(GL_ARRAY_BUFFER, buffer)
            glBufferData(GL_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
            index_buffers.append((buffer, int(indices.size)))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.index_buffers = tuple(index_buffers)

    @staticmethod
    def _upload_patch(patch: PatchCPU) -> PatchGL:
        vao = int(glGenVertexArrays(1))
        vbo = int(glGenBuffers(1))
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

        glBindVertexArray(0)
        return PatchGL(vao=vao, vbo=vbo)

    def draw(self, levels: tuple[int, ...]) -> tuple[int, tuple[int, ...]]:
        if len(levels) != len(self.patches):
            raise ValueError("um nivel deve ser informado para cada patch")
        histogram = [0] * len(self.terrain.lod_strides)
        triangles = 0
        for patch, level in zip(self.patches, levels, strict=True):
            histogram[level] += 1
            buffer, count = self.index_buffers[level]
            glBindVertexArray(patch.vao)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, buffer)
            glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_INT, None)
            triangles += count // 3
        glBindVertexArray(0)
        return triangles, tuple(histogram)

    def delete(self) -> None:
        for patch in self.patches:
            patch.delete()
        glDeleteBuffers(len(self.index_buffers), [buffer for buffer, _ in self.index_buffers])

