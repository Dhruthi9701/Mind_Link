"""
Mind Link — 3D Drone Simulator (pygame + software 3D renderer)
================================================================
Pure pygame — no Ursina, no OpenGL. Custom 3D projection gives
full control: world stays fixed, only drone moves.

Install: pip install pygame scipy numpy

Run:
    python drone_control/sim3d.py
    python drone_control/sim3d.py --no-bci
    python drone_control/sim3d.py --backend tello

Controls:
    T / L       — Takeoff / Land
    SPACE       — Hover (kill velocity)
    W / S       — Throttle up / down
    A / D       — Yaw left / right
    Arrows      — Pitch / Roll
    B           — Toggle BCI
    C           — Cycle camera angle
    ESC         — Quit
"""

import sys, os, math, time, argparse
import numpy as np
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pygame
except ImportError:
    print("pip install pygame"); sys.exit(1)

# ── colours ────────────────────────────────────────────────────────────
BG          = (4,   6,  14)
CYAN        = (0,  220, 255)
CYAN_DIM    = (0,  100, 130)
PURPLE      = (160,  60, 255)
PURPLE_DIM  = ( 70,  20, 120)
ORANGE      = (255, 140,   0)
GREEN       = ( 40, 255, 120)
RED         = (255,  50,  50)
WHITE       = (255, 255, 255)
GREY        = ( 80,  90, 110)
YELLOW      = (255, 220,   0)
GRID_MAJOR  = (  0, 150, 200, 100)   # dimmer cyan, semi-transparent
GRID_MINOR  = (  0,  60,  90,  50)   # very faint minor lines
DRONE_BODY  = ( 30, 120, 220)
DRONE_ARM   = ( 20,  60, 100)
ROTOR_A     = (255,  60,  60)
ROTOR_B     = ( 40, 255, 120)
TRAIL_COL   = (  0, 200, 255)

W, H = 1280, 720

# ══════════════════════════════════════════════════════════════════════
# 3-D CAMERA / PROJECTION
# ══════════════════════════════════════════════════════════════════════

