"""Janela, controles, renderizacao e benchmark da aplicacao."""

from __future__ import annotations

import json
import math
from pathlib import Path
import time

import glfw
import numpy as np
from OpenGL.GL import (
    GL_BACK,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_FILL,
    GL_FRONT_AND_BACK,
    GL_LINE,
    GL_MULTISAMPLE,
    GL_RGB,
    GL_UNSIGNED_BYTE,
    glClear,
    glClearColor,
    glEnable,
    glPolygonMode,
    glReadBuffer,
    glReadPixels,
    glViewport,
)
from PIL import Image

from .camera import FlyCamera
from .charts import create_comparison_chart
from .dataset import load_or_create
from .math3d import perspective
from .metrics import AutomaticBenchmark, MetricsRecorder, PerformanceMonitor
from .shader import ShaderProgram
from .terrain_cpu import TerrainCPU
from .terrain_gl import TerrainGL


class MeteorologicalApp:
    def __init__(
        self,
        project_dir: Path,
        config_path: Path,
        benchmark: bool = False,
        benchmark_seconds: float = 12.0,
        force_no_vsync: bool = False,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.config_path = (
            Path(config_path).resolve()
            if Path(config_path).is_absolute()
            else (self.project_dir / config_path).resolve()
        )
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.window_config = self.config["window"]
        self.terrain_config = self.config["terrain"]
        self.camera_config = self.config["camera"]
        self.render_config = self.config["rendering"]
        self.force_no_vsync = bool(force_no_vsync)
        self.automatic = AutomaticBenchmark(benchmark_seconds) if benchmark else None
        self.window = None
        self.width = int(self.window_config["width"])
        self.height = int(self.window_config["height"])
        self.lod_enabled = True
        self.wireframe = False
        self.mouse_look = False
        self.first_mouse = True
        self.last_mouse_x = 0.0
        self.last_mouse_y = 0.0
        self.pending_screenshot = False
        self.manual_recorder: MetricsRecorder | None = None
        self.benchmark_recorder: MetricsRecorder | None = None
        self.last_title_update = 0.0
        self.triangles = 0
        self.lod_histogram: tuple[int, ...] = ()

        self._create_window()
        self._create_scene()

    def _create_window(self) -> None:
        if not glfw.init():
            raise RuntimeError("GLFW nao conseguiu inicializar. Atualize o driver de video.")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.SAMPLES, int(self.window_config.get("msaa_samples", 4)))
        glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
        self.window = glfw.create_window(
            self.width,
            self.height,
            str(self.window_config["title"]),
            None,
            None,
        )
        if not self.window:
            glfw.terminate()
            raise RuntimeError(
                "nao foi possivel criar uma janela OpenGL 3.3. Verifique o driver da GPU"
            )
        glfw.make_context_current(self.window)
        use_vsync = bool(self.window_config.get("vsync", True)) and not self.force_no_vsync
        if self.automatic is not None:
            use_vsync = False
        glfw.swap_interval(1 if use_vsync else 0)
        glfw.set_framebuffer_size_callback(self.window, self._on_resize)
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_cursor_pos_callback(self.window, self._on_mouse_move)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_scroll_callback(self.window, self._on_scroll)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        glViewport(0, 0, self.width, self.height)

    def _create_scene(self) -> None:
        dataset_path = self.project_dir / str(self.terrain_config["dataset"])
        dataset = load_or_create(
            dataset_path,
            size=int(self.terrain_config["grid_size"]),
            seed=int(self.terrain_config["seed"]),
        )
        self.terrain_cpu = TerrainCPU(
            dataset=dataset,
            world_size=float(self.terrain_config["world_size"]),
            vertical_scale=float(self.terrain_config["vertical_scale"]),
            patch_size=int(self.terrain_config["patch_size"]),
            lod_strides=self.terrain_config["lod_strides"],
            lod_distances=self.terrain_config["lod_distances"],
            skirt_depth=float(self.terrain_config["skirt_depth"]),
        )
        self.terrain_gl = TerrainGL(self.terrain_cpu)
        self.shader = ShaderProgram(
            self.project_dir / "shaders" / "terrain.vert",
            self.project_dir / "shaders" / "terrain.frag",
        )
        self.camera = FlyCamera(
            position=self.camera_config["position"],
            target=self.camera_config["target"],
            move_speed=float(self.camera_config["move_speed"]),
            mouse_sensitivity=float(self.camera_config["mouse_sensitivity"]),
            fov=float(self.camera_config["field_of_view"]),
        )
        self.monitor = PerformanceMonitor()
        self.model_matrix = np.eye(4, dtype=np.float32)
        if self.automatic is not None:
            self.benchmark_recorder = MetricsRecorder(
                self.project_dir / "outputs", prefix="benchmark_opengl"
            )
        self._print_help()

    @staticmethod
    def _print_help() -> None:
        print(
            """
==========================================================
 VISUALIZACAO METEOROLOGICA - PYTHON + OPENGL
==========================================================
 W/A/S/D  mover camera       Q/E      descer/subir
 Mouse D. olhar ao redor     Roda     velocidade
 L        ligar/desligar LOD F        wireframe
 R        restaurar camera   B        gravar CSV
 F12      salvar imagem      ESC      sair
==========================================================
"""
        )

    def _on_resize(self, _window, width: int, height: int) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        glViewport(0, 0, self.width, self.height)

    def _on_key(self, window, key: int, _scancode: int, action: int, _mods: int) -> None:
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_L and self.automatic is None:
            self.lod_enabled = not self.lod_enabled
        elif key == glfw.KEY_F:
            self.wireframe = not self.wireframe
        elif key == glfw.KEY_R and self.automatic is None:
            self.camera.reset()
        elif key == glfw.KEY_F12:
            self.pending_screenshot = True
        elif key == glfw.KEY_B and self.automatic is None:
            self._toggle_manual_recording()

    def _on_mouse_button(self, window, button: int, action: int, _mods: int) -> None:
        if self.automatic is not None or button != glfw.MOUSE_BUTTON_RIGHT:
            return
        self.mouse_look = action == glfw.PRESS
        self.first_mouse = True
        glfw.set_input_mode(
            window,
            glfw.CURSOR,
            glfw.CURSOR_DISABLED if self.mouse_look else glfw.CURSOR_NORMAL,
        )

    def _on_mouse_move(self, _window, x_position: float, y_position: float) -> None:
        if not self.mouse_look or self.automatic is not None:
            return
        if self.first_mouse:
            self.last_mouse_x = x_position
            self.last_mouse_y = y_position
            self.first_mouse = False
            return
        delta_x = x_position - self.last_mouse_x
        delta_y = self.last_mouse_y - y_position
        self.last_mouse_x = x_position
        self.last_mouse_y = y_position
        self.camera.process_mouse(delta_x, delta_y)

    def _on_scroll(self, _window, _x_offset: float, y_offset: float) -> None:
        if self.automatic is None:
            self.camera.adjust_speed(y_offset)

    def _process_keyboard(self, delta_time: float) -> None:
        if self.automatic is not None:
            return
        keys = (
            (glfw.KEY_W, "forward"),
            (glfw.KEY_S, "backward"),
            (glfw.KEY_A, "left"),
            (glfw.KEY_D, "right"),
            (glfw.KEY_E, "up"),
            (glfw.KEY_Q, "down"),
        )
        for key, direction in keys:
            if glfw.get_key(self.window, key) == glfw.PRESS:
                self.camera.move(direction, delta_time)

    def _toggle_manual_recording(self) -> None:
        if self.manual_recorder is None:
            self.manual_recorder = MetricsRecorder(
                self.project_dir / "outputs", prefix="medicao_manual"
            )
            print("Gravacao iniciada. Pressione B novamente para salvar.")
            return
        frames_path, summary_path = self.manual_recorder.save()
        self.manual_recorder = None
        print(f"Quadros salvos em: {frames_path}")
        print(f"Resumo salvo em: {summary_path}")

    def _render(self) -> tuple[int, tuple[int, ...]]:
        background = self.render_config["background_color"]
        glClearColor(float(background[0]), float(background[1]), float(background[2]), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)

        projection = perspective(
            self.camera.fov,
            self.width / float(max(1, self.height)),
            float(self.camera_config["near_plane"]),
            float(self.camera_config["far_plane"]),
        )
        levels = self.terrain_cpu.select_levels(self.camera.position, self.lod_enabled)
        self.shader.use()
        self.shader.set_mat4("u_model", self.model_matrix)
        self.shader.set_mat4("u_view", self.camera.view_matrix())
        self.shader.set_mat4("u_projection", projection)
        self.shader.set_vec3("u_camera_position", self.camera.position)
        self.shader.set_vec3("u_light_direction", [-0.45, 0.82, -0.35])
        self.shader.set_float("u_temperature_min", self.render_config["temperature_min"])
        self.shader.set_float("u_temperature_max", self.render_config["temperature_max"])
        self.shader.set_float("u_fog_start", self.render_config["fog_start"])
        self.shader.set_float("u_fog_end", self.render_config["fog_end"])
        self.shader.set_vec3("u_fog_color", background)
        return self.terrain_gl.draw(levels)

    def _save_screenshot(self) -> Path:
        glReadBuffer(GL_BACK)
        pixels = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        image = Image.frombytes("RGB", (self.width, self.height), pixels)
        transpose = getattr(Image, "Transpose", Image).FLIP_TOP_BOTTOM
        image = image.transpose(transpose)
        output_dir = self.project_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / f"captura_{time.strftime('%Y%m%d_%H%M%S')}.png"
        image.save(destination)
        print(f"Captura salva em: {destination}")
        return destination

    def _update_title(self) -> None:
        now = time.perf_counter()
        if now - self.last_title_update < 0.25:
            return
        self.last_title_update = now
        mode = "COM LOD" if self.lod_enabled else "SEM LOD"
        recording = " | GRAVANDO" if self.manual_recorder is not None else ""
        if self.automatic is not None:
            recording = f" | BENCHMARK {self.automatic.phase_progress * 100:3.0f}%"
        histogram = "/".join(str(value) for value in self.lod_histogram)
        title = (
            f"{self.window_config['title']} | {mode} | "
            f"FPS {self.monitor.fps:6.1f} | {self.triangles:,} triangulos | "
            f"patches [{histogram}] | velocidade {self.camera.move_speed:.0f}{recording}"
        )
        glfw.set_window_title(self.window, title)

    def _record_metrics(self) -> None:
        mode = "com_lod" if self.lod_enabled else "sem_lod"
        recorders: list[MetricsRecorder] = []
        if self.manual_recorder is not None:
            recorders.append(self.manual_recorder)
        if (
            self.automatic is not None
            and self.benchmark_recorder is not None
            and self.automatic.should_record
        ):
            recorders.append(self.benchmark_recorder)
        for recorder in recorders:
            recorder.record(
                mode=mode,
                frame_time_ms=self.monitor.last_frame_time_ms,
                fps=self.monitor.fps,
                triangles=self.triangles,
                camera_position=self.camera.position,
                lod_histogram=self.lod_histogram,
            )

    def run(self) -> None:
        previous_time = time.perf_counter()
        try:
            while not glfw.window_should_close(self.window):
                frame_start = time.perf_counter()
                delta_time = min(0.1, frame_start - previous_time)
                previous_time = frame_start
                glfw.poll_events()
                self._process_keyboard(delta_time)

                if self.automatic is not None:
                    self.lod_enabled = self.automatic.lod_enabled
                    # Reiniciar o tempo em cada fase repete a mesma trajetoria de camera
                    # e torna a comparacao sem/com LOD experimentalmente justa.
                    elapsed = self.automatic.phase_elapsed
                    angle = elapsed * 0.22
                    height = 175.0 + 28.0 * math.sin(elapsed * 0.35)
                    self.camera.set_orbit(self.terrain_cpu.center, angle, 365.0, height)

                self.triangles, self.lod_histogram = self._render()
                if self.pending_screenshot:
                    self._save_screenshot()
                    self.pending_screenshot = False
                glfw.swap_buffers(self.window)

                frame_elapsed = time.perf_counter() - frame_start
                self.monitor.add_frame(frame_elapsed)
                self._record_metrics()
                self._update_title()

                if self.automatic is not None:
                    changed_phase = self.automatic.update()
                    if changed_phase:
                        self.monitor = PerformanceMonitor()
                    if self.automatic.done:
                        assert self.benchmark_recorder is not None
                        frames_path, summary_path = self.benchmark_recorder.save("comparacao")
                        chart_path = create_comparison_chart(summary_path)
                        print(f"Benchmark finalizado: {frames_path}")
                        print(f"Resumo: {summary_path}")
                        print(f"Grafico: {chart_path}")
                        glfw.set_window_should_close(self.window, True)
        finally:
            if self.manual_recorder is not None and self.manual_recorder.frames:
                self.manual_recorder.save()
            self.terrain_gl.delete()
            self.shader.delete()
            glfw.destroy_window(self.window)
            glfw.terminate()

