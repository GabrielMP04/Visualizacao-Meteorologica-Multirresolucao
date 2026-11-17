"""Operacoes matriciais minimas para a camera OpenGL."""

from __future__ import annotations

import math
import numpy as np


def normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32)
    length = float(np.linalg.norm(vector))
    if length < 1e-8:
        return np.zeros_like(vector)
    return vector / length


def perspective(fov_degrees: float, aspect: float, near: float, far: float) -> np.ndarray:
    if aspect <= 0 or near <= 0 or far <= near:
        raise ValueError("parametros invalidos para a matriz de perspectiva")
    f = 1.0 / math.tan(math.radians(fov_degrees) / 2.0)
    result = np.zeros((4, 4), dtype=np.float32)
    result[0, 0] = f / aspect
    result[1, 1] = f
    result[2, 2] = (far + near) / (near - far)
    result[2, 3] = (2.0 * far * near) / (near - far)
    result[3, 2] = -1.0
    return result


def look_at(eye: np.ndarray, target: np.ndarray, world_up: np.ndarray | None = None) -> np.ndarray:
    eye = np.asarray(eye, dtype=np.float32)
    target = np.asarray(target, dtype=np.float32)
    up_reference = (
        np.asarray(world_up, dtype=np.float32)
        if world_up is not None
        else np.array([0.0, 1.0, 0.0], dtype=np.float32)
    )
    forward = normalize(target - eye)
    right = normalize(np.cross(forward, up_reference))
    if float(np.linalg.norm(right)) < 1e-8:
        right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    up = normalize(np.cross(right, forward))

    result = np.eye(4, dtype=np.float32)
    result[0, :3] = right
    result[1, :3] = up
    result[2, :3] = -forward
    result[0, 3] = -float(np.dot(right, eye))
    result[1, 3] = -float(np.dot(up, eye))
    result[2, 3] = float(np.dot(forward, eye))
    return result

