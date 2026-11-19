"""Compilacao de shaders e envio de uniforms."""

from __future__ import annotations

from pathlib import Path
import numpy as np

from OpenGL.GL import (
    GL_FALSE,
    GL_FRAGMENT_SHADER,
    GL_VERTEX_SHADER,
    glDeleteProgram,
    glGetUniformLocation,
    glUniform1f,
    glUniform1i,
    glUniform4f,
    glUniform3f,
    glUniformMatrix4fv,
    glUseProgram,
)
from OpenGL.GL.shaders import compileProgram, compileShader


class ShaderProgram:
    def __init__(self, vertex_path: str | Path, fragment_path: str | Path) -> None:
        vertex_source = Path(vertex_path).read_text(encoding="utf-8")
        fragment_source = Path(fragment_path).read_text(encoding="utf-8")
        try:
            self.program = compileProgram(
                compileShader(vertex_source, GL_VERTEX_SHADER),
                compileShader(fragment_source, GL_FRAGMENT_SHADER),
            )
        except Exception as exc:
            raise RuntimeError(f"erro ao compilar os shaders: {exc}") from exc
        self._uniforms: dict[str, int] = {}

    def use(self) -> None:
        glUseProgram(self.program)

    def _location(self, name: str) -> int:
        if name not in self._uniforms:
            self._uniforms[name] = int(glGetUniformLocation(self.program, name))
        return self._uniforms[name]

    def set_int(self, name: str, value: int) -> None:
        glUniform1i(self._location(name), value)

    def set_vec4(self, name: str, value: tuple[float, float, float, float]) -> None:
        glUniform4f(self._location(name), *value)

    def set_float(self, name: str, value: float) -> None:
        glUniform1f(self._location(name), float(value))

    def set_vec3(self, name: str, value: np.ndarray | list[float] | tuple[float, ...]) -> None:
        vector = np.asarray(value, dtype=np.float32)
        glUniform3f(self._location(name), float(vector[0]), float(vector[1]), float(vector[2]))

    def set_mat4(self, name: str, matrix: np.ndarray) -> None:
        # OpenGL usa coluna principal; a transposicao explicita preserva a matriz Python.
        data = np.ascontiguousarray(np.asarray(matrix, dtype=np.float32).T)
        glUniformMatrix4fv(self._location(name), 1, GL_FALSE, data)

    def delete(self) -> None:
        if self.program:
            glDeleteProgram(self.program)
            self.program = 0

