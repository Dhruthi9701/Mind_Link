"""
Keyboard Pilot — Pygame simulation window
Run: python drone_control/keyboard_pilot.py

Controls:
    T           — Takeoff
    L           — Land
    SPACE       — Hover
    W / S       — Throttle up / down
    A / D       — Yaw left / right
    ↑ / ↓       — Pitch forward / backward
    ← / →       — Roll left / right
    ESC         — Emergency stop / quit
"""

import sys
import os
import math
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pygame
except ImportError:
    print("pygame not found. Install with: pip install pygame")
    sys.exit(1)

from drone_control.drone_controller import DroneState, SimBackend, MavlinkBackend, TelloBackend

# ------------------------------------------------------------------
# Colors
# ------------------------------------------------------------------
BG          = (15, 15, 25)
GRID        = (30, 30, 45)
DRONE_BODY  = (80, 180, 255)
DRONE_ARM   = (60, 140, 200)
PROP_SPIN   = (120, 220, 120)
PROP_IDLE   = (80, 80, 80)
HUD_TEXT    = (200, 220, 255)
HUD_WARN    = (255, 80, 80)
HUD_OK      = (80, 255, 140)
TRAIL       = (40, 80, 120)

W, H = 800, 600


def draw_drone(surface, state: DroneState, font, prop_angle: float):
    """Draw drone top-down view with rotating props."""
    x, y = int(state.x), int(state.y)
    yaw_rad = math.radians(state.yaw)
    arm_len = 22
    prop_r = 10

    # Draw trail (ghost positions stored externally)
    pass

    # Arms (X configuration)
    for angle_offset in [45, 135, 225, 315]:
        arm_rad = yaw_rad + math.radians(angle_offset)
        ex = int(x + arm_len * math.cos(arm_rad))
        ey = int(y + arm_len * math.sin(arm_rad))
        pygame.draw.line(surface, DRONE_ARM, (x, y), (ex, ey), 3)

        # Propeller
        color = PROP_SPIN if state.flying else PROP_IDLE
        pygame.draw.circle(surface, color, (ex, ey), prop_r, 2)

        # Spinning blade indicator
        if state.flying:
            bx = int(ex + prop_r * math.cos(prop_angle + angle_offset))
            by = int(ey + prop_r * math.sin(prop_angle + angle_offset))
            pygame.draw.line(surface, color, (ex, ey), (bx, by), 2)

    # Body center
    pygame.draw.circle(surface, DRONE_BODY, (x, y), 10)

    # Heading indicator
    hx = int(x + 18 * math.cos(yaw_rad))
    hy = int(y + 18 * math.sin(yaw_rad))
    pygame.draw.line(surface, (255, 200, 0), (x, y), (hx, hy), 3)


def draw_hud(surface, state: DroneState, font, small_font, controls):
    """Draw HUD overlay."""
    # Status panel background
    pygame.draw.rect(surface, (20, 20, 35), (10, 10, 220, 200), border_radius=8)
    pygame.draw.rect(surface, (50, 80, 120), (10, 10, 220, 200), 1, border_radius=8)

    mode_color = HUD_OK if state.flying else HUD_WARN
    lines = [
        (f"MODE: {state.mode}", mode_color),
        (f"ALT:  {state.altitude:.1f} m", HUD_TEXT),
        (f"YAW:  {state.yaw:.0f}°", HUD_TEXT),
        (f"X:    {state.x:.0f}  Y: {state.y:.0f}", HUD_TEXT),
        (f"ARMED: {'YES' if state.armed else 'NO'}", HUD_OK if state.armed else HUD_WARN),
    ]
    for i, (text, color) in enumerate(lines):
        surf = font.render(text, True, color)
        surface.blit(surf, (20, 20 + i * 28))

    # Controls hint (bottom)
    pygame.draw.rect(surface, (20, 20, 35), (10, H - 130, 380, 120), border_radius=8)
    pygame.draw.rect(surface, (50, 80, 120), (10, H - 130, 380, 120), 1, border_radius=8)
    hints = [
        "T=Takeoff  L=Land  SPACE=Hover  ESC=Stop",
        "W/S = Throttle    A/D = Yaw",
        "↑/↓ = Pitch       ←/→ = Roll",
    ]
    for i, hint in enumerate(hints):
        surf = small_font.render(hint, True, (140, 160, 200))
        surface.blit(surf, (20, H - 120 + i * 26))

    # Active controls indicator
    active = [k for k, v in controls.items() if v]
    if active:
        ctrl_text = "  ".join(active)
        surf = small_font.render(f"INPUT: {ctrl_text}", True, (255, 220, 80))
        surface.blit(surf, (W - 300, H - 30))