class Camera3D:
    """
    Orbit camera — always looks at the drone.
    Yaw/pitch controlled by preset angles (C key cycles) or mouse drag.
    World never rotates — only the viewpoint changes.
    """
    PRESETS = [
        (30,  -25),   # follow-behind low
        (30,  -55),   # high angle
        (0,   -90),   # top-down
        (90,  -20),   # side view
    ]
    PRESET_NAMES = ["FOLLOW", "HIGH", "TOP-DOWN", "SIDE"]

    def __init__(self):
        self._preset = 1            # start on HIGH so grid is visible
        self.dist    = 22.0         # camera distance (zoom-able)
        self.dist_min = 8.0
        self.dist_max = 80.0
        self.fov     = 500
        self._az, self._el = self.PRESETS[self._preset]

    @property
    def name(self):
        if self._preset == -1: return "FREE"
        return self.PRESET_NAMES[self._preset]

    def cycle(self):
        if self._preset == -1:
            self._preset = 0
        else:
            self._preset = (self._preset + 1) % len(self.PRESETS)
        self._az, self._el = self.PRESETS[self._preset]

    def zoom(self, delta):
        """delta > 0 = zoom in, delta < 0 = zoom out."""
        self.dist = max(self.dist_min, min(self.dist_max, self.dist - delta * 3.0))

    def rotate(self, dx, dy):
        """Rotate camera based on mouse movement."""
        self._preset = -1  # free camera
        self._az = (self._az - dx * 0.5) % 360
        self._el = max(-179.9, min(89.9, self._el - dy * 0.5))

    def project(self, world_pts, drone_pos):
        """
        Project list of (x,y,z) world points to screen (sx,sy,depth).
        Camera orbits around drone_pos.
        """
        az  = math.radians(self._az)
        el  = math.radians(self._el)

        # Camera position in world space
        cx = drone_pos[0] + self.dist * math.cos(el) * math.sin(az)
        cy = drone_pos[1] - self.dist * math.sin(el)
        cz = drone_pos[2] + self.dist * math.cos(el) * math.cos(az)

        # Forward vector (camera → target)
        fx = drone_pos[0] - cx
        fy = drone_pos[1] - cy
        fz = drone_pos[2] - cz
        fl = math.sqrt(fx*fx + fy*fy + fz*fz) + 1e-9
        fx /= fl; fy /= fl; fz /= fl

        # Right vector (cross forward × world-up)
        ux, uy, uz = 0, 1, 0
        rx = fy*uz - fz*uy
        ry = fz*ux - fx*uz
        rz = fx*uy - fy*ux
        rl = math.sqrt(rx*rx + ry*ry + rz*rz) + 1e-9
        rx /= rl; ry /= rl; rz /= rl

        # Up vector (cross right × forward)
        upx = ry*fz - rz*fy
        upy = rz*fx - rx*fz
        upz = rx*fy - ry*fx

        results = []
        for (wx, wy, wz) in world_pts:
            dx = wx - cx; dy = wy - cy; dz = wz - cz
            # Camera-space coords
            cam_x = dx*rx + dy*ry + dz*rz
            cam_y = dx*upx + dy*upy + dz*upz
            cam_z = dx*fx  + dy*fy  + dz*fz
            if cam_z < 0.1:
                results.append(None)
                continue
            sx = int(W//2 + cam_x * self.fov / cam_z)
            sy = int(H//2 - cam_y * self.fov / cam_z)
            results.append((sx, sy, cam_z))
        return results


# ══════════════════════════════════════════════════════════════════════
# WORLD GEOMETRY
# ══════════════════════════════════════════════════════════════════════

def make_grid(size=100, step=5):
    """Return list of (p1, p2, colour, width) line segments for the grid."""
    lines = []
    chunk = 20  # Break long lines into chunks to prevent whole-line clipping
    for i in range(-size, size+1, step):
        # major every 25, minor every 5
        is_major = (i % 25 == 0)
        col   = GRID_MAJOR[:3] if is_major else GRID_MINOR[:3]
        alpha = GRID_MAJOR[3]  if is_major else GRID_MINOR[3]
        w     = 2 if is_major else 1   # slightly thinner major lines
        for j in range(-size, size, chunk):
            lines.append(((i, 0, j), (i, 0, j+chunk), col, alpha, w))
            lines.append(((j, 0, i), (j+chunk, 0, i), col, alpha, w))
    return lines


def make_buildings():
    """Return list of box wireframes for distant buildings (pushed further out)."""
    defs = [
        ( 90, 0,  55,  5, 18, 5),
        (100, 0,  32,  3, 10, 3),
        (-82, 0,  72,  6, 22, 6),
        (-90, 0,  40,  4, 14, 4),
        (110, 0, -45,  7, 28, 7),
        (-99, 0, -54,  5, 16, 5),
        ( 72, 0, -90,  6, 20, 6),
        (-54, 0, -81,  4, 12, 4),
    ]
    buildings = []
    for (bx, by, bz, sw, sh, sd) in defs:
        x0, x1 = bx - sw/2, bx + sw/2
        y0, y1 = 0, sh
        z0, z1 = bz - sd/2, bz + sd/2
        corners = [
            (x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
            (x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1),
        ]
        edges = [
            (0,1),(1,2),(2,3),(3,0),   # bottom
            (4,5),(5,6),(6,7),(7,4),   # top
            (0,4),(1,5),(2,6),(3,7),   # verticals
        ]
        # window rows
        win_rows = []
        for wy in range(2, sh-1, 3):
            win_rows.append(wy)
        buildings.append((corners, edges, win_rows, bx, bz, sw, sd, sh))
    return buildings


GRID_LINES = make_grid()
BUILDINGS  = make_buildings()

# Landing pad corners (flat square at y=0)
PAD_SIZE = 4
PAD = [
    (-PAD_SIZE, 0, -PAD_SIZE), ( PAD_SIZE, 0, -PAD_SIZE),
    ( PAD_SIZE, 0,  PAD_SIZE), (-PAD_SIZE, 0,  PAD_SIZE),
]


# ══════════════════════════════════════════════════════════════════════
# DRONE GEOMETRY  (local coords, centred at origin)
# ══════════════════════════════════════════════════════════════════════

ARM_LEN  = 2.0
ROTOR_R  = 0.9
BODY_W   = 0.7    # half-width of body plate
BODY_L   = 0.8    # half-length of body plate
LEG_DROP = 0.6    # how far landing gear drops below body
LEG_SPREAD = 1.0  # lateral spread of landing gear

def drone_points(yaw_deg, pitch_deg, roll_deg):
    """
    Return all 3-D points for the drone in local space,
    rotated by yaw/pitch/roll.
    Returns: (centre, arms, body_corners, canopy, leg_tops, leg_bottoms, front_cam)
    """
    ya = math.radians(yaw_deg)
    pa = math.radians(pitch_deg)
    ra = math.radians(roll_deg)

    def rot(p):
        x, y, z = p
        # yaw (around Y)
        x2 = x*math.cos(ya) + z*math.sin(ya)
        z2 = -x*math.sin(ya) + z*math.cos(ya)
        x, z = x2, z2
        # pitch (around X)
        y2 = y*math.cos(pa) - z*math.sin(pa)
        z2 = y*math.sin(pa) + z*math.cos(pa)
        y, z = y2, z2
        # roll (around Z)
        x2 = x*math.cos(ra) - y*math.sin(ra)
        y2 = x*math.sin(ra) + y*math.cos(ra)
        return (x2, y2, z)

    centre = (0, 0, 0)

    # 4 motor positions (X-frame)
    arms = [
        rot(( ARM_LEN,  0,  ARM_LEN)),   # front-right
        rot((-ARM_LEN,  0,  ARM_LEN)),   # front-left
        rot(( ARM_LEN,  0, -ARM_LEN)),   # back-right
        rot((-ARM_LEN,  0, -ARM_LEN)),   # back-left
    ]

    # Body plate corners (octagonal)
    bw, bl = BODY_W, BODY_L
    body_corners = [
        rot(( bw,  0.05,  bl)), rot((-bw,  0.05,  bl)),
        rot((-bw*1.4, 0.05, 0)), rot((-bw,  0.05, -bl)),
        rot(( bw,  0.05, -bl)), rot(( bw*1.4, 0.05, 0)),
    ]
    # Top canopy
    canopy = [
        rot(( bw*0.7, 0.22, bl*0.5)), rot((-bw*0.7, 0.22, bl*0.5)),
        rot((-bw*0.7, 0.22, -bl*0.5)), rot(( bw*0.7, 0.22, -bl*0.5)),
    ]

    # Landing gear: 2 skid bars, each with front+back contact points
    leg_tops = [
        rot(( LEG_SPREAD,  0,  BODY_L*0.7)),   # right-front top
        rot(( LEG_SPREAD,  0, -BODY_L*0.7)),   # right-back top
        rot((-LEG_SPREAD,  0,  BODY_L*0.7)),   # left-front top
        rot((-LEG_SPREAD,  0, -BODY_L*0.7)),   # left-back top
    ]
    leg_bottoms = [
        rot(( LEG_SPREAD, -LEG_DROP,  BODY_L*0.9)),   # right-front bottom
        rot(( LEG_SPREAD, -LEG_DROP, -BODY_L*0.9)),   # right-back bottom
        rot((-LEG_SPREAD, -LEG_DROP,  BODY_L*0.9)),   # left-front bottom
        rot((-LEG_SPREAD, -LEG_DROP, -BODY_L*0.9)),   # left-back bottom
    ]

    # Front camera pod
    front_cam = rot((0, -0.1, BODY_L + 0.15))

    return centre, arms, body_corners, canopy, leg_tops, leg_bottoms, front_cam


def rotor_ring_pts(cx, cy, cz, r, n=12):
    """Circle of n points around a rotor centre."""
    pts = []
    for i in range(n):
        a = 2*math.pi * i / n
        pts.append((cx + r*math.cos(a), cy, cz + r*math.sin(a)))
    return pts


# ══════════════════════════════════════════════════════════════════════
# EEG SOURCE
# ══════════════════════════════════════════════════════════════════════

class EEGSource:
    _ANNOT = {"T0": 4, "T1": 2, "T2": 3}

    def __init__(self, use_real=False):
        self.use_real = use_real
        self.fs = 160; self.n_channels = 64
        self._bridge = None
        self._data = None; self._labels = None
        self._cursor = 0
        self.c3_idx = 7; self.c4_idx = 11
        self.current_intent = 4
        if use_real:
            try:
                from input.itie_bridge import ItieBridge
                self._bridge = ItieBridge(); self._bridge.connect(); self._bridge.start_stream()
                print("[eeg] Real headset connected")
            except Exception as e:
                print(f"[eeg] {e} — dataset replay"); self.use_real = False
        if not self.use_real:
            self._load()

    def _load(self):
        try:
            import mne; mne.set_log_level("WARNING")
        except ImportError:
            self._fallback(); return
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "mindlink","data","physionet","MNE-eegbci-data",
                            "files","eegmmidb","1.0.0","S001")
        all_d, all_l = [], []
        for f in ["S001R04.edf","S001R08.edf","S001R12.edf"]:
            fp = os.path.join(base, f)
            if not os.path.exists(fp): continue
            try:
                raw = mne.io.read_raw_edf(fp, preload=True, verbose=False)
                raw.filter(1., 40., fir_design="firwin", verbose=False)
                ch = [c.upper().strip('.') for c in raw.ch_names]
                self.c3_idx = next((i for i,c in enumerate(ch) if c=="C3"), 7)
                self.c4_idx = next((i for i,c in enumerate(ch) if c=="C4"), 11)
                self.fs = int(raw.info["sfreq"]); self.n_channels = len(raw.ch_names)
                d = raw.get_data().T * 1e6
                lb = np.full(len(d), 4, dtype=int)
                for ann in raw.annotations:
                    intent = self._ANNOT.get(ann["description"].strip(), 4)
                    s = int(ann["onset"]*self.fs); e = s+int(ann["duration"]*self.fs)
                    lb[s:e] = intent
                all_d.append(d); all_l.append(lb)
                print(f"[eeg] Loaded {f}")
            except Exception as ex: print(f"[eeg] {f}: {ex}")
        if all_d:
            self._data = np.concatenate(all_d); self._labels = np.concatenate(all_l)
            print(f"[eeg] {len(self._data)} samples ready")
        else: self._fallback()

    def _fallback(self):
        self.fs=250; self.n_channels=32; self.c3_idx=7; self.c4_idx=11

    def get_window(self, n=80):
        if self.use_real and self._bridge:
            w = self._bridge.get_window(n)
            if w is not None: return w["eeg"]
        if self._data is not None:
            total = len(self._data); end = self._cursor+n
            if end <= total:
                win = self._data[self._cursor:end]
                self.current_intent = int(np.bincount(self._labels[self._cursor:end]).argmax())
                self._cursor = end
            else:
                p1=self._data[self._cursor:]; p2=self._data[:n-len(p1)]
                win=np.concatenate([p1,p2]); self.current_intent=4; self._cursor=n-len(p1)
            return win
        # synthetic fallback
        t = np.linspace(0, n/self.fs, n)
        eeg = np.random.randn(n, self.n_channels)*3.
        intent = (self._cursor//(self.fs*3))%5; self.current_intent=intent; self._cursor+=n
        c3,c4 = self.c3_idx, self.c4_idx
        if intent==2: eeg[:,c3]+=18*np.sin(2*np.pi*10*t); eeg[:,c4]+=5*np.sin(2*np.pi*10*t)
        elif intent==3: eeg[:,c3]+=5*np.sin(2*np.pi*10*t); eeg[:,c4]+=18*np.sin(2*np.pi*10*t)
        else: eeg[:,c3]+=15*np.sin(2*np.pi*18*t); eeg[:,c4]+=15*np.sin(2*np.pi*18*t)
        return eeg

    def stop(self):
        if self._bridge: self._bridge.stop_stream()


# ══════════════════════════════════════════════════════════════════════
# BCI DECODER
# ══════════════════════════════════════════════════════════════════════

class BCIDecoder:
    LABELS = {0:"Forward",1:"Backward",2:"Left",3:"Right",4:"Hover"}
    def __init__(self, fs=160, c3=7, c4=11):
        self.fs=fs; self.c3=c3; self.c4=c4; self._hist=deque(maxlen=5)
    def decode(self, eeg):
        from scipy.signal import welch
        def bp(sig,lo,hi):
            f,p=welch(sig,fs=self.fs,nperseg=min(128,len(sig)))
            m=(f>=lo)&(f<=hi); return float(np.mean(p[m])) if m.any() else 0.
        c3=eeg[:,self.c3]; c4=eeg[:,self.c4]
        c3m=bp(c3,8,13); c4m=bp(c4,8,13); c3b=bp(c3,13,30); c4b=bp(c4,13,30)
        asym=(c3m-c4m)/(c3m+c4m+1e-9); bavg=(c3b+c4b)/2; mavg=(c3m+c4m)/2
        feat=dict(c3_mu=c3m,c4_mu=c4m,c3_beta=c3b,c4_beta=c4b,mu_asym=asym,beta_avg=bavg)
        ASYM=0.10; BETA=0.3; MU=0.2
        if bavg>BETA and mavg<MU: intent,conf=4,0.80
        elif asym>ASYM:  intent,conf=2,min(0.95,0.6+abs(asym))
        elif asym<-ASYM: intent,conf=3,min(0.95,0.6+abs(asym))
        elif mavg>MU and bavg<BETA: intent,conf=0,0.70
        elif bavg>BETA*0.6: intent,conf=1,0.65
        else: intent,conf=4,0.55
        self._hist.append(intent)
        smoothed=max(set(self._hist),key=list(self._hist).count)
        return smoothed,self.LABELS[smoothed],conf,feat

# ══════════════════════════════════════════════════════════════════════
# NEURAL SIGNAL MAPPING (user-configurable)
# ══════════════════════════════════════════════════════════════════════

# Available drone actions — each is (pitch, roll, yaw, throttle)
DRONE_ACTIONS = {
    "Throttle Up":    ( 0.,  0.,  0.,  1.),
    "Throttle Down":  ( 0.,  0.,  0., -1.),
    "Pitch Forward":  ( 1.,  0.,  0.,  0.),
    "Pitch Backward": (-1.,  0.,  0.,  0.),
    "Roll Left":      ( 0., -1.,  0.,  0.),
    "Roll Right":     ( 0.,  1.,  0.,  0.),
    "Yaw Left":       ( 0.,  0., -1.,  0.),
    "Yaw Right":      ( 0.,  0.,  1.,  0.),
    "Hover":          ( 0.,  0.,  0.,  0.),
}
ACTION_NAMES = list(DRONE_ACTIONS.keys())  # ordered list for menu

class SignalMapping:
    """
    Configurable mapping from BCI intent → drone action.
    Users can reassign any intent to any drone action via the in-sim menu (M key).
    """
    INTENT_NAMES = {0:"Forward", 1:"Backward", 2:"Left", 3:"Right", 4:"Hover"}

    # Default mapping
    DEFAULT = {
        0: "Pitch Forward",   # Forward intent → pitch forward
        1: "Pitch Backward",  # Backward intent → pitch backward
        2: "Roll Left",       # Left intent → roll left + yaw left
        3: "Roll Right",      # Right intent → roll right + yaw right
        4: "Hover",           # Hover intent → hover
    }

    def __init__(self):
        self.mapping = dict(self.DEFAULT)
        self.menu_open = False
        self.selected_intent = None  # which intent row is selected for reassignment

    def get_command(self, intent_id):
        """Get (pitch, roll, yaw, throttle) for the given intent."""
        action_name = self.mapping.get(intent_id, "Hover")
        return DRONE_ACTIONS.get(action_name, (0., 0., 0., 0.))

    def set_mapping(self, intent_id, action_name):
        """Assign a drone action to a BCI intent."""
        if action_name in DRONE_ACTIONS:
            self.mapping[intent_id] = action_name

    def cycle_action(self, intent_id):
        """Cycle to the next available action for this intent."""
        current = self.mapping.get(intent_id, "Hover")
        idx = ACTION_NAMES.index(current) if current in ACTION_NAMES else 0
        next_idx = (idx + 1) % len(ACTION_NAMES)
        self.mapping[intent_id] = ACTION_NAMES[next_idx]



# ══════════════════════════════════════════════════════════════════════
# PHYSICS
# ══════════════════════════════════════════════════════════════════════

class DroneState:
    def __init__(self):
        self.x=0.; self.y=0.; self.z=0.
        self.yaw=0.; self.pitch=0.; self.roll=0.
        self.vx=0.; self.vy=0.; self.vz=0.
        self.flying=False; self.armed=False; self.mode="IDLE"

class DronePhysics:
    DRAG=0.82; GRAVITY=3.0; THRUST=7.0; MOVE=9.0; YAW_RATE=80.
    def __init__(self, s): self.s=s
    def update(self, pitch, roll, yaw_in, throttle, dt):
        s=self.s
        if not s.flying: s.vx=s.vy=s.vz=0.; return
        s.yaw=(s.yaw+yaw_in*self.YAW_RATE*dt)%360
        yr=math.radians(s.yaw)
        # Altitude hold: only apply thrust/gravity when throttle is non-zero
        if throttle > 0:
            # Throttle up — climb
            s.vy += throttle * self.THRUST * dt; s.vy *= self.DRAG
        elif throttle < 0:
            # Throttle down — descend (gravity assists)
            s.vy += (throttle * self.THRUST - self.GRAVITY) * dt; s.vy *= self.DRAG
        else:
            # No throttle — hold altitude (kill vertical velocity)
            s.vy *= 0.5  # quickly dampen any residual vertical velocity
        fx=math.sin(yr); fz=math.cos(yr); rx=math.cos(yr); rz=-math.sin(yr)
        s.vx+=(pitch*fx+roll*rx)*self.MOVE*dt; s.vx*=self.DRAG
        s.vz+=(pitch*fz+roll*rz)*self.MOVE*dt; s.vz*=self.DRAG
        s.x+=s.vx*dt; s.z+=s.vz*dt
        s.y=max(0., s.y+s.vy*dt)
        if s.y<=0.: s.vy=0.
        # visual tilt
        s.pitch=pitch*-14; s.roll=roll*-14
        s.x=max(-90,min(90,s.x)); s.z=max(-90,min(90,s.z))


# ══════════════════════════════════════════════════════════════════════
# HUD DRAWING HELPERS
# ══════════════════════════════════════════════════════════════════════

def draw_panel(surf, x, y, w, h, border_col, alpha=200):
    """Dark semi-transparent panel with neon border + corner accents."""
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    panel.fill((5, 8, 18, alpha))
    surf.blit(panel, (x, y))
    t = 1
    pygame.draw.rect(surf, border_col, (x, y, w, h), t)
    # corner accents
    ca = 8
    for cx2, cy2, dx, dy in [
        (x,   y,   1, 1),(x+w, y,   -1, 1),
        (x,   y+h, 1,-1),(x+w, y+h, -1,-1),
    ]:
        pygame.draw.line(surf, WHITE, (cx2, cy2), (cx2+dx*ca, cy2), 2)
        pygame.draw.line(surf, WHITE, (cx2, cy2), (cx2, cy2+dy*ca), 2)


def draw_bar(surf, x, y, w, h, frac, col_fill, col_bg=(20,20,30)):
    """Horizontal progress bar."""
    pygame.draw.rect(surf, col_bg, (x, y, w, h))
    fill_w = int(w * max(0., min(1., frac)))
    if fill_w > 0:
        pygame.draw.rect(surf, col_fill, (x, y, fill_w, h))
    pygame.draw.rect(surf, GREY, (x, y, w, h), 1)


def draw_vbar(surf, x, y, w, h, frac, col_fill, col_bg=(20,20,30)):
    """Vertical progress bar (fills from bottom)."""
    pygame.draw.rect(surf, col_bg, (x, y, w, h))
    fill_h = int(h * max(0., min(1., frac)))
    if fill_h > 0:
        pygame.draw.rect(surf, col_fill, (x, y+h-fill_h, w, fill_h))
    pygame.draw.rect(surf, GREY, (x, y, w, h), 1)


def draw_compass(surf, cx, cy, r, yaw_deg, font_sm):
    """Circular compass with rotating needle."""
    pygame.draw.circle(surf, (10, 14, 28), (cx, cy), r)
    pygame.draw.circle(surf, CYAN_DIM, (cx, cy), r, 1)
    # tick marks
    for deg in range(0, 360, 45):
        a = math.radians(deg - yaw_deg)
        x1 = cx + int((r-4)*math.sin(a)); y1 = cy - int((r-4)*math.cos(a))
        x2 = cx + int(r*math.sin(a));     y2 = cy - int(r*math.cos(a))
        pygame.draw.line(surf, CYAN_DIM, (x1,y1), (x2,y2), 1)
    # N label
    na = math.radians(-yaw_deg)
    nx = cx + int((r-12)*math.sin(na)); ny = cy - int((r-12)*math.cos(na))
    lbl = font_sm.render("N", True, YELLOW)
    surf.blit(lbl, (nx-4, ny-6))
    # needle
    needle_a = 0   # always points up (north = up in compass)
    nx2 = cx + int((r-6)*math.sin(needle_a)); ny2 = cy - int((r-6)*math.cos(needle_a))
    nx3 = cx - int(8*math.sin(needle_a));     ny3 = cy + int(8*math.cos(needle_a))
    pygame.draw.line(surf, RED, (cx,cy), (nx2,ny2), 2)
    pygame.draw.line(surf, GREY, (cx,cy), (nx3,ny3), 2)
    pygame.draw.circle(surf, WHITE, (cx,cy), 3)


# ══════════════════════════════════════════════════════════════════════
# 3-D SCENE RENDERER
# ══════════════════════════════════════════════════════════════════════

def render_scene(surf, cam, state, trail, rotor_angle, font_sm):
    """Draw world grid, buildings, landing pad, drone, trail."""
    drone_pos = (state.x, state.y, state.z)

    # ── collect all world points to project ──────────────────────────
    # Grid lines
    grid_segs = []
    for (p1, p2, col, alpha, lw) in GRID_LINES:
        pts = cam.project([p1, p2], drone_pos)
        if pts[0] and pts[1]:
            grid_segs.append((pts[0], pts[1], col, alpha, lw))

    # Grid coordinate labels
    label_pts = []
    labels = []
    for x in range(-100, 101, 50):
        for z in range(-100, 101, 50):
            label_pts.append((float(x), 0.0, float(z)))
            labels.append(f"{x},{z}")
    label_proj = cam.project(label_pts, drone_pos)

    # Sort back-to-front by average depth
    grid_segs.sort(key=lambda s: -(s[0][2]+s[1][2])/2)

    # Draw grid on a surface with alpha
    grid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for (p1, p2, col, alpha, lw) in grid_segs:
        c = (col[0], col[1], col[2], alpha)
        pygame.draw.line(grid_surf, c, (p1[0],p1[1]), (p2[0],p2[1]), lw)
    surf.blit(grid_surf, (0,0))

    # Draw coordinate labels
    for i, p in enumerate(label_proj):
        if p and p[2] < 100:
            lbl = font_sm.render(labels[i], True, CYAN_DIM)
            surf.blit(lbl, (p[0], p[1]))

    # ── Landing pad ───────────────────────────────────────────────────
    pad_proj = cam.project(PAD, drone_pos)
    if all(pad_proj):
        pts2d = [(p[0],p[1]) for p in pad_proj]
        pygame.draw.polygon(surf, (15,15,30), pts2d)
        pygame.draw.polygon(surf, ORANGE, pts2d, 2)

    # ── Buildings ─────────────────────────────────────────────────────
    for (corners, edges, win_rows, bx, bz, sw, sd, sh) in BUILDINGS:
        proj = cam.project(corners, drone_pos)
        # draw edges
        for (i,j) in edges:
            if proj[i] and proj[j]:
                depth = (proj[i][2]+proj[j][2])/2
                fade = max(40, min(160, int(200 - depth*1.5)))
                col = (0, fade//2, fade)
                pygame.draw.line(surf, col, (proj[i][0],proj[i][1]),
                                 (proj[j][0],proj[j][1]), 1)
        # window glow dots
        for wy in win_rows:
            wp = cam.project([(bx, wy, bz)], drone_pos)
            if wp[0] and wp[0][2] < 120:
                pygame.draw.circle(surf, (180,220,255), (wp[0][0],wp[0][1]), 2)

    # ── Trail ─────────────────────────────────────────────────────────
    if len(trail) > 1:
        trail_proj = cam.project(list(trail), drone_pos)
        for i, pt in enumerate(trail_proj):
            if pt:
                alpha = int(200 * i / len(trail_proj))
                r = max(1, int(3 * i / len(trail_proj)))
                c = (0, alpha, min(255, alpha+80))
                pygame.draw.circle(surf, c, (pt[0],pt[1]), r)

    # ── Drone ─────────────────────────────────────────────────────────
    centre, arms, body_corners, canopy, leg_tops, leg_bottoms, front_cam = \
        drone_points(state.yaw, state.pitch, state.roll)
    # offset to world position
    def w(p): return (p[0]+state.x, p[1]+state.y, p[2]+state.z)

    arm_world = [w(a) for a in arms]
    ctr_world = w(centre)
    body_world = [w(b) for b in body_corners]
    canopy_world = [w(c) for c in canopy]
    lt_world = [w(l) for l in leg_tops]
    lb_world = [w(l) for l in leg_bottoms]
    cam_world = w(front_cam)

    # Collect all points for projection
    all_pts = [ctr_world] + arm_world + body_world + canopy_world + lt_world + lb_world + [cam_world]
    # rotor ring points
    rotor_rings = []
    for arm in arm_world:
        ring = rotor_ring_pts(arm[0], arm[1], arm[2], ROTOR_R)
        rotor_rings.append(ring)
        all_pts += ring

    proj_all = cam.project(all_pts, drone_pos)

    # Unpack projected indices
    ctr_p = proj_all[0]
    arm_p = proj_all[1:5]
    body_p = proj_all[5:11]
    canopy_p = proj_all[11:15]
    lt_p = proj_all[15:19]
    lb_p = proj_all[19:23]
    cam_p = proj_all[23]
    ring_start = 24

    if ctr_p:
        # Depth-based scale factor
        scale = max(0.3, min(2.0, 400 / max(1, ctr_p[2])))

        # ── Shadow on ground ─────────────────────────────────────────
        shadow_p = cam.project([(state.x, 0, state.z)], drone_pos)[0]
        if shadow_p:
            s_r = max(4, int(22*scale - state.y*0.6))
            shadow_surf = pygame.Surface((s_r*4, s_r*2), pygame.SRCALPHA)
            alpha = max(15, 90 - int(state.y*3))
            pygame.draw.ellipse(shadow_surf, (0,0,0,alpha), (0,0,s_r*4,s_r*2))
            surf.blit(shadow_surf, (shadow_p[0]-s_r*2, shadow_p[1]-s_r//2))

        # ── Landing gear (draw first = behind body) ──────────────────
        if lb_p[0] and lb_p[1]:
            pygame.draw.line(surf, GREY, (lb_p[0][0],lb_p[0][1]), (lb_p[1][0],lb_p[1][1]), max(1,int(2*scale)))
        if lb_p[2] and lb_p[3]:
            pygame.draw.line(surf, GREY, (lb_p[2][0],lb_p[2][1]), (lb_p[3][0],lb_p[3][1]), max(1,int(2*scale)))
        for i in range(4):
            if lt_p[i] and lb_p[i]:
                pygame.draw.line(surf, GREY, (lt_p[i][0],lt_p[i][1]), (lb_p[i][0],lb_p[i][1]), max(1,int(1.5*scale)))

        # ── X-frame arms (thick) ─────────────────────────────────────
        arm_thickness = max(2, int(4*scale))
        for i, ap in enumerate(arm_p):
            if ap:
                pygame.draw.line(surf, DRONE_ARM, (ctr_p[0],ctr_p[1]), (ap[0],ap[1]), arm_thickness)
                pygame.draw.line(surf, (40,90,160), (ctr_p[0],ctr_p[1]), (ap[0],ap[1]), max(1,int(1.5*scale)))

        # ── Body plate (octagonal) ──────────────────────────────
        valid_body = [p for p in body_p if p]
        if len(valid_body) >= 3:
            body_2d = [(p[0],p[1]) for p in valid_body]
            pygame.draw.polygon(surf, (15, 25, 50), body_2d)
            pygame.draw.polygon(surf, DRONE_BODY, body_2d, max(1,int(2*scale)))
            
        # ── Canopy (above body) ────────────────────────────────
        valid_canopy = [p for p in canopy_p if p]
        if len(valid_canopy) >= 3:
            canopy_2d = [(p[0],p[1]) for p in valid_canopy]
            pygame.draw.polygon(surf, (30, 100, 200, 150), canopy_2d) # semi-trans
            pygame.draw.polygon(surf, CYAN, canopy_2d, 1)

        # ── Motor housings ───────────────────────────────────────────
        motor_r = max(3, int(6*scale))
        motor_cols = [ROTOR_A, ROTOR_B, ROTOR_B, ROTOR_A]
        for i, ap in enumerate(arm_p):
            if ap:
                pygame.draw.circle(surf, (20,20,35), (ap[0],ap[1]), motor_r)
                pygame.draw.circle(surf, motor_cols[i], (ap[0],ap[1]), motor_r, max(1,int(1.5*scale)))

        # ── Rotor discs + spinning blades ────────────────────────────
        for ri, ring in enumerate(rotor_rings):
            ring_pts = proj_all[ring_start + ri*12 : ring_start + ri*12 + 12]
            valid = [p for p in ring_pts if p]
            if len(valid) >= 4:
                pts2d = [(p[0],p[1]) for p in valid]
                col = ROTOR_A if ri in (0,3) else ROTOR_B
                if state.flying:
                    disc_surf = pygame.Surface((W,H), pygame.SRCALPHA)
                    pygame.draw.polygon(disc_surf, (col[0],col[1],col[2], 30), pts2d)
                    surf.blit(disc_surf, (0,0))
                pygame.draw.polygon(surf, col, pts2d, 1)
                if state.flying and arm_p[ri]:
                    ax, ay = arm_p[ri][0], arm_p[ri][1]
                    spin = rotor_angle * (1 if ri%2==0 else -1)
                    blade_len = max(8, int(16*scale))
                    for b_off in [0, 2*math.pi/3, 4*math.pi/3]:
                        blade = spin + b_off
                        bx2 = ax + int(blade_len*math.cos(blade))
                        by2 = ay + int(blade_len*math.sin(blade))
                        pygame.draw.line(surf, col, (ax,ay), (bx2,by2), max(1,int(2*scale)))

        # ── Centre hub ───────────────────────────────────────────────
        hub_r = max(3, int(5*scale))
        pygame.draw.circle(surf, (15,25,50), (ctr_p[0],ctr_p[1]), hub_r)
        pygame.draw.circle(surf, CYAN, (ctr_p[0],ctr_p[1]), hub_r, max(1,int(1.5*scale)))

        # ── Front camera pod ─────────────────────────────────────────
        if cam_p:
            cam_r = max(2, int(4*scale))
            pygame.draw.circle(surf, (40,40,60), (cam_p[0],cam_p[1]), cam_r)
            pygame.draw.circle(surf, CYAN, (cam_p[0],cam_p[1]), cam_r, 1)
            pygame.draw.circle(surf, (255,50,50), (cam_p[0],cam_p[1]), max(1,int(1.5*scale)))

        # ── Front LED (green) ────────────────────────────────────────
        yr = math.radians(state.yaw)
        front_led = w((math.sin(yr)*ARM_LEN*0.5, 0.05, math.cos(yr)*ARM_LEN*0.5))
        fp = cam.project([front_led], drone_pos)[0]
        if fp:
            pygame.draw.circle(surf, GREEN, (fp[0],fp[1]), max(2,int(3*scale)))

        # ── Rear LED (red) ───────────────────────────────────────────
        rear_led = w((-math.sin(yr)*ARM_LEN*0.5, 0.05, -math.cos(yr)*ARM_LEN*0.5))
        rp = cam.project([rear_led], drone_pos)[0]
        if rp:
            pygame.draw.circle(surf, RED, (rp[0],rp[1]), max(2,int(2.5*scale)))


# ══════════════════════════════════════════════════════════════════════
# HUD RENDERER
# ══════════════════════════════════════════════════════════════════════

def render_hud(surf, fonts, state, source, bci_label, bci_conf,
               bci_features, bci_active, cam_name, fps, click_regions=None):
    font, font_sm, font_lg, font_title = fonts
    mx, my = pygame.mouse.get_pos()

    # ── Left telemetry panel ──────────────────────────────────────────
    PW, PH = 230, 260
    PX, PY = 14, 14
    draw_panel(surf, PX, PY, PW, PH, CYAN)

    # Title
    t = font_title.render("◈ FLIGHT DATA", True, CYAN)
    surf.blit(t, (PX+10, PY+8))
    pygame.draw.line(surf, CYAN_DIM, (PX+8, PY+28), (PX+PW-8, PY+28), 1)

    mode_col = GREEN if state.flying else RED
    rows = [
        ("MODE",  state.mode,          mode_col),
        ("ALT",   f"{state.y:.1f} m",  CYAN),
        ("YAW",   f"{state.yaw:.0f}°", CYAN),
        ("X",     f"{state.x:.1f}",    CYAN),
        ("Z",     f"{state.z:.1f}",    CYAN),
        ("INPUT", source,              GREEN if source=="BCI" else ORANGE if source=="KB" else GREY),
        ("ARMED", "YES" if state.armed else "NO", GREEN if state.armed else RED),
        ("CAM",   cam_name,            CYAN),
    ]
    for i, (label, val, col) in enumerate(rows):
        lbl_s = font_sm.render(label, True, GREY)
        val_s = font_sm.render(val,   True, col)
        surf.blit(lbl_s, (PX+10, PY+36 + i*26))
        surf.blit(val_s, (PX+100, PY+36 + i*26))

    # Altitude bar (right side of left panel)
    draw_vbar(surf, PX+PW-22, PY+36, 12, PH-50,
              min(state.y/20., 1.), CYAN, (10,20,30))
    alt_lbl = font_sm.render("ALT", True, CYAN_DIM)
    surf.blit(alt_lbl, (PX+PW-26, PY+PH-18))

    # ── Right BCI panel ───────────────────────────────────────────────
    BW, BH = 260, 440
    BX = W - BW - 14
    BY = 14
    border_col = PURPLE if bci_active else GREY
    draw_panel(surf, BX, BY, BW, BH, border_col)

    t2 = font_title.render("◈ NEURAL INPUT", True, border_col)
    surf.blit(t2, (BX+10, BY+8))
    pygame.draw.line(surf, PURPLE_DIM, (BX+8, BY+28), (BX+BW-8, BY+28), 1)

    if bci_active:
        intent_s = font.render(f"→ {bci_label}", True, GREEN if bci_conf>0.65 else ORANGE)
        surf.blit(intent_s, (BX+10, BY+36))

        # Confidence bar
        conf_col = GREEN if bci_conf > 0.65 else RED
        draw_bar(surf, BX+10, BY+68, BW-20, 12, bci_conf, conf_col)
        conf_lbl = font_sm.render(f"CONF  {bci_conf:.0%}", True, conf_col)
        surf.blit(conf_lbl, (BX+10, BY+54))

        # Extract feature values
        c3_mu = bci_features.get("c3_mu", 0)
        c4_mu = bci_features.get("c4_mu", 0)
        c3_beta = bci_features.get("c3_beta", 0)
        c4_beta = bci_features.get("c4_beta", 0)
        asym = bci_features.get("mu_asym", 0)

        # Band power bars with movement annotations
        # Mapping: T1=Left(2), T2=Right(3), T0=Forward(0), Hover=4
        bands = [
            ("C3 μ", c3_mu,   CYAN,         "← LEFT",   2),
            ("C4 μ", c4_mu,   (0,160,200),   "→ RIGHT",  3),
            ("C3 β", c3_beta, PURPLE,        "↑ FORWARD",0),
            ("C4 β", c4_beta, (120,40,200),  "■ HOVER",  4),
        ]
        max_val = max(v for _,v,_,_,_ in bands) + 1e-9
        for i, (lbl, val, col, move_hint, intent_id) in enumerate(bands):
            by2 = BY + 96 + i*42
            
            # Click region
            rect = pygame.Rect(BX+8, by2-2, BW-16, 40)
            is_hover = bci_active and rect.collidepoint(mx, my)
            if is_hover:
                pygame.draw.rect(surf, (60, 40, 80), rect, 0, 4)
                if click_regions is not None:
                    click_regions[intent_id] = rect

            lbl_s = font_sm.render(lbl, True, WHITE if is_hover else GREY)
            surf.blit(lbl_s, (BX+10, by2))
            draw_bar(surf, BX+10, by2+14, BW-20, 10, val/max_val, col)
            val_s = font_sm.render(f"{val:.3f}", True, col)
            surf.blit(val_s, (BX+BW-70, by2))
            
            # Movement annotation
            if is_hover:
                hint_s = font_sm.render(f"CLICK: {move_hint}", True, YELLOW)
                surf.blit(hint_s, (BX+70, by2))
            elif move_hint:
                hint_col = GREEN if "LEFT" in move_hint or "RIGHT" in move_hint else CYAN_DIM
                hint_s = font_sm.render(move_hint, True, hint_col)
                surf.blit(hint_s, (BX+70, by2))

        # Asymmetry indicator
        ay2 = BY + 270
        mid = BX + BW//2
        pygame.draw.rect(surf, (20,10,40), (BX+10, ay2, BW-20, 10))
        bar_len = int(asym * (BW//2 - 10))
        col = CYAN if asym > 0 else ORANGE
        if bar_len > 0:
            pygame.draw.rect(surf, col, (mid, ay2, bar_len, 10))
        elif bar_len < 0:
            pygame.draw.rect(surf, col, (mid+bar_len, ay2, -bar_len, 10))
        pygame.draw.line(surf, WHITE, (mid, ay2-2), (mid, ay2+12), 1)
        asym_lbl = font_sm.render(f"L←ASYM→R  {asym:+.2f}", True, GREY)
        surf.blit(asym_lbl, (BX+10, ay2-14))

        # Active direction indicator
        if abs(asym) > 0.10:
            dir_text = "◀ LEFT" if asym > 0 else "RIGHT ▶"
            dir_col = CYAN if asym > 0 else ORANGE
            dir_s = font.render(dir_text, True, dir_col)
            surf.blit(dir_s, (BX + BW//2 - dir_s.get_width()//2, ay2 + 16))

        # ── DECODE RULES legend ──────────────────────────────────────
        ry = BY + 310
        pygame.draw.line(surf, PURPLE_DIM, (BX+8, ry), (BX+BW-8, ry), 1)
        rules_title = font_title.render("◈ DECODE RULES", True, PURPLE_DIM)
        surf.blit(rules_title, (BX+10, ry+4))

        rules = [
            ("C3μ > C4μ",    "← LEFT",     CYAN),
            ("C4μ > C3μ",    "→ RIGHT",    ORANGE),
            ("Both μ high",  "↑ FORWARD",  GREEN),
            ("Both β high",  "■ HOVER",    YELLOW),
            ("β increase",   "↓ BACKWARD", RED),
        ]
        for i, (condition, result, rcol) in enumerate(rules):
            ry2 = ry + 22 + i * 18
            cond_s = font_sm.render(condition, True, GREY)
            res_s = font_sm.render(result, True, rcol)
            surf.blit(cond_s, (BX+12, ry2))
            surf.blit(res_s, (BX+130, ry2))
    else:
        off = font.render("OFFLINE", True, GREY)
        surf.blit(off, (BX+10, BY+40))
        kb = font_sm.render("Keyboard mode active", True, GREY)
        surf.blit(kb, (BX+10, BY+70))

    # ── Compass (bottom centre) ───────────────────────────────────────
    draw_compass(surf, W//2, H-60, 42, state.yaw, font_sm)

    # ── Mode banner (top centre) ──────────────────────────────────────
    mode_colors = {"FLYING": GREEN, "HOVER": YELLOW, "LANDING": ORANGE, "IDLE": GREY}
    mc = mode_colors.get(state.mode, GREY)
    banner = font_lg.render(f"[ {state.mode} ]", True, mc)
    bw = banner.get_width()
    # glow effect — draw slightly offset in dim colour first
    glow = font_lg.render(f"[ {state.mode} ]", True,
                          tuple(min(255,c//3) for c in mc))
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        surf.blit(glow, (W//2 - bw//2 + dx, 14 + dy))
    surf.blit(banner, (W//2 - bw//2, 14))

    # ── Bottom controls bar ───────────────────────────────────────────
    draw_panel(surf, 10, H-38, W-20, 28, ORANGE, alpha=180)
    ctrl = font_sm.render(
        "T=Takeoff  L=Land  SPACE=Hover  B=BCI  C=Camera  M=Mapping  ESC=Quit"
        "     W/S=Throttle  A/D=Yaw  Arrows=Pitch/Roll",
        True, ORANGE)
    surf.blit(ctrl, (20, H-30))

    # ── FPS (top right corner) ────────────────────────────────────────
    fps_s = font_sm.render(f"FPS {fps:.0f}", True, GREY)
    surf.blit(fps_s, (W-60, H-30))


# ══════════════════════════════════════════════════════════════════════
# SIGNAL MAPPING MENU RENDERER
# ══════════════════════════════════════════════════════════════════════

def render_mapping_menu(surf, fonts, sig_map):
    """Draw the neural signal mapping configuration menu."""
    font, font_sm, font_lg, font_title = fonts

    # Centre overlay panel
    MW, MH = 520, 380
    MX = W//2 - MW//2
    MY = H//2 - MH//2

    # Dimmed backdrop
    dim = pygame.Surface((W, H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 160))
    surf.blit(dim, (0, 0))

    draw_panel(surf, MX, MY, MW, MH, PURPLE)

    # Title
    t = font_lg.render("◈ NEURAL SIGNAL MAPPING", True, PURPLE)
    surf.blit(t, (MX + MW//2 - t.get_width()//2, MY + 12))
    pygame.draw.line(surf, PURPLE_DIM, (MX+10, MY+44), (MX+MW-10, MY+44), 1)

    # Instructions
    inst = font_sm.render("Click an intent to select, then press 1-9 to assign action", True, GREY)
    surf.blit(inst, (MX + MW//2 - inst.get_width()//2, MY + 50))
    inst2 = font_sm.render("Press M or ESC to close", True, GREY)
    surf.blit(inst2, (MX + MW//2 - inst2.get_width()//2, MY + 66))

    # Column headers
    pygame.draw.line(surf, PURPLE_DIM, (MX+10, MY+86), (MX+MW-10, MY+86), 1)
    hdr_intent = font_sm.render("BCI INTENT", True, CYAN)
    hdr_action = font_sm.render("DRONE ACTION", True, CYAN)
    hdr_key = font_sm.render("#", True, CYAN)
    surf.blit(hdr_key, (MX+15, MY+90))
    surf.blit(hdr_intent, (MX+40, MY+90))
    surf.blit(hdr_action, (MX+250, MY+90))

    # Intent rows
    for intent_id in range(5):
        row_y = MY + 110 + intent_id * 44
        is_selected = (sig_map.selected_intent == intent_id)

        # Highlight selected row
        if is_selected:
            hl = pygame.Surface((MW - 20, 38), pygame.SRCALPHA)
            hl.fill((160, 60, 255, 50))
            surf.blit(hl, (MX+10, row_y))
            pygame.draw.rect(surf, PURPLE, (MX+10, row_y, MW-20, 38), 1)

        # Intent name
        intent_name = sig_map.INTENT_NAMES[intent_id]
        col = GREEN if is_selected else WHITE
        num_s = font.render(f"{intent_id}", True, GREY)
        name_s = font.render(intent_name, True, col)
        action_name = sig_map.mapping.get(intent_id, "Hover")
        action_s = font.render(f"➜ {action_name}", True, ORANGE if is_selected else CYAN)

        surf.blit(num_s, (MX+18, row_y + 10))
        surf.blit(name_s, (MX+45, row_y + 10))
        surf.blit(action_s, (MX+250, row_y + 10))

    # Action legend at bottom
    legend_y = MY + MH - 60
    pygame.draw.line(surf, PURPLE_DIM, (MX+10, legend_y - 8), (MX+MW-10, legend_y - 8), 1)
    actions_left = [
        "1=Throttle Up", "2=Throttle Down", "3=Pitch Fwd",
        "4=Pitch Back", "5=Roll Left",
    ]
    actions_right = [
        "6=Roll Right", "7=Yaw Left", "8=Yaw Right", "9=Hover",
    ]
    left_str = "  ".join(actions_left)
    right_str = "  ".join(actions_right)
    l1 = font_sm.render(left_str, True, GREY)
    l2 = font_sm.render(right_str, True, GREY)
    surf.blit(l1, (MX + MW//2 - l1.get_width()//2, legend_y))
    surf.blit(l2, (MX + MW//2 - l2.get_width()//2, legend_y + 18))


# ══════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════

def run(use_bci=True, use_real_eeg=False, backend_name='sim'):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mind Link — 3D BCI Drone Simulator")
    clock = pygame.time.Clock()

    # Fonts
    pygame.font.init()
    try:
        font       = pygame.font.SysFont("consolas", 15)
        font_sm    = pygame.font.SysFont("consolas", 13)
        font_lg    = pygame.font.SysFont("consolas", 26, bold=True)
        font_title = pygame.font.SysFont("consolas", 14, bold=True)
    except Exception:
        font = font_sm = font_lg = font_title = pygame.font.Font(None, 16)
    fonts = (font, font_sm, font_lg, font_title)

    # State
    state   = DroneState()
    physics = DronePhysics(state)
    cam     = Camera3D()
    trail   = deque(maxlen=120)

    # EEG
    eeg_src = EEGSource(use_real=use_real_eeg)
    decoder = BCIDecoder(fs=eeg_src.fs, c3=eeg_src.c3_idx, c4=eeg_src.c4_idx) if use_bci else None

    bci_intent=4; bci_label="Hover"; bci_conf=0.; bci_features={}
    last_bci=0.; BCI_INT=0.25

    # Neural signal mapping (user-configurable)
    sig_map = SignalMapping()
    source="IDLE"; rotor_angle=0.

    # Warning flash
    warn_text=""; warn_timer=0.
    
    # Clickable HUD regions
    click_regions = {}

    mouse_dragging = False

    print("\n[sim3d] Ready — T=Takeoff, ESC=Quit")

    running = True
    while running:
        dt = clock.tick(60) / 1000.
        fps = clock.get_fps()
        
        # Reset regions each frame
        click_regions = {}

        # ── Events ───────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_t and not sig_map.menu_open:
                    state.flying=True; state.armed=True
                    state.y=0.3; state.mode="FLYING"; state.vy=2.
                    warn_text="TAKEOFF"; warn_timer=1.5
                elif event.key == pygame.K_l and not sig_map.menu_open:
                    state.mode="LANDING"; state.vy=-1.5
                    warn_text="LANDING"; warn_timer=1.5
                elif event.key == pygame.K_SPACE and not sig_map.menu_open:
                    state.vx=state.vy=state.vz=0.; state.mode="HOVER"
                    warn_text="HOVER"; warn_timer=1.
                elif event.key == pygame.K_b and not sig_map.menu_open:
                    use_bci = not use_bci
                    warn_text=f"BCI {'ON' if use_bci else 'OFF'}"; warn_timer=1.5
                elif event.key == pygame.K_c and not sig_map.menu_open:
                    cam.cycle()
                    warn_text=f"CAM: {cam.name}"; warn_timer=1.
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS) and not sig_map.menu_open:
                    cam.zoom(1); warn_text=f"ZOOM {cam.dist:.0f}"; warn_timer=0.5
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS) and not sig_map.menu_open:
                    cam.zoom(-1); warn_text=f"ZOOM {cam.dist:.0f}"; warn_timer=0.5
                elif event.key == pygame.K_m:
                    sig_map.menu_open = not sig_map.menu_open
                    sig_map.selected_intent = None
                    if sig_map.menu_open:
                        warn_text="SIGNAL MAPPING"; warn_timer=1.
                # Mapping menu: number keys to assign actions
                elif sig_map.menu_open and sig_map.selected_intent is not None:
                    key_action_map = {
                        pygame.K_1: "Throttle Up",
                        pygame.K_2: "Throttle Down",
                        pygame.K_3: "Pitch Forward",
                        pygame.K_4: "Pitch Backward",
                        pygame.K_5: "Roll Left",
                        pygame.K_6: "Roll Right",
                        pygame.K_7: "Yaw Left",
                        pygame.K_8: "Yaw Right",
                        pygame.K_9: "Hover",
                    }
                    if event.key in key_action_map:
                        sig_map.set_mapping(sig_map.selected_intent, key_action_map[event.key])
                        warn_text=f"{sig_map.INTENT_NAMES[sig_map.selected_intent]} → {key_action_map[event.key]}"
                        warn_timer=1.5
                        sig_map.selected_intent = None
                # Mapping menu: 0-4 to select intent row
                elif sig_map.menu_open:
                    intent_keys = {
                        pygame.K_0: 0, pygame.K_1: 1, pygame.K_2: 2,
                        pygame.K_3: 3, pygame.K_4: 4,
                    }
                    if event.key in intent_keys:
                        sig_map.selected_intent = intent_keys[event.key]
            # Mouse wheel zoom
            if event.type == pygame.MOUSEWHEEL:
                cam.zoom(event.y)   # y>0 = scroll up = zoom in
            # Mouse click handling
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                clicked_ui = False
                
                # Check mapping menu clicks
                if sig_map.menu_open:
                    MW2, MH2 = 520, 380
                    MX2 = W//2 - MW2//2
                    MY2 = H//2 - MH2//2
                    for i in range(5):
                        row_y = MY2 + 110 + i * 44
                        if MX2+10 <= mx <= MX2+MW2-10 and row_y <= my <= row_y+38:
                            sig_map.selected_intent = i
                            clicked_ui = True
                            break
                    if MX2 <= mx <= MX2+MW2 and MY2 <= my <= MY2+MH2:
                        clicked_ui = True

                # Check BCI bar clicks in HUD
                elif use_bci:
                    for intent_id, rect in click_regions.items():
                        if rect.collidepoint(mx, my):
                            bci_intent = intent_id
                            bci_label = sig_map.INTENT_NAMES[intent_id]
                            bci_conf = 1.0 # Manual override
                            last_bci = time.time() # Lock it in for a moment
                            warn_text = f"MANUAL: {bci_label}"
                            warn_timer = 1.0
                            clicked_ui = True
                            break
                            
                if not clicked_ui and event.button in (1, 3):
                    mouse_dragging = True

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 3):
                    mouse_dragging = False
                    
            if event.type == pygame.MOUSEMOTION:
                if mouse_dragging:
                    cam.rotate(event.rel[0], event.rel[1])

        # ── Keyboard flight input ─────────────────────────────────────
        keys = pygame.key.get_pressed()
        pitch=roll=yaw_in=throttle=0.
        if keys[pygame.K_UP]:    pitch    =  1.
        if keys[pygame.K_DOWN]:  pitch    = -1.
        if keys[pygame.K_LEFT]:  roll     = -1.
        if keys[pygame.K_RIGHT]: roll     =  1.
        if keys[pygame.K_w]:     throttle =  1.
        if keys[pygame.K_s]:     throttle = -1.
        if keys[pygame.K_a]:     yaw_in   = -1.
        if keys[pygame.K_d]:     yaw_in   =  1.
        kb_active = any([pitch, roll, yaw_in, throttle])

        # ── BCI decode ────────────────────────────────────────────────
        if use_bci and decoder and (time.time()-last_bci) > BCI_INT:
            n = int(eeg_src.fs*0.5)
            win = eeg_src.get_window(n)
            bci_intent,bci_label,bci_conf,bci_features = decoder.decode(win)
            last_bci = time.time()

        # ── Merge inputs ──────────────────────────────────────────────
        if kb_active:
            source = "KB"
        elif use_bci and state.flying and bci_conf > 0.45:
            p,r,y,t2 = sig_map.get_command(bci_intent)
            pitch,roll,yaw_in,throttle = p,r,y,t2
            source = "BCI"
        else:
            source = "IDLE"

        # ── Physics ───────────────────────────────────────────────────
        physics.update(pitch, roll, yaw_in, throttle, dt)
        if state.flying:
            rotor_angle += dt * 15
            trail.append((state.x, state.y, state.z))

        # Landing complete
        if state.mode == "LANDING" and state.y <= 0.:
            state.flying=False; state.mode="IDLE"; physics.vy=0.

        # ── Draw ──────────────────────────────────────────────────────
        screen.fill(BG)

        # Subtle scanline overlay
        scan_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for sy in range(0, H, 4):
            pygame.draw.line(scan_surf, (0,0,0,18), (0,sy), (W,sy))
        screen.blit(scan_surf, (0,0))

        render_scene(screen, cam, state, trail, rotor_angle, fonts[1])
        render_hud(screen, fonts, state, source, bci_label, bci_conf,
                   bci_features, use_bci, cam.name, fps, click_regions)

        # Mapping menu overlay
        if sig_map.menu_open:
            render_mapping_menu(screen, fonts, sig_map)

        # Warning flash
        if warn_timer > 0:
            warn_timer -= dt
            alpha = min(255, int(warn_timer * 300))
            wc = tuple(min(255, c) for c in CYAN) + (alpha,)
            ws = font_lg.render(warn_text, True, CYAN)
            ww = ws.get_width()
            screen.blit(ws, (W//2 - ww//2, H//2 - 20))

        pygame.display.flip()

    pygame.quit()
    eeg_src.stop()
    print("[sim3d] Session ended")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-bci',   action='store_true')
    parser.add_argument('--real-eeg', action='store_true')
    parser.add_argument('--backend',  default='sim', choices=['sim','mavlink','tello'])
    args = parser.parse_args()
    run(use_bci=not args.no_bci, use_real_eeg=args.real_eeg, backend_name=args.backend)
