"""
Mind Link — High-Fidelity 3D Drone Simulator (Ursina Engine)
===========================================================
Advanced 3D rendering with infinite grid, lighting, and 3D entities.
Supports BCI input and manual clickable overrides.

Install: pip install ursina
Run: python mindlink/drone_control/sim_ursina.py
"""

import sys
import os
import math
import time
import numpy as np
from collections import deque
from ursina import *
from ursina.prefabs.health_bar import HealthBar
from ursina.prefabs.window_panel import WindowPanel
from ursina.prefabs.first_person_controller import FirstPersonController

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── Import Shared BCI Logic ──────────────────────────────────────────
# We reuse the robust logic from sim3d.py
from mindlink.drone_control.sim3d import EEGSource, BCIDecoder, SignalMapping, DRONE_ACTIONS

# ── Configuration ────────────────────────────────────────────────────
CYAN = color.cyan
PURPLE = color.magenta
GOLD = color.gold
DARK_BG = color.hex("#050812")
GRID_COLOR = color.hex("#00b4d2")

# ── Drone Entity ─────────────────────────────────────────────────────

class Drone(Entity):
    def __init__(self, **kwargs):
        super().__init__(model='cube', color=color.gray, scale=(1, 0.2, 1.2), **kwargs)
        
        # Body Visuals
        self.body = Entity(parent=self, model='cube', color=color.hex("#1e78dc"), scale=(0.8, 1, 0.8))
        self.canopy = Entity(parent=self, model='sphere', color=color.cyan, scale=(0.6, 1.5, 0.5), y=0.5, alpha=0.6)
        
        # Arms
        self.arms = []
        for i, pos in enumerate([(1,0,1), (-1,0,1), (1,0,-1), (-1,0,-1)]):
            arm = Entity(parent=self, model='cube', color=color.dark_gray, 
                         position=(pos[0]*0.5, 0, pos[2]*0.5), 
                         scale=(1.2, 0.2, 0.1), rotation_y=45 if i%2==0 else -45)
            self.arms.append(arm)
            
            # Rotors
            rotor = Entity(parent=arm, model='sphere', color=color.black, 
                           position=(0.5 if pos[0]>0 else -0.5, 0.1, 0), scale=(0.8, 0.1, 0.8))
            
            # Blades
            blade = Entity(parent=rotor, model='cube', color=color.red if pos[2]>0 else color.green,
                           scale=(1.2, 0.1, 0.1))
            rotor.blade = blade
            arm.rotor = rotor

        # Landing Skids
        Entity(parent=self, model='cube', color=color.gray, position=(0.5, -0.4, 0), scale=(0.1, 0.1, 1.2))
        Entity(parent=self, model='cube', color=color.gray, position=(-0.5, -0.4, 0), scale=(0.1, 0.1, 1.2))
        
        # Physics State
        self.vx = self.vy = self.vz = 0
        self.target_pitch = 0
        self.target_roll = 0
        self.DRAG = 0.95
        self.THRUST = 20
        self.MOVE_SPEED = 15
        self.flying = False

    def update(self):
        if not self.flying:
            return

        # Spin rotors
        for arm in self.arms:
            arm.rotor.blade.rotation_y += 50

        # Apply physics
        self.x += self.vx * time.dt
        self.y += self.vy * time.dt
        self.z += self.vz * time.dt
        
        # Smooth Tilt
        self.rotation_x = lerp(self.rotation_x, self.target_pitch, time.dt * 5)
        self.rotation_z = lerp(self.rotation_z, self.target_roll, time.dt * 5)
        
        # Dampen velocity
        self.vx *= self.DRAG
        self.vy *= self.DRAG
        self.vz *= self.DRAG

# ── HUD Interface ────────────────────────────────────────────────────

