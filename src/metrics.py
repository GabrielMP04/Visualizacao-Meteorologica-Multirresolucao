"""Medicao de FPS e exportacao do experimento para CSV."""

from __future__ import annotations

from collections import deque
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import statistics
import time


class PerformanceMonitor:
    def __init__(self, sample_count: int = 120) -> None:
        self.frame_times: deque[float] = deque(maxlen=sample_count)
        self.last_frame_time_ms = 0.0

    def add_frame(self, elapsed_seconds: float) -> None:
        value = max(float(elapsed_seconds), 1e-9)
        self.frame_times.append(value)
        self.last_frame_time_ms = value * 1000.0

    @property
    def fps(self) -> float:
        if not self.frame_times:
            return 0.0
        return len(self.frame_times) / sum(self.frame_times)


@dataclass(frozen=True)
class FrameMetric:
    mode: str
    frame: int
    elapsed_seconds: float
    frame_time_ms: float
    fps: float
    triangles: int
    camera_x: float
    camera_y: float
    camera_z: float
    lod_histogram: tuple[int, ...]


class MetricsRecorder:
    def __init__(self, output_dir: str | Path, prefix: str = "medicao") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.frames: list[FrameMetric] = []
        self.started_at = time.perf_counter()

    def record(
        self,
        mode: str,
        frame_time_ms: float,
        fps: float,
        triangles: int,
        camera_position,
        lod_histogram: tuple[int, ...],
    ) -> None:
        self.frames.append(
            FrameMetric(
                mode=mode,
                frame=len(self.frames),
                elapsed_seconds=time.perf_counter() - self.started_at,
                frame_time_ms=float(frame_time_ms),
                fps=float(fps),
                triangles=int(triangles),
                camera_x=float(camera_position[0]),
                camera_y=float(camera_position[1]),
                camera_z=float(camera_position[2]),
                lod_histogram=tuple(int(value) for value in lod_histogram),
            )
        )

    def save(self, suffix: str | None = None) -> tuple[Path, Path]:
        if not self.frames:
            raise ValueError("nenhum quadro foi registrado")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{self.prefix}_{suffix or timestamp}"
        frames_path = self.output_dir / f"{name}_frames.csv"
        summary_path = self.output_dir / f"{name}_resumo.csv"
        max_levels = max(len(frame.lod_histogram) for frame in self.frames)

        headers = [
            "mode",
            "frame",
            "elapsed_seconds",
            "frame_time_ms",
            "fps",
            "triangles",
            "camera_x",
            "camera_y",
            "camera_z",
        ] + [f"patches_lod_{level}" for level in range(max_levels)]
        with frames_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for frame in self.frames:
                row = {
                    "mode": frame.mode,
                    "frame": frame.frame,
                    "elapsed_seconds": f"{frame.elapsed_seconds:.6f}",
                    "frame_time_ms": f"{frame.frame_time_ms:.6f}",
                    "fps": f"{frame.fps:.3f}",
                    "triangles": frame.triangles,
                    "camera_x": f"{frame.camera_x:.4f}",
                    "camera_y": f"{frame.camera_y:.4f}",
                    "camera_z": f"{frame.camera_z:.4f}",
                }
                for level in range(max_levels):
                    row[f"patches_lod_{level}"] = (
                        frame.lod_histogram[level] if level < len(frame.lod_histogram) else 0
                    )
                writer.writerow(row)

        grouped: dict[str, list[FrameMetric]] = {}
        for frame in self.frames:
            grouped.setdefault(frame.mode, []).append(frame)
        summary_headers = [
            "mode",
            "frames",
            "mean_fps",
            "mean_frame_time_ms",
            "std_frame_time_ms",
            "p95_frame_time_ms",
            "mean_triangles",
            "min_triangles",
            "max_triangles",
        ]
        with summary_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=summary_headers)
            writer.writeheader()
            for mode, frames in grouped.items():
                frame_times = [frame.frame_time_ms for frame in frames]
                triangles = [frame.triangles for frame in frames]
                sorted_times = sorted(frame_times)
                p95_index = min(len(sorted_times) - 1, int(0.95 * len(sorted_times)))
                writer.writerow(
                    {
                        "mode": mode,
                        "frames": len(frames),
                        "mean_fps": f"{statistics.fmean(frame.fps for frame in frames):.3f}",
                        "mean_frame_time_ms": f"{statistics.fmean(frame_times):.6f}",
                        "std_frame_time_ms": f"{statistics.pstdev(frame_times):.6f}",
                        "p95_frame_time_ms": f"{sorted_times[p95_index]:.6f}",
                        "mean_triangles": f"{statistics.fmean(triangles):.2f}",
                        "min_triangles": min(triangles),
                        "max_triangles": max(triangles),
                    }
                )
        return frames_path, summary_path


class AutomaticBenchmark:
    """Duas fases identicas: sem LOD e com LOD."""

    def __init__(self, seconds_per_mode: float, warmup_seconds: float = 2.0) -> None:
        self.seconds_per_mode = max(2.0, float(seconds_per_mode))
        self.warmup_seconds = max(0.5, float(warmup_seconds))
        self.phase_index = 0
        self.phase_started = time.perf_counter()
        self.done = False

    @property
    def mode_name(self) -> str:
        return "sem_lod" if self.phase_index == 0 else "com_lod"

    @property
    def lod_enabled(self) -> bool:
        return self.phase_index == 1

    @property
    def should_record(self) -> bool:
        return time.perf_counter() - self.phase_started >= self.warmup_seconds

    @property
    def phase_elapsed(self) -> float:
        """Tempo da fase atual, sem depender da duracao da fase anterior."""
        return max(0.0, time.perf_counter() - self.phase_started)

    @property
    def phase_progress(self) -> float:
        elapsed = time.perf_counter() - self.phase_started
        return min(1.0, elapsed / (self.warmup_seconds + self.seconds_per_mode))

    def update(self) -> bool:
        elapsed = time.perf_counter() - self.phase_started
        if elapsed < self.warmup_seconds + self.seconds_per_mode:
            return False
        if self.phase_index == 0:
            self.phase_index = 1
            self.phase_started = time.perf_counter()
            return True
        self.done = True
        return False

