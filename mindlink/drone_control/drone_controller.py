"""
Drone Controller — Simulation + Real Hardware
Keyboard control via pygame. Swap backend for real drone.

Controls:
    W / S       — Throttle up / down
    A / D       — Yaw left / right
    ↑ / ↓       — Pitch forward / backward
    ← / →       — Roll left / right
    SPACE       — Hover (hold position)
    T           — Takeoff
    L           — Land
    ESC         — Emergency stop
"""

import time
import math
import threading
import numpy as np

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[drone] pygame not found — install with: pip install pygame")


# ------------------------------------------------------------------
# Drone state
# ------------------------------------------------------------------

class DroneState:
    def __init__(self):
        self.x = 400.0          # pixels (sim) or meters (real)
        self.y = 300.0
        self.altitude = 0.0     # meters
        self.yaw = 0.0          # degrees
        self.pitch_vel = 0.0
        self.roll_vel = 0.0
        self.yaw_vel = 0.0
        self.throttle = 0.0
        self.armed = False
        self.flying = False
        self.mode = "IDLE"      # IDLE / FLYING / HOVER / LANDING

    def to_dict(self):
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "altitude": round(self.altitude, 2),
            "yaw": round(self.yaw, 1),
            "mode": self.mode,
            "armed": self.armed
        }


# ------------------------------------------------------------------
# Backend interface
# ------------------------------------------------------------------

class DroneBackend:
    """Base class — swap for real hardware."""

    def connect(self) -> bool:
        return True

    def send_command(self, pitch: float, roll: float, yaw: float,
                     throttle: float):
        pass

    def takeoff(self):
        pass

    def land(self):
        pass

    def emergency_stop(self):
        pass

    def disconnect(self):
        pass


class SimBackend(DroneBackend):
    """Pure simulation — updates DroneState locally."""

    def __init__(self, state: DroneState):
        self.state = state

    def connect(self) -> bool:
        print("[sim] Simulation backend connected")
        return True

    def send_command(self, pitch, roll, yaw, throttle):
        s = self.state
        if not s.flying:
            return
        dt = 0.05  # 20 Hz update

        # Update yaw
        s.yaw = (s.yaw + yaw * dt * 60) % 360

        # Move in yaw direction
        rad = math.radians(s.yaw)
        s.x += (pitch * math.cos(rad) - roll * math.sin(rad)) * dt * 80
        s.y += (pitch * math.sin(rad) + roll * math.cos(rad)) * dt * 80

        # Altitude hold: only change altitude when throttle is applied
        if throttle != 0.0:
            s.altitude = max(0.0, s.altitude + throttle * dt * 3)

        # Clamp to window
        s.x = max(30, min(770, s.x))
        s.y = max(30, min(570, s.y))

    def takeoff(self):
        self.state.flying = True
        self.state.armed = True
        self.state.altitude = 1.5
        self.state.mode = "FLYING"
        print("[sim] Takeoff!")

    def land(self):
        self.state.flying = False
        self.state.altitude = 0.0
        self.state.mode = "LANDING"
        print("[sim] Landing...")
        time.sleep(0.5)
        self.state.mode = "IDLE"

    def emergency_stop(self):
        self.state.flying = False
        self.state.altitude = 0.0
        self.state.mode = "IDLE"
        print("[sim] EMERGENCY STOP")


class MavlinkBackend(DroneBackend):
    """Real drone via MAVLink (Pixhawk / ArduPilot / Betaflight)."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self.port = port
        self.baud = baud
        self._conn = None

    def connect(self) -> bool:
        try:
            from pymavlink import mavutil
            self._conn = mavutil.mavlink_connection(self.port, baud=self.baud)
            self._conn.wait_heartbeat(timeout=5)
            print(f"[mavlink] Connected — system {self._conn.target_system}")
            return True
        except Exception as e:
            print(f"[mavlink] Connection failed: {e}")
            return False

    def send_command(self, pitch, roll, yaw, throttle):
        if not self._conn:
            return
        try:
            self._conn.mav.rc_channels_override_send(
                self._conn.target_system,
                self._conn.target_component,
                # CH1=Roll, CH2=Pitch, CH3=Throttle, CH4=Yaw
                int(1500 + roll * 500),
                int(1500 + pitch * 500),
                int(1000 + (throttle + 1) * 500),
                int(1500 + yaw * 500),
                0, 0, 0, 0
            )
        except Exception as e:
            print(f"[mavlink] Send error: {e}")

    def takeoff(self):
        if not self._conn:
            return
        try:
            self._conn.mav.command_long_send(
                self._conn.target_system,
                self._conn.target_component,
                22,  # MAV_CMD_NAV_TAKEOFF
                0, 0, 0, 0, 0, 0, 0, 2.0  # 2m altitude
            )
            print("[mavlink] Takeoff command sent")
        except Exception as e:
            print(f"[mavlink] Takeoff error: {e}")

    def land(self):
        if not self._conn:
            return
        try:
            self._conn.mav.command_long_send(
                self._conn.target_system,
                self._conn.target_component,
                21,  # MAV_CMD_NAV_LAND
                0, 0, 0, 0, 0, 0, 0, 0
            )
            print("[mavlink] Land command sent")
        except Exception as e:
            print(f"[mavlink] Land error: {e}")

    def emergency_stop(self):
        if self._conn:
            try:
                self._conn.mav.command_long_send(
                    self._conn.target_system,
                    self._conn.target_component,
                    400,  # MAV_CMD_COMPONENT_ARM_DISARM
                    0, 0, 0, 0, 0, 0, 0, 0  # disarm
                )
                print("[mavlink] Disarmed")
            except Exception as e:
                print(f"[mavlink] Disarm error: {e}")

    def disconnect(self):
        if self._conn:
            self._conn.close()


class TelloBackend(DroneBackend):
    """DJI Tello via djitellopy."""

    def __init__(self):
        self._tello = None

    def connect(self) -> bool:
        try:
            from djitellopy import Tello
            self._tello = Tello()
            self._tello.connect()
            print(f"[tello] Battery: {self._tello.get_battery()}%")
            return True
        except Exception as e:
            print(f"[tello] Connection failed: {e}")
            return False

    def send_command(self, pitch, roll, yaw, throttle):
        if not self._tello:
            return
        self._tello.send_rc_control(
            int(roll * 100),
            int(pitch * 100),
            int(throttle * 100),
            int(yaw * 100)
        )

    def takeoff(self):
        if self._tello:
            self._tello.takeoff()

    def land(self):
        if self._tello:
            self._tello.land()

    def emergency_stop(self):
        if self._tello:
            self._tello.emergency()

    def disconnect(self):
        if self._tello:
            self._tello.end()