class BCI_HUD(Entity):
    def __init__(self, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        
        # Panels
        self.left_panel = WindowPanel(title='◈ FLIGHT DATA', content=[], 
                                      position=(-0.7, 0.4), scale=(0.2, 0.4))
        self.right_panel = WindowPanel(title='◈ NEURAL INPUT', content=[], 
                                       position=(0.5, 0.4), scale=(0.3, 0.6))
        
        # Labels
        self.alt_label = Text(text='ALT: 0.0m', parent=self.left_panel, position=(0.1, -0.1), scale=0.8)
        self.mode_label = Text(text='MODE: IDLE', parent=self.left_panel, position=(0.1, -0.2), scale=0.8)
        
        self.intent_label = Text(text='INTENT: HOVER', parent=self.right_panel, position=(0.1, -0.1), color=color.green)
        self.conf_bar = HealthBar(max_value=1.0, value=0.5, parent=self.right_panel, position=(0.1, -0.2), scale=(0.8, 0.05))
        
        # Clickable Signal Bars
        self.signal_bars = []
        labels = [("C3 μ (LEFT)", 2), ("C4 μ (RIGHT)", 3), ("C3 β (FORWARD)", 0), ("C4 β (HOVER)", 4)]
        
        for i, (name, intent_id) in enumerate(labels):
            btn = Button(text=name, parent=self.right_panel, position=(0.1, -0.35 - i*0.1), 
                         scale=(0.8, 0.08), color=color.black66)
            btn.intent_id = intent_id
            btn.on_click = lambda i=intent_id: self.on_bar_click(i)
            self.signal_bars.append(btn)
            
            # Mini bar inside button
            bar = Entity(parent=btn, model='quad', color=color.cyan, scale=(0, 0.2), x=-0.45, y=-0.3)
            btn.progress_bar = bar

        self.override_intent = -1

    def on_bar_click(self, intent_id):
        self.override_intent = intent_id
        print(f"[hud] Manual Override: {intent_id}")

    def update_data(self, state, bci_label, bci_conf, features):
        self.alt_label.text = f"ALT: {state.y:.1f}m"
        self.mode_label.text = f"MODE: {state.mode}"
        self.intent_label.text = f"INTENT: {bci_label}"
        self.conf_bar.value = bci_conf
        
        # Update mini bars
        feats = [features.get('c3_mu', 0), features.get('c4_mu', 0), 
                 features.get('c3_beta', 0), features.get('c4_beta', 0)]
        for i, val in enumerate(feats):
            self.signal_bars[i].progress_bar.scale_x = min(1.0, val/1.5)

# ── Main Application ─────────────────────────────────────────────────

app = Ursina()

# Environment
Sky(color=color.black)
grid = Entity(model=Grid(100, 100), rotation_x=90, scale=1000, color=GRID_COLOR, alpha=0.3)
floor = Entity(model='plane', scale=2000, color=DARK_BG, collider='box')

# Drone & Logic
drone = Drone(y=0.1)
state = drone # Shared state for simplicity
state.mode = "IDLE"

eeg = EEGSource()
decoder = BCIDecoder()
sig_map = SignalMapping()
hud = BCI_HUD()

# Camera
EditorCamera() # Allow free look
camera.position = (0, 10, -20)
camera.rotation_x = 25

def update():
    dt = time.dt
    
    # ── BCI Logic ─────────────────────────────────────────────────────
    win = eeg.get_window(80)
    intent, label, conf, feat = decoder.decode(win)
    
    # Check Manual Override
    if hud.override_intent != -1:
        intent = hud.override_intent
        label = sig_map.INTENT_NAMES[intent]
        conf = 1.0
        hud.override_intent = -1 # Reset
    
    hud.update_data(state, label, conf, feat)
    
    # ── Controls ──────────────────────────────────────────────────────
    pitch = roll = yaw = throttle = 0
    
    if held_keys['t']:
        drone.flying = True
        state.mode = "FLYING"
        drone.vy = 2
    if held_keys['l']:
        state.mode = "LANDING"
        drone.vy = -1.5
    if held_keys['space']:
        drone.vx = drone.vy = drone.vz = 0
        state.mode = "HOVER"

    # Merge Input
    if drone.flying and conf > 0.45:
        p, r, y, t = sig_map.get_command(intent)
        drone.target_pitch = p * 15
        drone.target_roll = r * 15
        drone.vx += r * drone.MOVE_SPEED * dt
        drone.vz += p * drone.MOVE_SPEED * dt
        drone.vy += t * drone.THRUST * dt

    # Ground Check
    if drone.y < 0.1:
        drone.y = 0.1
        drone.vy = 0
        if state.mode == "LANDING":
            drone.flying = False
            state.mode = "IDLE"

def input(key):
    if key == 'escape':
        quit()

app.run()