def draw_grid(surface):
    """Draw background grid."""
    for x in range(0, W, 50):
        pygame.draw.line(surface, GRID, (x, 0), (x, H))
    for y in range(0, H, 50):
        pygame.draw.line(surface, GRID, (0, y), (W, y))


def run(backend_name: str = "sim"):
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mind Link — Drone Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    small_font = pygame.font.SysFont("consolas", 14)

    state = DroneState()

    # Select backend
    if backend_name == "mavlink":
        backend = MavlinkBackend()
    elif backend_name == "tello":
        backend = TelloBackend()
    else:
        backend = SimBackend(state)

    if not backend.connect():
        print("Failed to connect. Falling back to simulation.")
        backend = SimBackend(state)

    trail = []  # position history
    prop_angle = 0.0
    running = True

    controls = {
        "THROTTLE↑": False, "THROTTLE↓": False,
        "YAW←": False, "YAW→": False,
        "PITCH↑": False, "PITCH↓": False,
        "ROLL←": False, "ROLL→": False,
    }

    print("\n[keyboard_pilot] Window open — press T to takeoff\n")

    while running:
        dt = clock.tick(20) / 1000.0  # 20 Hz

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    backend.emergency_stop()
                    running = False
                elif event.key == pygame.K_t:
                    backend.takeoff()
                elif event.key == pygame.K_l:
                    backend.land()
                elif event.key == pygame.K_SPACE:
                    state.mode = "HOVER"
                    print("[pilot] Hover")

        # --- Held keys ---
        keys = pygame.key.get_pressed()
        pitch = roll = yaw = throttle = 0.0

        if keys[pygame.K_UP]:
            pitch = 1.0;    controls["PITCH↑"] = True
        else:               controls["PITCH↑"] = False

        if keys[pygame.K_DOWN]:
            pitch = -1.0;   controls["PITCH↓"] = True
        else:               controls["PITCH↓"] = False

        if keys[pygame.K_LEFT]:
            roll = -1.0;    controls["ROLL←"] = True
        else:               controls["ROLL←"] = False

        if keys[pygame.K_RIGHT]:
            roll = 1.0;     controls["ROLL→"] = True
        else:               controls["ROLL→"] = False

        if keys[pygame.K_w]:
            throttle = 1.0; controls["THROTTLE↑"] = True
        else:               controls["THROTTLE↑"] = False

        if keys[pygame.K_s]:
            throttle = -1.0; controls["THROTTLE↓"] = True
        else:               controls["THROTTLE↓"] = False

        if keys[pygame.K_a]:
            yaw = -1.0;     controls["YAW←"] = True
        else:               controls["YAW←"] = False

        if keys[pygame.K_d]:
            yaw = 1.0;      controls["YAW→"] = True
        else:               controls["YAW→"] = False

        # Send to backend
        if any([pitch, roll, yaw, throttle]):
            state.mode = "FLYING" if state.flying else state.mode
            backend.send_command(pitch, roll, yaw, throttle)

        # Prop animation
        if state.flying:
            prop_angle += dt * 15

        # Trail
        if state.flying:
            trail.append((int(state.x), int(state.y)))
            if len(trail) > 80:
                trail.pop(0)

        # --- Draw ---
        screen.fill(BG)
        draw_grid(screen)

        # Trail
        for i, pos in enumerate(trail):
            alpha = int(80 * i / max(len(trail), 1))
            pygame.draw.circle(screen, (40 + alpha, 80 + alpha, 120 + alpha), pos, 2)

        draw_drone(screen, state, font, prop_angle)
        draw_hud(screen, state, font, small_font, controls)

        # Altitude bar (right side)
        bar_h = int(state.altitude / 10.0 * 200)
        pygame.draw.rect(screen, (30, 30, 50), (W - 30, H // 2 - 100, 20, 200), border_radius=4)
        pygame.draw.rect(screen, (80, 200, 120), (W - 30, H // 2 + 100 - bar_h, 20, bar_h), border_radius=4)
        alt_label = small_font.render("ALT", True, HUD_TEXT)
        screen.blit(alt_label, (W - 35, H // 2 + 105))

        pygame.display.flip()

    pygame.quit()
    backend.disconnect()
    print("[keyboard_pilot] Session ended")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="sim",
                        choices=["sim", "mavlink", "tello"],
                        help="Backend: sim (default), mavlink, tello")
    args = parser.parse_args()
    run(backend_name=args.backend)
