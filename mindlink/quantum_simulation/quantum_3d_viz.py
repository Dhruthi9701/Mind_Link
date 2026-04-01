"""
Mind Link — Interactive 3D Quantum Visualization
=================================================
Shows the complete journey from EEG signals to quantum classification.

Features:
- 3D rotating Hilbert space visualization
- Real-time quantum state evolution
- Interactive camera controls
- Step-by-step explanations
- Comparison of different motor imagery patterns

Controls:
    SPACE       — Next step / Play animation
    R           — Reset to beginning
    C           — Cycle camera view
    Mouse drag  — Rotate view
    Scroll      — Zoom in/out
    1-4         — Jump to specific motor imagery class
    P           — Pause/Resume animation
    ESC         — Quit

Install: pip install pygame numpy scipy matplotlib qiskit qiskit-aer
"""

import sys
import os
import math
import time
import numpy as np
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pygame
    from pygame import gfxdraw
except ImportError:
    print("pip install pygame")
    sys.exit(1)

try:
    from qiskit.circuit.library import ZZFeatureMap
    from qiskit_aer import AerSimulator
    from qiskit.quantum_info import Statevector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    print("[viz] Qiskit not found — using mock quantum states")

# ══════════════════════════════════════════════════════════════════════
# COLORS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════

BG = (8, 10, 20)
GRID_COLOR = (30, 40, 60)
QUANTUM_BLUE = (0, 180, 255)
QUANTUM_PURPLE = (180, 80, 255)
QUANTUM_CYAN = (0, 255, 200)
QUANTUM_PINK = (255, 100, 180)
EEG_GREEN = (80, 255, 120)
CLASSICAL_ORANGE = (255, 160, 40)
TEXT_COLOR = (220, 230, 255)
HIGHLIGHT = (255, 220, 0)
GLOW_BLUE = (100, 200, 255)

W, H = 1280, 720  # Reduced to fit laptop screens
FPS = 30

# Greek symbols for better mathematical notation
GREEK_PSI = "ψ"
GREEK_THETA = "θ"
GREEK_PHI = "φ"
GREEK_ALPHA = "α"
GREEK_BETA = "β"
GREEK_MU = "μ"

# ══════════════════════════════════════════════════════════════════════
# 3D CAMERA
# ══════════════════════════════════════════════════════════════════════

