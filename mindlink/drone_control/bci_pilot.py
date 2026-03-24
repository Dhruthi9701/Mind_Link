"""
BCI + Keyboard Hybrid Pilot
============================
Combines motor imagery EEG decoding with keyboard fallback.

Motor Imagery → Drone Command mapping:
    Right hand up    → Throttle UP    (beta increase C4)
    Right hand down  → Throttle DOWN  (beta decrease C4)
    Right hand right → Roll RIGHT     (mu suppression C4 > C3)
    Right hand left  → Roll LEFT      (mu suppression C3 > C4)
    Both hands       → HOVER
    Rest             → Hold position

Keyboard fallback (always active):
    T=Takeoff  L=Land  SPACE=Hover  ESC=Stop
    W/S=Throttle  A/D=Yaw  Arrows=Pitch/Roll

Run:
    python drone_control/bci_pilot.py              # BCI sim + drone sim
    python drone_control/bci_pilot.py --backend tello   # real Tello
    python drone_control/bci_pilot.py --no-bci     # keyboard only
"""

import sys
import os
import math
import time
import threading
import argparse
import numpy as np
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pygame
except ImportError:
    print("Install pygame: pip install pygame")
    sys.exit(1)

from drone_control.drone_controller import (
    DroneState, SimBackend, MavlinkBackend, TelloBackend
)

# ------------------------------------------------------------------
# EEG source — real headset or synthetic simulation
# ------------------------------------------------------------------

