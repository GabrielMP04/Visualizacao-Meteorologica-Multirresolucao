"""Camera livre controlada por teclado e mouse."""

from __future__ import annotations

import math
import numpy as np

from .math3d import look_at, normalize


class FlyCamera:
    def __init__(
        self,
        position: list[float] | np.ndarray,
        target: list[float] | np.ndarray,
        move_speed: float,
        mouse_sensitivity: float,
        fov: float,
    ) -> None:
        self.initial_position = np.asarray(position, dtype=np.float32)
        self.initial_target = np.asarray(target, dtype=np.float32)
        self.position = self.initial_position.copy()
        self.move_speed = float(move_speed)
        self.base_speed = float(move_speed)
        self.mouse_sensitivity = float(mouse_sensitivity)
        self.fov = float(fov)
        self.world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.yaw = -90.0
        self.pitch = -20.0
        self.front = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        self.look_at(self.initial_target)

    def _update_vectors(self) -> None:
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        front = np.array(
            [
                math.cos(yaw) * math.cos(pitch),
                math.sin(pitch),
                math.sin(yaw) * math.cos(pitch),
            ],
            dtype=np.float32,
        )
        self.front = normalize(front)
        self.right = normalize(np.cross(self.front, self.world_up))

    def look_at(self, target: np.ndarray | list[float]) -> None:
        direction = normalize(np.asarray(target, dtype=np.float32) - self.position)
        self.pitch = math.degrees(math.asin(float(np.clip(direction[1], -1.0, 1.0))))
        self.yaw = math.degrees(math.atan2(float(direction[2]), float(direction[0])))
        self._update_vectors()

    def reset(self) -> None:
        self.position = self.initial_position.copy()
        self.move_speed = self.base_speed
        self.look_at(self.initial_target)

    def view_matrix(self) -> np.ndarray:
        return look_at(self.position, self.position + self.front, self.world_up)

    def process_mouse(self, delta_x: float, delta_y: float) -> None:
        self.yaw += float(delta_x) * self.mouse_sensitivity
        self.pitch += float(delta_y) * self.mouse_sensitivity
        self.pitch = float(np.clip(self.pitch, -89.0, 89.0))
        self._update_vectors()

    def adjust_speed(self, wheel_delta: float) -> None:
        factor = 1.15 if wheel_delta > 0 else 1.0 / 1.15
        self.move_speed = float(np.clip(self.move_speed * factor, 10.0, 700.0))

    def move(self, direction: str, delta_time: float) -> None:
        velocity = self.move_speed * max(0.0, float(delta_time))
        if direction == "forward":
            self.position += self.front * velocity
        elif direction == "backward":
            self.position -= self.front * velocity
        elif direction == "left":
            self.position -= self.right * velocity
        elif direction == "right":
            self.position += self.right * velocity
        elif direction == "up":
            self.position += self.world_up * velocity
        elif direction == "down":
            self.position -= self.world_up * velocity
        self.position[1] = max(self.position[1], 2.0)

    def set_orbit(self, center: np.ndarray, angle_radians: float, radius: float, height: float) -> None:
        self.position = np.array(
            [
                center[0] + math.cos(angle_radians) * radius,
                height,
                center[2] + math.sin(angle_radians) * radius,
            ],
            dtype=np.float32,
        )
        target = np.array([center[0], center[1], center[2]], dtype=np.float32)
        self.look_at(target)