class Camera3D:
    """Orbiting camera for 3D visualization."""
    
    def __init__(self, distance=15.0):
        self.distance = distance
        self.azimuth = 45.0
        self.elevation = 30.0
        self.target = np.array([0.0, 0.0, 0.0])
        self.fov = 600
        self.auto_rotate = True
        self.rotation_speed = 15.0  # degrees per second
        self.pan_offset = np.array([0.0, 0.0])  # NEW: Pan offset for dragging
        
    def update(self, dt):
        """Auto-rotate if enabled."""
        if self.auto_rotate:
            self.azimuth = (self.azimuth + self.rotation_speed * dt) % 360
    
    def rotate(self, daz, del_):
        """Manual rotation."""
        self.azimuth = (self.azimuth + daz) % 360
        self.elevation = max(-89, min(89, self.elevation + del_))
        self.auto_rotate = False
    
    def pan(self, dx, dy):
        """Pan the view (drag entire scene)."""
        # Convert screen space drag to world space pan
        pan_speed = 0.05
        self.pan_offset[0] += dx * pan_speed
        self.pan_offset[1] -= dy * pan_speed  # Inverted Y
        self.auto_rotate = False
    
    def zoom(self, delta):
        """Zoom in/out."""
        self.distance = max(5.0, min(50.0, self.distance + delta))
    
    def project(self, points_3d):
        """Project 3D points to 2D screen coordinates."""
        if len(points_3d) == 0:
            return []
        
        # Apply pan offset to target
        panned_target = self.target + np.array([self.pan_offset[0], self.pan_offset[1], 0.0])
        
        # Camera position
        az_rad = math.radians(self.azimuth)
        el_rad = math.radians(self.elevation)
        
        cam_x = panned_target[0] + self.distance * math.cos(el_rad) * math.sin(az_rad)
        cam_y = panned_target[1] - self.distance * math.sin(el_rad)
        cam_z = panned_target[2] + self.distance * math.cos(el_rad) * math.cos(az_rad)
        
        # View direction
        forward = panned_target - np.array([cam_x, cam_y, cam_z])
        forward = forward / (np.linalg.norm(forward) + 1e-9)
        
        # Right and up vectors
        world_up = np.array([0, 1, 0])
        right = np.cross(forward, world_up)
        right = right / (np.linalg.norm(right) + 1e-9)
        up = np.cross(right, forward)
        
        # Project each point
        results = []
        for pt in points_3d:
            # Translate to camera space
            rel = pt - np.array([cam_x, cam_y, cam_z])
            
            # Camera coordinates
            cam_x_coord = np.dot(rel, right)
            cam_y_coord = np.dot(rel, up)
            cam_z_coord = np.dot(rel, forward)
            
            if cam_z_coord < 0.1:
                results.append(None)
                continue
            
            # Perspective projection
            screen_x = int(W // 2 + cam_x_coord * self.fov / cam_z_coord)
            screen_y = int(H // 2 - cam_y_coord * self.fov / cam_z_coord)
            results.append((screen_x, screen_y, cam_z_coord))
        
        return results


# ══════════════════════════════════════════════════════════════════════
# QUANTUM STATE GENERATOR
# ══════════════════════════════════════════════════════════════════════

class QuantumStateGenerator:
    """Generate quantum states from EEG features using ZZ feature map."""
    
    def __init__(self, n_qubits=4, reps=2):
        self.n_qubits = n_qubits
        self.reps = reps
        self.dim = 2 ** n_qubits
        
        if QISKIT_AVAILABLE:
            self.feature_map = ZZFeatureMap(
                feature_dimension=n_qubits,
                reps=reps,
                entanglement="linear"
            )
        else:
            self.feature_map = None
    
    def encode(self, features):
        """Encode classical features into quantum state."""
        if QISKIT_AVAILABLE and self.feature_map:
            try:
                # Bind features to circuit
                # Try new API first (Qiskit 1.0+), then fall back to old API
                try:
                    # Qiskit 1.0+ uses assign_parameters with dict
                    feature_dict = {self.feature_map.parameters[i]: features[i] 
                                   for i in range(min(len(features), self.n_qubits))}
                    circuit = self.feature_map.assign_parameters(feature_dict)
                except (AttributeError, TypeError):
                    # Older Qiskit uses bind_parameters with list
                    circuit = self.feature_map.bind_parameters(features[:self.n_qubits])
                
                # Simulate to get statevector
                backend = AerSimulator(method='statevector')
                circuit.save_statevector()
                job = backend.run(circuit)
                result = job.result()
                statevector = result.get_statevector()
                
                return np.array(statevector.data)
            except Exception as e:
                print(f"[viz] Qiskit encoding failed: {e}")
                print("[viz] Using mock quantum state for visualization")
                return self._mock_state(features)
        else:
            # Mock quantum state
            return self._mock_state(features)
    
    def _mock_state(self, features):
        """Generate mock quantum state for visualization."""
        state = np.zeros(self.dim, dtype=complex)
        
        # Create superposition based on features
        for i in range(self.dim):
            phase = sum(features[j % len(features)] * ((i >> j) & 1) for j in range(self.n_qubits))
            amplitude = np.exp(-0.5 * ((i - self.dim/2) / (self.dim/4))**2)
            state[i] = amplitude * np.exp(1j * phase)
        
        # Normalize
        state = state / np.linalg.norm(state)
        return state


# ══════════════════════════════════════════════════════════════════════
# MOTOR IMAGERY PATTERNS
# ══════════════════════════════════════════════════════════════════════

MOTOR_IMAGERY_PATTERNS = {
    "Left Hand": {
        "features": np.array([2.1, 0.8, 1.5, 0.3]),  # High C3, low C4
        "color": QUANTUM_BLUE,
        "description": "Left motor cortex active\nHigh C3 mu suppression"
    },
    "Right Hand": {
        "features": np.array([0.8, 2.1, 0.3, 1.5]),  # Low C3, high C4
        "color": QUANTUM_PURPLE,
        "description": "Right motor cortex active\nHigh C4 mu suppression"
    },
    "Rest": {
        "features": np.array([0.5, 0.5, 1.8, 1.8]),  # Balanced, high beta
        "color": EEG_GREEN,
        "description": "No motor imagery\nHigh bilateral beta"
    },
    "Both Hands": {
        "features": np.array([1.8, 1.8, 1.2, 1.2]),  # High bilateral mu
        "color": CLASSICAL_ORANGE,
        "description": "Bilateral motor cortex\nBalanced mu suppression"
    }
}



# ══════════════════════════════════════════════════════════════════════
# VISUALIZATION STAGES
# ══════════════════════════════════════════════════════════════════════

class VisualizationStage:
    """Base class for visualization stages."""
    
    def __init__(self, title, description):
        self.title = title
        self.description = description
        self.progress = 0.0  # 0.0 to 1.0
    
    def update(self, dt):
        """Update animation."""
        pass
    
    def draw_3d(self, surface, camera):
        """Draw 3D elements."""
        pass
    
    def draw_2d(self, surface, font, small_font):
        """Draw 2D overlay."""
        pass


class Stage1_EEGSignal(VisualizationStage):
    """Stage 1: Raw EEG signal visualization."""
    
    def __init__(self, pattern_name, pattern_data):
        super().__init__(
            "Stage 1: EEG Signal Acquisition",
            f"Recording motor imagery: {pattern_name}\n" +
            pattern_data["description"]
        )
        self.pattern_name = pattern_name
        self.features = pattern_data["features"]
        self.color = pattern_data["color"]
        self.time = 0.0
        self.signal_history = deque(maxlen=200)
    
    def update(self, dt):
        self.time += dt
        self.progress = min(1.0, self.time / 3.0)
        
        # Generate mock EEG signal
        t = self.time
        c3_signal = 10 * np.sin(2 * np.pi * 10 * t) * self.features[0] / 2.0
        c4_signal = 10 * np.sin(2 * np.pi * 10 * t + 0.5) * self.features[1] / 2.0
        self.signal_history.append((c3_signal, c4_signal))
    
    def draw_2d(self, surface, font, small_font):
        # Main panel - centered and larger
        panel_w, panel_h = 1100, 600
        panel_x = (W - panel_w) // 2
        panel_y = 180
        
        # Panel background
        pygame.draw.rect(surface, (20, 25, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surface, self.color, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
        
        # Title
        title = font.render("Brain Activity - Motor Cortex Electrodes", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(W // 2, panel_y + 20))
        surface.blit(title, title_rect)
        
        # Signal display area
        signal_x = panel_x + 40
        signal_w = panel_w - 80
        
        # C3 Channel (Left Motor Cortex)
        c3_y = panel_y + 140
        c3_h = 150
        
        # C3 Background and grid
        pygame.draw.rect(surface, (15, 18, 25), (signal_x, c3_y - 80, signal_w, c3_h), border_radius=4)
        
        # C3 Label with explanation - MOVED ABOVE signal area
        c3_title = font.render("C3 - Left Motor Cortex", True, QUANTUM_CYAN)
        surface.blit(c3_title, (signal_x + 10, c3_y - 75))
        
        c3_desc = small_font.render("Controls right hand | Mu (8-13 Hz) suppression = motor imagery active", True, (150, 180, 200))
        surface.blit(c3_desc, (signal_x + 10, c3_y - 53))
        
        # C3 Grid lines with measurements
        for i in range(5):
            grid_y = c3_y - 30 + i * (c3_h // 4)
            pygame.draw.line(surface, GRID_COLOR, (signal_x, grid_y), (signal_x + signal_w, grid_y), 1)
            # Amplitude labels
            amp_val = 30 - i * 15
            amp_label = small_font.render(f"{amp_val}μV", True, (100, 120, 140))
            surface.blit(amp_label, (signal_x - 35, grid_y - 8))
        
        # C3 Center line
        pygame.draw.line(surface, (80, 100, 120), (signal_x, c3_y + 45), (signal_x + signal_w, c3_y + 45), 2)
        
        # C4 Channel (Right Motor Cortex)
        c4_y = panel_y + 380
        c4_h = 150
        
        # C4 Background and grid
        pygame.draw.rect(surface, (15, 18, 25), (signal_x, c4_y - 80, signal_w, c4_h), border_radius=4)
        
        # C4 Label with explanation - MOVED ABOVE signal area
        c4_title = font.render("C4 - Right Motor Cortex", True, QUANTUM_PURPLE)
        surface.blit(c4_title, (signal_x + 10, c4_y - 75))
        
        c4_desc = small_font.render("Controls left hand | Mu (8-13 Hz) suppression = motor imagery active", True, (150, 180, 200))
        surface.blit(c4_desc, (signal_x + 10, c4_y - 53))
        
        # C4 Grid lines with measurements
        for i in range(5):
            grid_y = c4_y - 30 + i * (c4_h // 4)
            pygame.draw.line(surface, GRID_COLOR, (signal_x, grid_y), (signal_x + signal_w, grid_y), 1)
            # Amplitude labels
            amp_val = 30 - i * 15
            amp_label = small_font.render(f"{amp_val}μV", True, (100, 120, 140))
            surface.blit(amp_label, (signal_x - 35, grid_y - 8))
        
        # C4 Center line
        pygame.draw.line(surface, (80, 100, 120), (signal_x, c4_y + 45), (signal_x + signal_w, c4_y + 45), 2)
        
        # Time axis label
        time_label = small_font.render("Time (seconds)", True, (150, 180, 200))
        time_rect = time_label.get_rect(center=(W // 2, panel_y + panel_h - 15))
        surface.blit(time_label, time_rect)
        
        # Plot signals
        if len(self.signal_history) > 1:
            points_c3 = []
            points_c4 = []
            for i, (c3, c4) in enumerate(self.signal_history):
                x = signal_x + int(i * signal_w / 200)
                y_c3 = int(c3_y + 45 - c3 * 2.5)
                y_c4 = int(c4_y + 45 - c4 * 2.5)
                points_c3.append((x, y_c3))
                points_c4.append((x, y_c4))
            
            if len(points_c3) > 1:
                # Draw with glow effect
                for width, alpha in [(5, 50), (3, 100), (2, 255)]:
                    if width == 2:
                        pygame.draw.lines(surface, QUANTUM_CYAN, False, points_c3, width)
                        pygame.draw.lines(surface, QUANTUM_PURPLE, False, points_c4, width)
                    else:
                        # Glow layers
                        for j in range(len(points_c3) - 1):
                            pygame.draw.line(surface, QUANTUM_CYAN, points_c3[j], points_c3[j+1], width)
                            pygame.draw.line(surface, QUANTUM_PURPLE, points_c4[j], points_c4[j+1], width)


class Stage2_FeatureExtraction(VisualizationStage):
    """Stage 2: Extract classical features from EEG."""
    
    def __init__(self, pattern_name, pattern_data):
        super().__init__(
            "Stage 2: Feature Extraction",
            "Extracting mu/beta band power from C3/C4\n" +
            "Features normalized to [0, π] for quantum encoding"
        )
        self.pattern_name = pattern_name
        self.features = pattern_data["features"]
        self.color = pattern_data["color"]
        self.time = 0.0
        self.feature_labels = [f"C3 {GREEK_MU} (Mu)", f"C4 {GREEK_MU} (Mu)", f"C3 {GREEK_BETA} (Beta)", f"C4 {GREEK_BETA} (Beta)"]
        self.feature_descriptions = [
            "Left motor cortex rhythm (8-13 Hz) - Suppressed during right hand imagery",
            "Right motor cortex rhythm (8-13 Hz) - Suppressed during left hand imagery",
            "Left motor cortex activation (13-30 Hz) - Increases with motor planning",
            "Right motor cortex activation (13-30 Hz) - Increases with motor planning"
        ]
    
    def update(self, dt):
        self.time += dt
        self.progress = min(1.0, self.time / 2.0)
    
    def draw_2d(self, surface, font, small_font):
        # Main panel - CENTER ALIGNED
        panel_w, panel_h = 550, 580
        panel_x = (W - panel_w) // 2  # Center aligned
        panel_y = 120
        
        pygame.draw.rect(surface, (20, 25, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surface, self.color, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
        
        title = font.render("Classical Feature Extraction", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(panel_x + panel_w // 2, panel_y + 15))
        surface.blit(title, title_rect)
        
        # Explanation
        exp_text = small_font.render("Power spectral density analysis extracts frequency band power from EEG signals", True, (150, 180, 200))
        exp_rect = exp_text.get_rect(center=(panel_x + panel_w // 2, panel_y + 38))
        surface.blit(exp_text, exp_rect)
        
        # Draw feature bars - SMALLER, evenly distributed
        bar_h = 45  # Reduced from 60
        bar_spacing = 100  # Reduced from 120
        bar_w = 400  # Reduced from 600
        max_val = np.pi
        
        start_y = panel_y + 70  # Adjusted start
        
        colors = [QUANTUM_CYAN, QUANTUM_PURPLE, QUANTUM_BLUE, QUANTUM_PINK]
        
        for i, (label, val, desc) in enumerate(zip(self.feature_labels, self.features, self.feature_descriptions)):
            bar_y = start_y + i * bar_spacing
            
            # Feature name and value - left aligned
            name_text = font.render(label, True, colors[i])
            surface.blit(name_text, (panel_x + 20, bar_y))
            
            val_text = font.render(f"{val:.3f} rad", True, HIGHLIGHT)
            surface.blit(val_text, (panel_x + 150, bar_y))
            
            # Description - smaller text below, SHORTENED
            desc_short = desc[:60] + "..." if len(desc) > 60 else desc
            desc_surf = small_font.render(desc_short, True, (130, 150, 170))
            surface.blit(desc_surf, (panel_x + 20, bar_y + 20))
            
            # Bar background with grid
            bar_x = panel_x + 20
            bar_bg_y = bar_y + 38
            pygame.draw.rect(surface, (30, 35, 45), (bar_x, bar_bg_y, bar_w, bar_h), border_radius=4)
            
            # Grid lines for measurement
            for j in range(5):
                grid_x = bar_x + int(j * bar_w / 4)
                pygame.draw.line(surface, GRID_COLOR, (grid_x, bar_bg_y), (grid_x, bar_bg_y + bar_h), 1)
                # Value labels
                if j > 0:
                    grid_val = (np.pi / 4) * j
                    grid_label = small_font.render(f"{grid_val:.2f}", True, (100, 120, 140))
                    surface.blit(grid_label, (grid_x - 15, bar_bg_y + bar_h + 3))
            
            # Bar fill (animated)
            fill_w = int(bar_w * (val / max_val) * min(1.0, self.progress * 2))
            if fill_w > 0:
                # Gradient effect
                for x_offset in range(fill_w):
                    alpha = int(200 + 55 * (x_offset / max(fill_w, 1)))
                    color_with_alpha = tuple(int(c * alpha / 255) for c in colors[i])
                    pygame.draw.line(surface, color_with_alpha, 
                                   (bar_x + x_offset, bar_bg_y), 
                                   (bar_x + x_offset, bar_bg_y + bar_h))
            
            # Border
            pygame.draw.rect(surface, colors[i], (bar_x, bar_bg_y, bar_w, bar_h), 2, border_radius=4)
            
            # Max line (π)
            max_x = bar_x + bar_w
            pygame.draw.line(surface, (255, 100, 100), (max_x, bar_bg_y), (max_x, bar_bg_y + bar_h), 3)
            max_lbl = font.render("π", True, (255, 100, 100))
            surface.blit(max_lbl, (max_x + 8, bar_bg_y + bar_h // 2 - 10))
        
        # Bottom explanation - COMPACT
        bottom_y = panel_y + panel_h - 50
        
        # Create a sub-panel for legend
        legend_panel_h = 40
        pygame.draw.rect(surface, (15, 20, 30), (panel_x + 15, bottom_y, panel_w - 30, legend_panel_h), border_radius=4)
        
        note1 = small_font.render(f"Mu ({GREEK_MU}): 8-13 Hz - Motor idle, suppressed during imagery", True, QUANTUM_CYAN)
        note2 = small_font.render(f"Beta ({GREEK_BETA}): 13-30 Hz - Motor activation, increases with planning", True, QUANTUM_BLUE)
        
        note1_rect = note1.get_rect(center=(panel_x + panel_w // 2, bottom_y + 12))
        note2_rect = note2.get_rect(center=(panel_x + panel_w // 2, bottom_y + 28))
        
        surface.blit(note1, note1_rect)
        surface.blit(note2, note2_rect)


class Stage3_QuantumEncoding(VisualizationStage):
    """Stage 3: Encode features into quantum state."""
    
    def __init__(self, pattern_name, pattern_data, quantum_gen):
        super().__init__(
            "Stage 3: Quantum Encoding (ZZ Feature Map)",
            "Mapping classical features to quantum Hilbert space\n" +
            "Creating superposition and entanglement"
        )
        self.pattern_name = pattern_name
        self.features = pattern_data["features"]
        self.color = pattern_data["color"]
        self.quantum_gen = quantum_gen
        self.state_vector = None
        self.time = 0.0
    
    def update(self, dt):
        self.time += dt
        self.progress = min(1.0, self.time / 2.0)
        
        if self.progress > 0.3 and self.state_vector is None:
            self.state_vector = self.quantum_gen.encode(self.features)
    
    def draw_3d(self, surface, camera):
        if self.state_vector is None or self.progress < 0.5:
            return
        
        # Draw quantum state as 3D bars in Hilbert space
        n_basis = len(self.state_vector)
        grid_size = int(np.sqrt(n_basis))
        
        # Draw base grid first
        self._draw_base_grid(surface, camera, grid_size)
        
        points_3d = []
        bar_data = []
        
        for i in range(n_basis):
            row = i // grid_size
            col = i % grid_size
            
            # Position in 3D grid
            x = (col - grid_size / 2) * 2.0
            z = (row - grid_size / 2) * 2.0
            
            # Amplitude
            amplitude = np.abs(self.state_vector[i])
            height = amplitude * 10.0 * self.progress
            
            # Base and top positions
            base = np.array([x, 0, z])
            top = np.array([x, height, z])
            
            points_3d.extend([base, top])
            bar_data.append((i, amplitude, height, self.state_vector[i]))
        
        # Project to 2D
        projected = camera.project(points_3d)
        
        # Draw bars
        for i, (basis_idx, amp, height, complex_amp) in enumerate(bar_data):
            base_idx = i * 2
            top_idx = i * 2 + 1
            
            if projected[base_idx] and projected[top_idx]:
                base_2d = projected[base_idx]
                top_2d = projected[top_idx]
                
                # Color based on phase
                phase = np.angle(complex_amp)
                hue = (phase + np.pi) / (2 * np.pi)
                color = self._hue_to_rgb(hue)
                
                # Draw bar
                width = max(2, int(20 / (base_2d[2] + 1)))
                pygame.draw.line(surface, color, (base_2d[0], base_2d[1]), (top_2d[0], top_2d[1]), width)
                
                # Glow effect
                if amp > 0.1:
                    glow_color = tuple(min(255, c + 50) for c in color)
                    pygame.draw.circle(surface, glow_color, (top_2d[0], top_2d[1]), width + 2)
    
    def _draw_base_grid(self, surface, camera, grid_size):
        """Draw base grid for quantum state projection."""
        grid_points = []
        for i in range(grid_size + 1):
            for j in range(grid_size + 1):
                x = (i - grid_size / 2) * 2.0
                z = (j - grid_size / 2) * 2.0
                grid_points.append(np.array([x, 0, z]))
        
        projected = camera.project(grid_points)
        
        # Draw grid lines (horizontal)
        for i in range(grid_size + 1):
            for j in range(grid_size):
                idx1 = i * (grid_size + 1) + j
                idx2 = i * (grid_size + 1) + j + 1
                if projected[idx1] and projected[idx2]:
                    pygame.draw.line(surface, GRID_COLOR, 
                                   (projected[idx1][0], projected[idx1][1]),
                                   (projected[idx2][0], projected[idx2][1]), 1)
        
        # Draw grid lines (vertical)
        for j in range(grid_size + 1):
            for i in range(grid_size):
                idx1 = i * (grid_size + 1) + j
                idx2 = (i + 1) * (grid_size + 1) + j
                if projected[idx1] and projected[idx2]:
                    pygame.draw.line(surface, GRID_COLOR,
                                   (projected[idx1][0], projected[idx1][1]),
                                   (projected[idx2][0], projected[idx2][1]), 1)
    
    def _hue_to_rgb(self, hue):
        """Convert hue [0,1] to RGB."""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def draw_2d(self, surface, font, small_font):
        # Circuit diagram info - RIGHT SIDE PANEL, SMALLER
        panel_x, panel_y = W - 420, 120
        panel_w, panel_h = 400, 580
        
        pygame.draw.rect(surface, (20, 25, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surface, self.color, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
        
        title = font.render("ZZ Feature Map Circuit", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(panel_x + panel_w // 2, panel_y + 15))
        surface.blit(title, title_rect)
        
        # Circuit explanation with proper symbols
        y_offset = 45
        
        sections = [
            ("Layer 1: Hadamard Gates (H)", HIGHLIGHT, [
                "Creates quantum superposition",
                "H|0⟩ = (|0⟩ + |1⟩) / √2",
                "Prepares qubits equally"
            ]),
            (f"Layer 2: RZ Rotations", QUANTUM_CYAN, [
                "Encodes feature values",
                f"RZ({GREEK_THETA}) = exp(-i·{GREEK_THETA}·Z/2)",
                f"{GREEK_THETA} = feature in radians"
            ]),
            (f"Layer 3: ZZ Entanglement", QUANTUM_PURPLE, [
                "Creates quantum correlations",
                f"ZZ({GREEK_PHI}) = exp(-i·{GREEK_PHI}·Z_i⊗Z_j/2)",
                "Connects neighboring qubits"
            ]),
            ("Repetition: 2x", CLASSICAL_ORANGE, [
                "Layers 1-3 repeated twice",
                "Deeper feature encoding",
                "Stronger entanglement"
            ])
        ]
        
        for section_title, title_color, items in sections:
            # Section title
            sec_title = font.render(section_title, True, title_color)
            surface.blit(sec_title, (panel_x + 15, panel_y + y_offset))
            y_offset += 24
            
            # Section items
            for item in items:
                item_text = small_font.render("  " + item, True, (150, 170, 190))
                surface.blit(item_text, (panel_x + 15, panel_y + y_offset))
                y_offset += 17
            
            y_offset += 6
        
        # 3D Visualization Legend
        y_offset += 5
        legend_title = font.render("3D Visualization:", True, HIGHLIGHT)
        surface.blit(legend_title, (panel_x + 15, panel_y + y_offset))
        y_offset += 24
        
        legend_items = [
            "Colored bars = quantum amplitudes",
            "Bar height = probability amplitude",
            "Color hue = quantum phase angle",
            "Brighter = higher probability"
        ]
        
        for item in legend_items:
            item_text = small_font.render("  " + item, True, (150, 170, 190))
            surface.blit(item_text, (panel_x + 15, panel_y + y_offset))
            y_offset += 17
        
        # Bottom note
        note = small_font.render("Result: 4 features → 16D quantum state", True, HIGHLIGHT)
        note_rect = note.get_rect(center=(panel_x + panel_w // 2, panel_y + panel_h - 15))
        surface.blit(note, note_rect)


class Stage4_HilbertSpace(VisualizationStage):
    """Stage 4: Visualize quantum state in Hilbert space."""
    
    def __init__(self, pattern_name, pattern_data, quantum_gen):
        super().__init__(
            "Stage 4: Quantum State in Hilbert Space",
            f"16-dimensional complex vector space\n" +
            f"State |{GREEK_PSI}⟩ = Σ {GREEK_ALPHA}_i|i⟩ where Σ|{GREEK_ALPHA}_i|² = 1"
        )
        self.pattern_name = pattern_name
        self.features = pattern_data["features"]
        self.color = pattern_data["color"]
        self.quantum_gen = quantum_gen
        self.state_vector = quantum_gen.encode(pattern_data["features"])
        self.time = 0.0
    
    def update(self, dt):
        self.time += dt
        self.progress = min(1.0, self.time / 3.0)
    
    def draw_3d(self, surface, camera):
        # Draw full 3D Hilbert space visualization
        n_basis = len(self.state_vector)
        grid_size = int(np.sqrt(n_basis))
        
        # Draw grid floor
        self._draw_grid(surface, camera, grid_size)
        
        # Draw quantum state bars
        points_3d = []
        bar_data = []
        
        for i in range(n_basis):
            row = i // grid_size
            col = i % grid_size
            
            x = (col - grid_size / 2) * 2.5
            z = (row - grid_size / 2) * 2.5
            
            amplitude = np.abs(self.state_vector[i])
            probability = amplitude ** 2
            height = probability * 30.0
            
            base = np.array([x, 0, z])
            top = np.array([x, height, z])
            
            points_3d.extend([base, top])
            bar_data.append((i, amplitude, probability, height, self.state_vector[i]))
        
        projected = camera.project(points_3d)
        
        # Sort by depth for proper rendering
        render_order = []
        for i, (basis_idx, amp, prob, height, complex_amp) in enumerate(bar_data):
            base_idx = i * 2
            if projected[base_idx]:
                render_order.append((projected[base_idx][2], i, basis_idx, amp, prob, height, complex_amp))
        
        render_order.sort(reverse=True)
        
        # Draw bars back to front
        for depth, i, basis_idx, amp, prob, height, complex_amp in render_order:
            base_idx = i * 2
            top_idx = i * 2 + 1
            
            if projected[base_idx] and projected[top_idx]:
                base_2d = projected[base_idx]
                top_2d = projected[top_idx]
                
                # Color based on amplitude
                intensity = min(1.0, amp * 3)
                color = tuple(int(c * intensity) for c in self.color)
                
                # Draw bar
                width = max(3, int(25 / (base_2d[2] + 1)))
                pygame.draw.line(surface, color, (base_2d[0], base_2d[1]), (top_2d[0], top_2d[1]), width)
                
                # Top cap
                if prob > 0.01:
                    cap_color = tuple(min(255, c + 80) for c in color)
                    pygame.draw.circle(surface, cap_color, (top_2d[0], top_2d[1]), width // 2 + 2)
                
                # Label top states
                if prob > 0.05:
                    basis_str = format(basis_idx, f'0{int(np.log2(n_basis))}b')
                    label = pygame.font.SysFont("consolas", 10).render(f"|{basis_str}⟩", True, TEXT_COLOR)
                    surface.blit(label, (top_2d[0] - 15, top_2d[1] - 20))
    
    def _draw_grid(self, surface, camera, grid_size):
        """Draw grid floor in 3D."""
        grid_points = []
        for i in range(grid_size + 1):
            for j in range(grid_size + 1):
                x = (i - grid_size / 2) * 2.5
                z = (j - grid_size / 2) * 2.5
                grid_points.append(np.array([x, 0, z]))
        
        projected = camera.project(grid_points)
        
        # Draw grid lines
        for i in range(grid_size + 1):
            for j in range(grid_size):
                idx1 = i * (grid_size + 1) + j
                idx2 = i * (grid_size + 1) + j + 1
                if projected[idx1] and projected[idx2]:
                    pygame.draw.line(surface, GRID_COLOR, 
                                   (projected[idx1][0], projected[idx1][1]),
                                   (projected[idx2][0], projected[idx2][1]), 1)
        
        for j in range(grid_size + 1):
            for i in range(grid_size):
                idx1 = i * (grid_size + 1) + j
                idx2 = (i + 1) * (grid_size + 1) + j
                if projected[idx1] and projected[idx2]:
                    pygame.draw.line(surface, GRID_COLOR,
                                   (projected[idx1][0], projected[idx1][1]),
                                   (projected[idx2][0], projected[idx2][1]), 1)
    
    def draw_2d(self, surface, font, small_font):
        # State info panel - RIGHT SIDE, SMALLER
        panel_x, panel_y = W - 420, 120
        panel_w, panel_h = 400, 580
        
        pygame.draw.rect(surface, (20, 25, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surface, self.color, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
        
        title = font.render(f"Quantum State |{GREEK_PSI}⟩", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(panel_x + panel_w // 2, panel_y + 15))
        surface.blit(title, title_rect)
        
        # Explanation with proper symbols
        exp1 = small_font.render("16-dimensional complex vector space", True, (150, 170, 190))
        exp2 = small_font.render(f"|{GREEK_PSI}⟩ = Σ_i ({GREEK_ALPHA}_i·|i⟩) where Σ_i |{GREEK_ALPHA}_i|² = 1", True, QUANTUM_CYAN)
        exp1_rect = exp1.get_rect(center=(panel_x + panel_w // 2, panel_y + 35))
        exp2_rect = exp2.get_rect(center=(panel_x + panel_w // 2, panel_y + 52))
        surface.blit(exp1, exp1_rect)
        surface.blit(exp2, exp2_rect)
        
        # Top 5 basis states
        probabilities = np.abs(self.state_vector) ** 2
        top_indices = np.argsort(probabilities)[::-1][:5]
        
        y_offset = 75
        sec_title = font.render("Top 5 Basis States:", True, HIGHLIGHT)
        surface.blit(sec_title, (panel_x + 15, panel_y + y_offset))
        y_offset += 24
        
        # Header
        header1 = small_font.render("State", True, (120, 140, 160))
        header2 = small_font.render("Probability", True, (120, 140, 160))
        header3 = small_font.render("Amplitude", True, (120, 140, 160))
        surface.blit(header1, (panel_x + 15, panel_y + y_offset))
        surface.blit(header2, (panel_x + 85, panel_y + y_offset))
        surface.blit(header3, (panel_x + 190, panel_y + y_offset))
        y_offset += 18
        
        n_qubits = int(np.log2(len(self.state_vector)))
        for idx in top_indices:
            basis_str = format(idx, f'0{n_qubits}b')
            prob = probabilities[idx]
            amp = self.state_vector[idx]
            
            state_text = f"|{basis_str}⟩"
            prob_text = f"{prob:.4f}"
            amp_text = f"{amp.real:.2f}{amp.imag:+.2f}i"
            
            text1 = small_font.render(state_text, True, QUANTUM_CYAN)
            text2 = small_font.render(prob_text, True, TEXT_COLOR)
            text3 = small_font.render(amp_text, True, (150, 170, 190))
            
            surface.blit(text1, (panel_x + 15, panel_y + y_offset))
            surface.blit(text2, (panel_x + 85, panel_y + y_offset))
            surface.blit(text3, (panel_x + 190, panel_y + y_offset))
            
            # Probability bar
            bar_w = int(130 * prob)
            if bar_w > 0:
                pygame.draw.rect(surface, self.color, (panel_x + 85, panel_y + y_offset + 12, bar_w, 4), border_radius=2)
            
            y_offset += 23
        
        # Normalization check
        y_offset += 10
        total_prob = np.sum(probabilities)
        norm_color = HIGHLIGHT if abs(total_prob - 1.0) < 0.001 else (255, 100, 100)
        norm_text = font.render(f"Σ_i |{GREEK_ALPHA}_i|² = {total_prob:.6f}", True, norm_color)
        norm_rect = norm_text.get_rect(center=(panel_x + panel_w // 2, panel_y + y_offset))
        surface.blit(norm_text, norm_rect)
        
        if abs(total_prob - 1.0) < 0.001:
            check_text = small_font.render("State is properly normalized ✓", True, EEG_GREEN)
        else:
            check_text = small_font.render("Normalization error", True, (255, 100, 100))
        check_rect = check_text.get_rect(center=(panel_x + panel_w // 2, panel_y + y_offset + 17))
        surface.blit(check_text, check_rect)
        
        # Explanation section
        y_offset += 42
        exp_title = font.render("What This Means:", True, HIGHLIGHT)
        surface.blit(exp_title, (panel_x + 15, panel_y + y_offset))
        y_offset += 24
        
        explanations = [
            "Each |0000⟩ to |1111⟩ = outcome",
            f"Probability = |{GREEK_ALPHA}|² = likelihood",
            "Higher 3D bars = likely states",
            "Superposition = ALL states!"
        ]
        
        for exp in explanations:
            exp_surf = small_font.render(exp, True, (150, 170, 190))
            surface.blit(exp_surf, (panel_x + 15, panel_y + y_offset))
            y_offset += 17
        
        # 3D Visualization Legend
        y_offset += 12
        legend_title = font.render("3D Legend:", True, HIGHLIGHT)
        surface.blit(legend_title, (panel_x + 15, panel_y + y_offset))
        y_offset += 22
        
        # Color legend with sample
        legend_items = [
            (self.color, "Bar color = pattern type"),
            ((200, 200, 200), f"Height = probability |{GREEK_ALPHA}|²"),
            ((150, 170, 190), "Grid = basis positions")
        ]
        
        for color, text in legend_items:
            # Color sample
            pygame.draw.rect(surface, color, (panel_x + 15, panel_y + y_offset, 12, 12), border_radius=2)
            # Text
            text_surf = small_font.render(text, True, (150, 170, 190))
            surface.blit(text_surf, (panel_x + 32, panel_y + y_offset))
            y_offset += 17




class Stage5_Comparison(VisualizationStage):
    """Stage 5: Compare all motor imagery patterns."""
    
    def __init__(self, quantum_gen):
        super().__init__(
            "Stage 5: Pattern Comparison",
            "Comparing quantum states for different motor imagery\n" +
            "Quantum kernel measures state similarity"
        )
        self.quantum_gen = quantum_gen
        self.patterns = {}
        self.time = 0.0
        
        # Generate all states
        for name, data in MOTOR_IMAGERY_PATTERNS.items():
            state = quantum_gen.encode(data["features"])
            self.patterns[name] = {
                "state": state,
                "color": data["color"],
                "features": data["features"]
            }
    
    def update(self, dt):
        self.time += dt
        self.progress = min(1.0, self.time / 4.0)
    
    def draw_3d(self, surface, camera):
        # Draw all patterns side by side
        pattern_names = list(self.patterns.keys())
        n_patterns = len(pattern_names)
        
        # Draw base grid for all patterns
        self._draw_base_grid(surface, camera, n_patterns)
        
        for p_idx, name in enumerate(pattern_names):
            pattern = self.patterns[name]
            state = pattern["state"]
            color = pattern["color"]
            
            # Offset each pattern
            x_offset = (p_idx - n_patterns / 2) * 8.0
            
            n_basis = len(state)
            grid_size = int(np.sqrt(n_basis))
            
            points_3d = []
            bar_data = []
            
            for i in range(n_basis):
                row = i // grid_size
                col = i % grid_size
                
                x = (col - grid_size / 2) * 1.5 + x_offset
                z = (row - grid_size / 2) * 1.5
                
                amplitude = np.abs(state[i])
                probability = amplitude ** 2
                height = probability * 20.0
                
                base = np.array([x, 0, z])
                top = np.array([x, height, z])
                
                points_3d.extend([base, top])
                bar_data.append((amplitude, probability, height))
            
            projected = camera.project(points_3d)
            
            # Draw bars
            for i, (amp, prob, height) in enumerate(bar_data):
                base_idx = i * 2
                top_idx = i * 2 + 1
                
                if projected[base_idx] and projected[top_idx]:
                    base_2d = projected[base_idx]
                    top_2d = projected[top_idx]
                    
                    intensity = min(1.0, amp * 3)
                    bar_color = tuple(int(c * intensity) for c in color)
                    
                    width = max(2, int(15 / (base_2d[2] + 1)))
                    pygame.draw.line(surface, bar_color, (base_2d[0], base_2d[1]), (top_2d[0], top_2d[1]), width)
            
            # Label
            label_pos = np.array([x_offset, -2, 0])
            label_proj = camera.project([label_pos])[0]
            if label_proj:
                label = pygame.font.SysFont("consolas", 14, bold=True).render(name, True, color)
                surface.blit(label, (label_proj[0] - label.get_width() // 2, label_proj[1]))
    
    def _draw_base_grid(self, surface, camera, n_patterns):
        """Draw base grid for all pattern projections."""
        grid_size = 4  # 4x4 grid for each pattern
        
        for p_idx in range(n_patterns):
            x_offset = (p_idx - n_patterns / 2) * 8.0
            
            grid_points = []
            for i in range(grid_size + 1):
                for j in range(grid_size + 1):
                    x = (i - grid_size / 2) * 1.5 + x_offset
                    z = (j - grid_size / 2) * 1.5
                    grid_points.append(np.array([x, 0, z]))
            
            projected = camera.project(grid_points)
            
            # Draw grid lines (horizontal)
            for i in range(grid_size + 1):
                for j in range(grid_size):
                    idx1 = i * (grid_size + 1) + j
                    idx2 = i * (grid_size + 1) + j + 1
                    if projected[idx1] and projected[idx2]:
                        pygame.draw.line(surface, GRID_COLOR, 
                                       (projected[idx1][0], projected[idx1][1]),
                                       (projected[idx2][0], projected[idx2][1]), 1)
            
            # Draw grid lines (vertical)
            for j in range(grid_size + 1):
                for i in range(grid_size):
                    idx1 = i * (grid_size + 1) + j
                    idx2 = (i + 1) * (grid_size + 1) + j
                    if projected[idx1] and projected[idx2]:
                        pygame.draw.line(surface, GRID_COLOR,
                                       (projected[idx1][0], projected[idx1][1]),
                                       (projected[idx2][0], projected[idx2][1]), 1)
    
    def draw_2d(self, surface, font, small_font):
        # Quantum kernel matrix - RIGHT SIDE, SMALLER FONT
        panel_w, panel_h = 380, 580
        panel_x = W - panel_w - 20  # Right side with margin
        panel_y = 120
        
        pygame.draw.rect(surface, (20, 25, 35), (panel_x, panel_y, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(surface, QUANTUM_CYAN, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=8)
        
        title = font.render("Quantum Kernel Matrix", True, TEXT_COLOR)
        title_rect = title.get_rect(center=(panel_x + panel_w // 2, panel_y + 15))
        surface.blit(title, title_rect)
        
        desc = small_font.render(f"K(x,x') = |⟨{GREEK_PSI}(x)|{GREEK_PSI}(x')⟩|²", True, HIGHLIGHT)
        desc_rect = desc.get_rect(center=(panel_x + panel_w // 2, panel_y + 32))
        surface.blit(desc, desc_rect)
        
        # Compute kernel matrix
        pattern_names = list(self.patterns.keys())
        n = len(pattern_names)
        kernel_matrix = np.zeros((n, n))
        
        for i, name1 in enumerate(pattern_names):
            for j, name2 in enumerate(pattern_names):
                state1 = self.patterns[name1]["state"]
                state2 = self.patterns[name2]["state"]
                overlap = np.abs(np.vdot(state1, state2)) ** 2
                kernel_matrix[i, j] = overlap
        
        # Draw matrix - SMALLER CELLS
        cell_size = 40  # Reduced from 45
        matrix_w = n * cell_size
        matrix_x = panel_x + (panel_w - matrix_w) // 2
        matrix_y = panel_y + 55
        
        # Column labels - SMALLER FONT
        tiny_font = pygame.font.SysFont("consolas", 9)
        for j, name in enumerate(pattern_names):
            short_name = name.split()[0][:4]
            label = tiny_font.render(short_name, True, TEXT_COLOR)
            label_rect = label.get_rect(center=(matrix_x + j * cell_size + cell_size // 2, matrix_y - 10))
            surface.blit(label, label_rect)
        
        # Draw cells
        for i in range(n):
            # Row label - SMALLER FONT
            short_name = pattern_names[i].split()[0][:4]
            label = tiny_font.render(short_name, True, TEXT_COLOR)
            label_rect = label.get_rect(center=(matrix_x - 25, matrix_y + i * cell_size + cell_size // 2))
            surface.blit(label, label_rect)
            
            for j in range(n):
                value = kernel_matrix[i, j]
                
                # Cell color based on value
                intensity = int(value * 200)
                cell_color = (intensity // 2, intensity, intensity)
                
                cell_rect = (matrix_x + j * cell_size, matrix_y + i * cell_size, cell_size - 2, cell_size - 2)
                pygame.draw.rect(surface, cell_color, cell_rect, border_radius=3)
                pygame.draw.rect(surface, (100, 100, 120), cell_rect, 1, border_radius=3)
                
                # Value text - SMALLER FONT
                val_text = tiny_font.render(f"{value:.2f}", True, TEXT_COLOR if value < 0.5 else (0, 0, 0))
                text_rect = val_text.get_rect(center=(matrix_x + j * cell_size + cell_size // 2, 
                                                       matrix_y + i * cell_size + cell_size // 2))
                surface.blit(val_text, text_rect)
        
        # Color Legend
        y_offset = matrix_y + n * cell_size + 20
        legend_title = font.render("Color Legend:", True, HIGHLIGHT)
        legend_rect = legend_title.get_rect(center=(panel_x + panel_w // 2, panel_y + y_offset))
        surface.blit(legend_title, legend_rect)
        y_offset += 22
        
        # Color gradient samples
        gradient_w = 180
        gradient_h = 15
        gradient_x = panel_x + (panel_w - gradient_w) // 2
        gradient_y = panel_y + y_offset
        
        # Draw gradient
        for i in range(gradient_w):
            value = i / gradient_w
            intensity = int(value * 200)
            color = (intensity // 2, intensity, intensity)
            pygame.draw.line(surface, color, (gradient_x + i, gradient_y), (gradient_x + i, gradient_y + gradient_h))
        
        pygame.draw.rect(surface, (100, 100, 120), (gradient_x, gradient_y, gradient_w, gradient_h), 2, border_radius=2)
        
        # Labels - SMALLER FONT
        low_label = tiny_font.render("0.0 (Different)", True, TEXT_COLOR)
        high_label = tiny_font.render("1.0 (Identical)", True, TEXT_COLOR)
        low_rect = low_label.get_rect(center=(gradient_x + 35, gradient_y + gradient_h + 10))
        high_rect = high_label.get_rect(center=(gradient_x + gradient_w - 35, gradient_y + gradient_h + 10))
        surface.blit(low_label, low_rect)
        surface.blit(high_label, high_rect)
        
        y_offset += gradient_h + 30
        
        # Interpretation - SMALLER FONT
        interp_lines = [
            "Interpretation:",
            "Diagonal = 1.0 (same state)",
            "Low = distinguishable",
            "High = similar states",
            "Used for classification"
        ]
        
        for line in interp_lines:
            if line.startswith("Interpretation"):
                text = font.render(line, True, HIGHLIGHT)
            else:
                text = small_font.render("  " + line, True, QUANTUM_CYAN if not line.startswith("Interpretation") else TEXT_COLOR)
            text_rect = text.get_rect(center=(panel_x + panel_w // 2, panel_y + y_offset))
            surface.blit(text, text_rect)
            y_offset += 16 if line.startswith("Interpretation") else 14


# ══════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════

class QuantumVisualizationApp:
    """Main application controller."""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Mind Link — Quantum 3D Visualization")
        self.clock = pygame.time.Clock()
        
        self.font = pygame.font.SysFont("consolas", 16, bold=True)  # Reduced from 20
        self.small_font = pygame.font.SysFont("consolas", 11)  # Reduced from 14
        self.title_font = pygame.font.SysFont("consolas", 26, bold=True)  # Reduced from 32
        
        self.camera = Camera3D(distance=20.0)
        self.quantum_gen = QuantumStateGenerator(n_qubits=4, reps=2)
        
        self.current_pattern = "Left Hand"
        self.current_stage_idx = 0
        self.stages = []
        self.paused = False
        self.mouse_dragging = False
        self.last_mouse_pos = None
        
        self._build_stages()
        
        print("\n" + "="*70)
        print("QUANTUM 3D VISUALIZATION")
        print("="*70)
        print("\nControls:")
        print("  SPACE       — Next step / Play animation")
        print("  R           — Reset to beginning")
        print("  C           — Toggle auto-rotate camera")
        print("  Mouse drag  — Rotate view")
        print("  Scroll      — Zoom in/out")
        print("  1-4         — Jump to motor imagery pattern")
        print("  P           — Pause/Resume")
        print("  ESC         — Quit")
        print("\nStarting visualization...")
        print("="*70 + "\n")
    
    def _build_stages(self):
        """Build visualization stages for current pattern."""
        pattern_data = MOTOR_IMAGERY_PATTERNS[self.current_pattern]
        
        self.stages = [
            Stage1_EEGSignal(self.current_pattern, pattern_data),
            Stage2_FeatureExtraction(self.current_pattern, pattern_data),
            Stage3_QuantumEncoding(self.current_pattern, pattern_data, self.quantum_gen),
            Stage4_HilbertSpace(self.current_pattern, pattern_data, self.quantum_gen),
            Stage5_Comparison(self.quantum_gen)
        ]
        self.current_stage_idx = 0
    
    def change_pattern(self, pattern_name):
        """Switch to different motor imagery pattern."""
        if pattern_name in MOTOR_IMAGERY_PATTERNS:
            self.current_pattern = pattern_name
            self._build_stages()
            print(f"\n[viz] Switched to: {pattern_name}")
    
    def next_stage(self):
        """Advance to next stage."""
        if self.current_stage_idx < len(self.stages) - 1:
            self.current_stage_idx += 1
            print(f"\n[viz] Stage {self.current_stage_idx + 1}: {self.stages[self.current_stage_idx].title}")
    
    def reset(self):
        """Reset to first stage."""
        self._build_stages()
        print("\n[viz] Reset to beginning")
    
    def handle_events(self):
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.next_stage()
                elif event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_c:
                    self.camera.auto_rotate = not self.camera.auto_rotate
                    print(f"[viz] Auto-rotate: {'ON' if self.camera.auto_rotate else 'OFF'}")
                elif event.key == pygame.K_p:
                    self.paused = not self.paused
                    print(f"[viz] {'Paused' if self.paused else 'Resumed'}")
                elif event.key == pygame.K_1:
                    self.change_pattern("Left Hand")
                elif event.key == pygame.K_2:
                    self.change_pattern("Right Hand")
                elif event.key == pygame.K_3:
                    self.change_pattern("Rest")
                elif event.key == pygame.K_4:
                    self.change_pattern("Both Hands")
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_dragging = True
                    self.last_mouse_pos = event.pos
                elif event.button == 4:  # Scroll up
                    self.camera.zoom(-1.0)
                elif event.button == 5:  # Scroll down
                    self.camera.zoom(1.0)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.mouse_dragging and self.last_mouse_pos:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    
                    # Check if dragging in center area (3D visualization)
                    # Center area is roughly x: 200-900, y: 150-750
                    if 200 < event.pos[0] < 900 and 150 < event.pos[1] < 750:
                        # Pan the 3D view
                        self.camera.pan(dx, dy)
                    else:
                        # Rotate camera (when dragging outside center)
                        self.camera.rotate(dx * 0.5, dy * 0.5)
                    
                    self.last_mouse_pos = event.pos
        
        return True
    
    def update(self, dt):
        """Update animation."""
        if not self.paused:
            self.camera.update(dt)
            self.stages[self.current_stage_idx].update(dt)
    
    def draw(self):
        """Render frame."""
        self.screen.fill(BG)
        
        # Draw current stage
        stage = self.stages[self.current_stage_idx]
        
        # 3D elements
        stage.draw_3d(self.screen, self.camera)
        
        # 2D overlay
        stage.draw_2d(self.screen, self.font, self.small_font)
        
        # Header
        self._draw_header(stage)
        
        # Footer controls
        self._draw_footer()
        
        pygame.display.flip()
    
    def _draw_header(self, stage):
        """Draw header with title and description."""
        # Title bar
        header_h = 120
        pygame.draw.rect(self.screen, (15, 18, 28), (0, 0, W, header_h))
        pygame.draw.rect(self.screen, QUANTUM_CYAN, (0, header_h - 2, W, 2))
        
        # Title
        title = self.title_font.render(stage.title, True, HIGHLIGHT)
        self.screen.blit(title, (20, 15))
        
        # Description
        y_offset = 55
        for line in stage.description.split('\n'):
            text = self.small_font.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (20, y_offset))
            y_offset += 20
        
        # Stage indicator
        stage_text = f"Stage {self.current_stage_idx + 1} / {len(self.stages)}"
        stage_surf = self.font.render(stage_text, True, QUANTUM_CYAN)
        self.screen.blit(stage_surf, (W - 200, 20))
        
        # Pattern indicator
        pattern_text = f"Motor Imagery: {self.current_pattern}"
        pattern_surf = self.small_font.render(pattern_text, True, MOTOR_IMAGERY_PATTERNS[self.current_pattern]["color"])
        self.screen.blit(pattern_surf, (W - 250, 50))
    
    def _draw_footer(self):
        """Draw footer with controls."""
        footer_h = 60
        footer_y = H - footer_h
        
        pygame.draw.rect(self.screen, (15, 18, 28), (0, footer_y, W, footer_h))
        pygame.draw.rect(self.screen, QUANTUM_CYAN, (0, footer_y, W, 2))
        
        controls = [
            "SPACE: Next",
            "R: Reset",
            "C: Auto-Rotate",
            "Drag: Pan View",
            "1-4: Patterns",
            "ESC: Quit"
        ]
        
        x_offset = 20
        for ctrl in controls:
            text = self.small_font.render(ctrl, True, TEXT_COLOR)
            self.screen.blit(text, (x_offset, footer_y + 20))
            x_offset += text.get_width() + 30
        
        # Camera info
        cam_text = f"Camera: Az={self.camera.azimuth:.0f}deg El={self.camera.elevation:.0f}deg Dist={self.camera.distance:.1f}"
        cam_surf = self.small_font.render(cam_text, True, (150, 150, 170))
        self.screen.blit(cam_surf, (W - 450, footer_y + 20))
    
    def run(self):
        """Main loop."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            running = self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        print("\n[viz] Visualization ended\n")


# ══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def main():
    """Run the quantum 3D visualization."""
    if not QISKIT_AVAILABLE:
        print("\n⚠ Warning: Qiskit not found. Using mock quantum states.")
        print("For real quantum simulation, install: pip install qiskit qiskit-aer\n")
    
    app = QuantumVisualizationApp()
    app.run()


if __name__ == "__main__":
    main()