class EEGSource:
    """
    Wraps itie bridge OR replays real PhysioNet EDF recordings.

    Simulation mode: streams windows from S001R04/R08/R12.edf in order,
    looping forever. Each EDF epoch is annotated T1 (left fist) or T2
    (right fist) — we expose those as the current intent so the decoder
    can be evaluated against ground-truth labels.

    Intent mapping from PhysioNet annotations:
        T0 = rest   → Hover  (4)
        T1 = left   → Left   (2)
        T2 = right  → Right  (3)
    """

    # PhysioNet annotation → intent id
    _ANNOT_TO_INTENT = {"T0": 4, "T1": 2, "T2": 3}

    def __init__(self, use_real: bool = False, config: dict = None):
        self.use_real = use_real
        self.fs = 160          # PhysioNet EEGMMIDB is 160 Hz
        self.n_channels = 64   # 64-ch cap in dataset
        self._bridge = None

        # Dataset replay state
        self._edf_data = None       # (n_samples, n_channels) full concatenated array
        self._edf_labels = None     # per-sample intent id
        self._cursor = 0
        self._c3_idx = 0
        self._c4_idx = 0
        self.current_intent = 4     # ground-truth label for current window

        if use_real:
            try:
                from input.itie_bridge import ItieBridge
                self._bridge = ItieBridge(config=config)
                self._bridge.connect()
                self._bridge.start_stream()
                print("[eeg] Real headset connected")
            except Exception as e:
                print(f"[eeg] Headset failed ({e}) — falling back to dataset replay")
                self.use_real = False

        if not self.use_real:
            self._load_edf_dataset()

    # ------------------------------------------------------------------
    # Dataset loading
    # ------------------------------------------------------------------

    def _load_edf_dataset(self):
        """Load S001R04, R08, R12 EDF files and build a replay buffer."""
        try:
            import mne
            mne.set_log_level("WARNING")
        except ImportError:
            print("[eeg] MNE not found — pip install mne. Falling back to synthetic.")
            self._use_synthetic_fallback()
            return

        edf_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "mindlink", "data", "physionet",
            "MNE-eegbci-data", "files", "eegmmidb", "1.0.0", "S001"
        )
        runs = ["S001R04.edf", "S001R08.edf", "S001R12.edf"]

        all_data, all_labels = [], []

        for fname in runs:
            fpath = os.path.join(edf_dir, fname)
            if not os.path.exists(fpath):
                print(f"[eeg] Missing {fname} — skipping")
                continue
            try:
                raw = mne.io.read_raw_edf(fpath, preload=True, verbose=False)
                raw.filter(1.0, 40.0, fir_design="firwin", verbose=False)

                # Locate C3 / C4 by name (dataset uses 'C3.' / 'C4.' notation)
                ch_names = [c.upper().strip('.') for c in raw.ch_names]
                c3_idx = next((i for i, c in enumerate(ch_names) if c == "C3"), None)
                c4_idx = next((i for i, c in enumerate(ch_names) if c == "C4"), None)
                if c3_idx is None or c4_idx is None:
                    # fallback: search for partial match
                    c3_idx = next((i for i, c in enumerate(ch_names) if "C3" in c), 7)
                    c4_idx = next((i for i, c in enumerate(ch_names) if "C4" in c), 11)

                self._c3_idx = c3_idx
                self._c4_idx = c4_idx
                self.fs = int(raw.info["sfreq"])
                self.n_channels = len(raw.ch_names)

                # Raw signal: (n_channels, n_times) → transpose to (n_times, n_channels)
                # MNE returns volts — convert to µV so PSD values are in usable range
                data = raw.get_data().T * 1e6

                # Build per-sample label array from annotations
                labels = np.full(len(data), 4, dtype=int)  # default = Hover/rest
                for annot in raw.annotations:
                    desc = annot["description"].strip()
                    intent = self._ANNOT_TO_INTENT.get(desc, 4)
                    onset_sample = int(annot["onset"] * self.fs)
                    dur_sample   = int(annot["duration"] * self.fs)
                    labels[onset_sample: onset_sample + dur_sample] = intent

                all_data.append(data)
                all_labels.append(labels)
                print(f"[eeg] Loaded {fname} — {len(data)} samples @ {self.fs} Hz, "
                      f"C3=ch{c3_idx}, C4=ch{c4_idx}")

            except Exception as e:
                print(f"[eeg] Failed to load {fname}: {e}")

        if all_data:
            self._edf_data   = np.concatenate(all_data,   axis=0)
            self._edf_labels = np.concatenate(all_labels, axis=0)
            self._cursor = 0
            print(f"[eeg] Dataset ready — {len(self._edf_data)} total samples, "
                  f"looping for simulation")
        else:
            print("[eeg] No EDF files loaded — using synthetic fallback")
            self._use_synthetic_fallback()

    def _use_synthetic_fallback(self):
        """Minimal synthetic fallback if EDF loading fails."""
        self.fs = 250
        self.n_channels = 32
        self._c3_idx = 7
        self._c4_idx = 11
        self._edf_data = None
        self._edf_labels = None

    # ------------------------------------------------------------------
    # Window retrieval
    # ------------------------------------------------------------------

    def get_window(self, n_samples: int = 125):
        """Return (n_samples, n_channels) EEG window."""
        if self.use_real and self._bridge:
            w = self._bridge.get_window(n_samples)
            if w is not None:
                return w["eeg"]

        if self._edf_data is not None:
            return self._dataset_window(n_samples)

        return self._synthetic_window(n_samples)

    def _dataset_window(self, n_samples: int) -> np.ndarray:
        """Slice next window from the loaded EDF buffer, looping at end."""
        total = len(self._edf_data)
        end = self._cursor + n_samples

        if end <= total:
            window = self._edf_data[self._cursor:end]
            # Majority label in this window
            self.current_intent = int(
                np.bincount(self._edf_labels[self._cursor:end]).argmax()
            )
            self._cursor = end
        else:
            # Wrap around
            part1 = self._edf_data[self._cursor:]
            part2 = self._edf_data[:n_samples - len(part1)]
            window = np.concatenate([part1, part2], axis=0)
            self.current_intent = int(
                np.bincount(self._edf_labels[self._cursor:]).argmax()
            )
            self._cursor = n_samples - len(part1)

        return window

    def _synthetic_window(self, n_samples: int) -> np.ndarray:
        """Fallback: simple sine-wave motor imagery simulation."""
        t = np.linspace(0, n_samples / self.fs, n_samples)
        eeg = np.random.randn(n_samples, self.n_channels) * 3.0
        # cycle through intents every ~3s worth of windows
        intent = (self._cursor // (self.fs * 3)) % 5
        self.current_intent = intent
        self._cursor += n_samples
        c3, c4 = self._c3_idx, self._c4_idx
        if intent == 2:    # Left
            eeg[:, c3] += 18 * np.sin(2 * np.pi * 10 * t)
            eeg[:, c4] += 5  * np.sin(2 * np.pi * 10 * t)
        elif intent == 3:  # Right
            eeg[:, c3] += 5  * np.sin(2 * np.pi * 10 * t)
            eeg[:, c4] += 18 * np.sin(2 * np.pi * 10 * t)
        else:
            eeg[:, c3] += 15 * np.sin(2 * np.pi * 18 * t)
            eeg[:, c4] += 15 * np.sin(2 * np.pi * 18 * t)
        return eeg

    def advance_sim_intent(self):
        """No-op — dataset replay drives intent automatically."""
        pass

    @property
    def c3_idx(self):
        return self._c3_idx

    @property
    def c4_idx(self):
        return self._c4_idx

    def stop(self):
        if self._bridge:
            self._bridge.stop_stream()


# ------------------------------------------------------------------
# EEG → Intent decoder
# ------------------------------------------------------------------

class BCIDecoder:
    """
    Extracts motor imagery intent from EEG window.
    Uses C3/C4 mu (8-13 Hz) and beta (13-30 Hz) power asymmetry.

    Returns: (intent_id, label, confidence)
    Intent map:
        0 = Forward   (bilateral mu suppression)
        1 = Backward  (bilateral beta increase)
        2 = Left      (C3 dominant mu suppression)
        3 = Right     (C4 dominant mu suppression)
        4 = Hover     (rest / strong bilateral beta)
    """

    LABELS = {0: "Forward", 1: "Backward", 2: "Left", 3: "Right", 4: "Hover"}

    def __init__(self, fs: int = 250, use_ml: bool = False,
                 c3_idx: int = 7, c4_idx: int = 11):
        self.fs = fs
        self.c3_idx = c3_idx
        self.c4_idx = c4_idx
        self.use_ml = use_ml
        self._ml_model = None
        self._history = deque(maxlen=5)  # smooth over last 5 predictions

        if use_ml:
            self._load_ml_model()

    def _load_ml_model(self):
        try:
            from decoding.hybrid_decoder import HybridDecoder
            self._ml_model = HybridDecoder()
            self._ml_model.load_models()
            print("[bci] ML model loaded")
        except Exception as e:
            print(f"[bci] ML model load failed ({e}) — using signal heuristics")
            self.use_ml = False

    def decode(self, eeg: np.ndarray):
        """
        Decode EEG window into drone intent.
        Returns (intent_id, label, confidence, features_dict)
        """
        from scipy.signal import welch

        # Extract C3/C4 band powers
        c3, c4 = eeg[:, self.c3_idx], eeg[:, self.c4_idx]

        def band_power(sig, lo, hi):
            freqs, psd = welch(sig, fs=self.fs, nperseg=min(128, len(sig)))
            mask = (freqs >= lo) & (freqs <= hi)
            return float(np.mean(psd[mask])) if mask.any() else 0.0

        c3_mu   = band_power(c3, 8, 13)
        c4_mu   = band_power(c4, 8, 13)
        c3_beta = band_power(c3, 13, 30)
        c4_beta = band_power(c4, 13, 30)

        # Debug: print once to verify scale
        if not hasattr(self, '_scale_printed'):
            print(f"[bci] PSD scale check — C3 mu={c3_mu:.4f} C4 mu={c4_mu:.4f} "
                  f"C3 beta={c3_beta:.4f} C4 beta={c4_beta:.4f}")
            self._scale_printed = True

        mu_asym  = (c3_mu - c4_mu) / (c3_mu + c4_mu + 1e-9)   # +1=left, -1=right
        beta_avg = (c3_beta + c4_beta) / 2.0
        mu_avg   = (c3_mu + c4_mu) / 2.0

        features = {
            "c3_mu": c3_mu, "c4_mu": c4_mu,
            "c3_beta": c3_beta, "c4_beta": c4_beta,
            "mu_asym": mu_asym, "beta_avg": beta_avg
        }

        # Use ML model if available
        if self.use_ml and self._ml_model:
            feat_vec = np.array([c3_mu, c4_mu, c3_beta, c4_beta,
                                 mu_asym, beta_avg, mu_avg, 0])
            result = self._ml_model.predict(feat_vec)
            intent = result["intent"]
            conf = result["confidence"]
        else:
            intent, conf = self._heuristic_decode(
                mu_asym, beta_avg, mu_avg, c3_mu, c4_mu
            )

        # Temporal smoothing
        self._history.append(intent)
        smoothed = max(set(self._history), key=list(self._history).count)

        return smoothed, self.LABELS[smoothed], conf, features

    def _heuristic_decode(self, mu_asym, beta_avg, mu_avg, c3_mu, c4_mu):
        """
        Rule-based decoder using EEG signal heuristics.
        Works without any training data.
        """
        # Thresholds tuned for real PhysioNet µV² PSD values
        ASYM_THRESH  = 0.10   # asymmetry threshold for left/right
        BETA_HIGH    = 0.3    # high beta power (µV²/Hz)
        MU_SUPP      = 0.2    # mu power threshold

        # Hover: strong bilateral beta, low mu
        if beta_avg > BETA_HIGH and mu_avg < MU_SUPP:
            return 4, 0.80

        # Left: C3 mu suppression dominant
        if mu_asym > ASYM_THRESH:
            conf = min(0.95, 0.6 + abs(mu_asym))
            return 2, conf

        # Right: C4 mu suppression dominant
        if mu_asym < -ASYM_THRESH:
            conf = min(0.95, 0.6 + abs(mu_asym))
            return 3, conf

        # Forward: bilateral mu suppression
        if mu_avg > MU_SUPP and beta_avg < BETA_HIGH:
            return 0, 0.70

        # Backward: bilateral beta increase
        if beta_avg > BETA_HIGH * 0.6:
            return 1, 0.65

        # Default: hover
        return 4, 0.55


# ------------------------------------------------------------------
# Intent → flight command (user-configurable)
# ------------------------------------------------------------------

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
ACTION_NAMES = list(DRONE_ACTIONS.keys())

class SignalMapping:
    """Configurable mapping from BCI intent → drone action."""
    INTENT_NAMES = {0:"Forward", 1:"Backward", 2:"Left", 3:"Right", 4:"Hover"}
    DEFAULT = {
        0: "Pitch Forward",
        1: "Pitch Backward",
        2: "Roll Left",
        3: "Roll Right",
        4: "Hover",
    }
    def __init__(self):
        self.mapping = dict(self.DEFAULT)
        self.menu_open = False
        self.selected_intent = None

    def get_command(self, intent_id):
        action_name = self.mapping.get(intent_id, "Hover")
        return DRONE_ACTIONS.get(action_name, (0., 0., 0., 0.))

    def set_mapping(self, intent_id, action_name):
        if action_name in DRONE_ACTIONS:
            self.mapping[intent_id] = action_name


# ------------------------------------------------------------------
# Drawing helpers (reused from keyboard_pilot)
# ------------------------------------------------------------------

BG = (15, 15, 25); GRID = (30, 30, 45)
DRONE_BODY = (80, 180, 255); DRONE_ARM = (60, 140, 200)
PROP_SPIN = (120, 220, 120); PROP_IDLE = (80, 80, 80)
HUD_TEXT = (200, 220, 255); HUD_WARN = (255, 80, 80); HUD_OK = (80, 255, 140)
W, H = 900, 650


def draw_drone(surface, state, prop_angle):
    x, y = int(state.x), int(state.y)
    yaw_rad = math.radians(state.yaw)
    for ao in [45, 135, 225, 315]:
        ar = yaw_rad + math.radians(ao)
        ex = int(x + 22 * math.cos(ar))
        ey = int(y + 22 * math.sin(ar))
        pygame.draw.line(surface, DRONE_ARM, (x, y), (ex, ey), 3)
        color = PROP_SPIN if state.flying else PROP_IDLE
        pygame.draw.circle(surface, color, (ex, ey), 10, 2)
        if state.flying:
            bx = int(ex + 10 * math.cos(prop_angle + math.radians(ao)))
            by = int(ey + 10 * math.sin(prop_angle + math.radians(ao)))
            pygame.draw.line(surface, color, (ex, ey), (bx, by), 2)
    pygame.draw.circle(surface, DRONE_BODY, (x, y), 10)
    hx = int(x + 18 * math.cos(yaw_rad))
    hy = int(y + 18 * math.sin(yaw_rad))
    pygame.draw.line(surface, (255, 200, 0), (x, y), (hx, hy), 3)


def draw_eeg_panel(surface, features: dict, intent_label: str,
                   confidence: float, font, small_font, bci_active: bool):
    """EEG signal visualization panel on the right side."""
    px, py, pw, ph = W - 210, 10, 200, 300
    pygame.draw.rect(surface, (20, 20, 35), (px, py, pw, ph), border_radius=8)
    pygame.draw.rect(surface, (80, 50, 120), (px, py, pw, ph), 1, border_radius=8)

    title_color = (180, 100, 255) if bci_active else (100, 100, 120)
    title = font.render("BCI INPUT", True, title_color)
    surface.blit(title, (px + 10, py + 10))

    if not bci_active:
        off = small_font.render("(keyboard mode)", True, (100, 100, 120))
        surface.blit(off, (px + 10, py + 35))
        return

    # Intent display
    intent_surf = font.render(f"→ {intent_label}", True, HUD_OK)
    surface.blit(intent_surf, (px + 10, py + 38))

    conf_color = HUD_OK if confidence > 0.7 else HUD_WARN
    conf_surf = small_font.render(f"Conf: {confidence:.0%}", True, conf_color)
    surface.blit(conf_surf, (px + 10, py + 65))

    # Band power bars
    bars = [
        ("C3 μ",   features.get("c3_mu", 0),   (100, 180, 255)),
        ("C4 μ",   features.get("c4_mu", 0),   (80,  140, 220)),
        ("C3 β",   features.get("c3_beta", 0), (180, 100, 255)),
        ("C4 β",   features.get("c4_beta", 0), (140, 80,  220)),
    ]
    max_val = max(b[1] for b in bars) + 1e-9
    for i, (label, val, color) in enumerate(bars):
        bar_y = py + 100 + i * 45
        bar_w = int((val / max_val) * 160)
        pygame.draw.rect(surface, (40, 40, 60), (px + 10, bar_y, 160, 18), border_radius=3)
        pygame.draw.rect(surface, color, (px + 10, bar_y, bar_w, 18), border_radius=3)
        lbl = small_font.render(label, True, HUD_TEXT)
        surface.blit(lbl, (px + 10, bar_y - 14))

    # Asymmetry indicator
    asym = features.get("mu_asym", 0)
    asym_y = py + 285
    pygame.draw.rect(surface, (40, 40, 60), (px + 10, asym_y, 160, 8), border_radius=3)
    mid = px + 10 + 80
    bar_len = int(asym * 80)
    color = (100, 200, 255) if asym > 0 else (255, 150, 80)
    pygame.draw.rect(surface, color, (mid, asym_y, bar_len, 8))
    asym_lbl = small_font.render(f"L←Asym→R  {asym:+.2f}", True, HUD_TEXT)
    surface.blit(asym_lbl, (px + 10, asym_y - 14))


def draw_mapping_menu_2d(surface, font, small_font, sig_map):
    """Draw neural signal mapping overlay for 2D simulator."""
    MW2, MH2 = 440, 350
    MX2 = W//2 - MW2//2
    MY2 = H//2 - MH2//2

    # Dimmed backdrop
    dim = pygame.Surface((W, H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 180))
    surface.blit(dim, (0, 0))

    # Panel
    pygame.draw.rect(surface, (20, 20, 35), (MX2, MY2, MW2, MH2), border_radius=8)
    pygame.draw.rect(surface, (180, 100, 255), (MX2, MY2, MW2, MH2), 2, border_radius=8)

    # Title
    title = font.render("NEURAL SIGNAL MAPPING", True, (180, 100, 255))
    surface.blit(title, (MX2 + MW2//2 - title.get_width()//2, MY2 + 10))

    # Instructions
    inst = small_font.render("Click intent, then press 1-9 to assign | M to close", True, (140, 160, 200))
    surface.blit(inst, (MX2 + MW2//2 - inst.get_width()//2, MY2 + 35))

    # Headers
    surface.blit(small_font.render("#", True, (100,180,255)), (MX2+12, MY2+58))
    surface.blit(small_font.render("INTENT", True, (100,180,255)), (MX2+35, MY2+58))
    surface.blit(small_font.render("DRONE ACTION", True, (100,180,255)), (MX2+210, MY2+58))

    for i in range(5):
        row_y = MY2 + 78 + i * 38
        is_sel = (sig_map.selected_intent == i)
        if is_sel:
            pygame.draw.rect(surface, (60,30,100), (MX2+8, row_y, MW2-16, 32), border_radius=4)
            pygame.draw.rect(surface, (180,100,255), (MX2+8, row_y, MW2-16, 32), 1, border_radius=4)
        col = (80,255,140) if is_sel else (200,220,255)
        surface.blit(font.render(f"{i}", True, (100,100,120)), (MX2+14, row_y+7))
        surface.blit(font.render(sig_map.INTENT_NAMES[i], True, col), (MX2+38, row_y+7))
        action = sig_map.mapping.get(i, "Hover")
        acol = (255,150,80) if is_sel else (100,180,255)
        surface.blit(font.render(f"-> {action}", True, acol), (MX2+215, row_y+7))

    # Legend
    leg_y = MY2 + MH2 - 50
    leg1 = "1=Up 2=Down 3=Fwd 4=Back 5=RollL"
    leg2 = "6=RollR 7=YawL 8=YawR 9=Hover"
    surface.blit(small_font.render(leg1, True, (100,100,120)), (MX2+15, leg_y))
    surface.blit(small_font.render(leg2, True, (100,100,120)), (MX2+15, leg_y+18))


# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------

def run(backend_name: str = "sim", use_bci: bool = True,
        use_real_eeg: bool = False, use_ml: bool = False):

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mind Link — BCI + Keyboard Pilot")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 14)

    state = DroneState()
    state.x, state.y = 450, 325

    # Backend
    if backend_name == "mavlink":
        backend = MavlinkBackend()
    elif backend_name == "tello":
        backend = TelloBackend()
    else:
        backend = SimBackend(state)

    if not backend.connect():
        backend = SimBackend(state)

    # EEG + decoder
    eeg_source = EEGSource(use_real=use_real_eeg)
    bci_decoder = BCIDecoder(
        fs=eeg_source.fs,
        use_ml=use_ml,
        c3_idx=eeg_source.c3_idx,
        c4_idx=eeg_source.c4_idx
    ) if use_bci else None

    # State
    trail = []
    prop_angle = 0.0
    bci_intent = 4
    bci_label = "Hover"
    bci_conf = 0.0
    bci_features = {}
    last_bci_time = 0.0
    BCI_INTERVAL = 0.25  # decode every 250 ms

    # Neural signal mapping
    sig_map = SignalMapping()

    # Sim intent cycling
    sim_intent_timer = 0.0
    SIM_INTENT_DURATION = 3.0

    print("\n[bci_pilot] Ready — T=Takeoff, M=Mapping, ESC=Quit")
    print(f"[bci_pilot] BCI: {'ON' if use_bci else 'OFF (keyboard only)'}")

    running = True
    while running:
        dt = clock.tick(20) / 1000.0

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if sig_map.menu_open:
                        sig_map.menu_open = False
                        sig_map.selected_intent = None
                    else:
                        backend.emergency_stop(); running = False
                elif event.key == pygame.K_m:
                    sig_map.menu_open = not sig_map.menu_open
                    sig_map.selected_intent = None
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
                        sig_map.selected_intent = None
                elif sig_map.menu_open:
                    intent_keys = {
                        pygame.K_0: 0, pygame.K_1: 1, pygame.K_2: 2,
                        pygame.K_3: 3, pygame.K_4: 4,
                    }
                    if event.key in intent_keys:
                        sig_map.selected_intent = intent_keys[event.key]
                elif event.key == pygame.K_t:
                    backend.takeoff()
                elif event.key == pygame.K_l:
                    backend.land()
                elif event.key == pygame.K_SPACE:
                    state.mode = "HOVER"
                elif event.key == pygame.K_b:
                    use_bci = not use_bci
                    print(f"[bci_pilot] BCI {'enabled' if use_bci else 'disabled'}")
            # Mouse click to select intent in mapping menu
            if event.type == pygame.MOUSEBUTTONDOWN and sig_map.menu_open:
                mx, my = event.pos
                MW2, MH2 = 440, 350
                MX2 = W//2 - MW2//2
                MY2 = H//2 - MH2//2
                for i in range(5):
                    row_y = MY2 + 78 + i * 38
                    if MX2+8 <= mx <= MX2+MW2-8 and row_y <= my <= row_y+32:
                        sig_map.selected_intent = i
                        break

        # --- Keyboard input ---
        keys = pygame.key.get_pressed()
        kb_pitch = kb_roll = kb_yaw = kb_throttle = 0.0
        if keys[pygame.K_UP]:    kb_pitch    =  1.0
        if keys[pygame.K_DOWN]:  kb_pitch    = -1.0
        if keys[pygame.K_LEFT]:  kb_roll     = -1.0
        if keys[pygame.K_RIGHT]: kb_roll     =  1.0
        if keys[pygame.K_w]:     kb_throttle =  1.0
        if keys[pygame.K_s]:     kb_throttle = -1.0
        if keys[pygame.K_a]:     kb_yaw      = -1.0
        if keys[pygame.K_d]:     kb_yaw      =  1.0
        kb_active = any([kb_pitch, kb_roll, kb_yaw, kb_throttle])

        # --- BCI decode (every 250 ms) ---
        if use_bci and (time.time() - last_bci_time) > BCI_INTERVAL:
            n_samples = int(eeg_source.fs * 0.5)  # 500ms window
            eeg_win = eeg_source.get_window(n_samples)
            bci_intent, bci_label, bci_conf, bci_features = bci_decoder.decode(eeg_win)
            last_bci_time = time.time()

            # Advance simulated thought (no-op for dataset replay)
            sim_intent_timer += BCI_INTERVAL
            if sim_intent_timer >= SIM_INTENT_DURATION:
                eeg_source.advance_sim_intent()
                sim_intent_timer = 0.0

        # --- Merge inputs (keyboard overrides BCI) ---
        if kb_active:
            pitch, roll, yaw, throttle = kb_pitch, kb_roll, kb_yaw, kb_throttle
            source = "KB"
        elif use_bci and state.flying and bci_conf > 0.45:
            p, r, y, t2 = sig_map.get_command(bci_intent)
            pitch, roll, yaw, throttle = p, r, y, t2
            source = "BCI"
        else:
            pitch = roll = yaw = throttle = 0.0
            source = "IDLE"

        if state.flying and any([pitch, roll, yaw, throttle]):
            state.mode = "FLYING"
            backend.send_command(pitch, roll, yaw, throttle)

        # Prop + trail
        if state.flying:
            prop_angle += dt * 15
            trail.append((int(state.x), int(state.y)))
            if len(trail) > 100:
                trail.pop(0)

        # --- Draw ---
        screen.fill(BG)
        for x in range(0, W, 50):
            pygame.draw.line(screen, GRID, (x, 0), (x, H))
        for y in range(0, H, 50):
            pygame.draw.line(screen, GRID, (0, y), (W, y))

        # Trail
        for i, pos in enumerate(trail):
            a = int(80 * i / max(len(trail), 1))
            pygame.draw.circle(screen, (40+a, 80+a, 120+a), pos, 2)

        draw_drone(screen, state, prop_angle)

        # HUD
        pygame.draw.rect(screen, (20, 20, 35), (10, 10, 220, 230), border_radius=8)
        pygame.draw.rect(screen, (50, 80, 120), (10, 10, 220, 230), 1, border_radius=8)
        mode_color = HUD_OK if state.flying else HUD_WARN
        for i, (txt, col) in enumerate([
            (f"MODE:  {state.mode}", mode_color),
            (f"ALT:   {state.altitude:.1f} m", HUD_TEXT),
            (f"YAW:   {state.yaw:.0f}°", HUD_TEXT),
            (f"POS:   {state.x:.0f}, {state.y:.0f}", HUD_TEXT),
            (f"INPUT: {source}", HUD_OK if source == "BCI" else HUD_TEXT),
            (f"ARMED: {'YES' if state.armed else 'NO'}", HUD_OK if state.armed else HUD_WARN),
        ]):
            screen.blit(font.render(txt, True, col), (20, 20 + i * 30))

        # BCI panel
        draw_eeg_panel(screen, bci_features, bci_label, bci_conf,
                       font, small_font, use_bci)

        # Controls hint
        pygame.draw.rect(screen, (20, 20, 35), (10, H-110, 420, 100), border_radius=8)
        pygame.draw.rect(screen, (50, 80, 120), (10, H-110, 420, 100), 1, border_radius=8)
        for i, hint in enumerate([
            "T=Takeoff  L=Land  SPACE=Hover  B=BCI  M=Mapping  ESC=Stop",
            "W/S=Throttle  A/D=Yaw  Arrows=Pitch/Roll",
            "Keyboard overrides BCI | M opens signal mapping",
        ]):
            screen.blit(small_font.render(hint, True, (140, 160, 200)), (20, H-100 + i*26))

        # Altitude bar
        bar_h = int(min(state.altitude / 10.0, 1.0) * 200)
        pygame.draw.rect(screen, (30, 30, 50), (W-30, H//2-100, 20, 200), border_radius=4)
        pygame.draw.rect(screen, (80, 200, 120),
                         (W-30, H//2+100-bar_h, 20, bar_h), border_radius=4)
        screen.blit(small_font.render("ALT", True, HUD_TEXT), (W-35, H//2+105))

        # Signal mapping menu overlay
        if sig_map.menu_open:
            draw_mapping_menu_2d(screen, font, small_font, sig_map)

        pygame.display.flip()

    pygame.quit()
    eeg_source.stop()
    backend.disconnect()
    print("[bci_pilot] Session ended")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="sim",
                        choices=["sim", "mavlink", "tello"])
    parser.add_argument("--no-bci", action="store_true",
                        help="Keyboard only mode")
    parser.add_argument("--real-eeg", action="store_true",
                        help="Use real EEG headset via LSL")
    parser.add_argument("--ml", action="store_true",
                        help="Use trained ML decoder instead of heuristics")
    args = parser.parse_args()

    run(
        backend_name=args.backend,
        use_bci=not args.no_bci,
        use_real_eeg=args.real_eeg,
        use_ml=args.ml
    )
