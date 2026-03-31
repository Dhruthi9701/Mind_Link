"""
Mind Link — 3D BCI Drone Simulator (Ursina Engine)  — minimal demo
===================================================================
Run:  python mindlink/drone_control/sim_ursina.py
Keys: T=Takeoff  L=Land  SPACE=Hover  B=BCI  C=Camera  ESC=Quit
      W/S=Throttle  A/D=Yaw  Arrows=Pitch/Roll
"""

import sys, os, math, time
import numpy as np
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ursina import *
from mindlink.drone_control.sim3d import EEGSource, BCIDecoder, SignalMapping

# ── Palette ─────────────────────────────────────────────────────────
C_BG        = color.hex("#04060e")
C_PANEL     = color.hex("#060a14")
C_PANEL_BAR = color.hex("#0e1020")
C_CYAN      = color.hex("#00dcff")
C_CYAN_DIM  = color.hex("#004455")
C_PURPLE    = color.hex("#a03cff")
C_ORANGE    = color.hex("#ff8c00")
C_GREEN     = color.hex("#28ff78")
C_RED       = color.hex("#ff3232")
C_YELLOW    = color.hex("#ffdc00")
C_GREY      = color.hex("#606878")

# ══════════════════════════════════════════════════════════════════════
# WORLD
# ══════════════════════════════════════════════════════════════════════

def _line_mesh(pairs):
    verts, idx = [], []
    for i, (a, b) in enumerate(pairs):
        verts += [a, b]; idx += [i*2, i*2+1]
    return Mesh(vertices=verts, triangles=idx, mode='line', thickness=1)


def build_grid():
    maj, mn = [], []
    for i in range(-100, 101, 10):
        target = maj if i % 50 == 0 else mn
        target += [(Vec3(i,0,-100), Vec3(i,0,100)),
                   (Vec3(-100,0,i), Vec3(100,0,i))]
    Entity(model=_line_mesh(maj), color=color.rgba(0,180,210,110), y=0.02, unlit=True)
    Entity(model=_line_mesh(mn),  color=color.rgba(0,80,100,55),   y=0.01, unlit=True)


def build_landing_pad(size=3):
    th = 0.10
    for (px, pz, sx, sz) in [
        (0, -size, size*2+th, th), (0,  size, size*2+th, th),
        (-size, 0, th, size*2),    (size, 0,  th, size*2),
    ]:
        Entity(model='cube', color=C_ORANGE,
               position=(px, 0.04, pz), scale=(sx, th, sz), unlit=True)
    Entity(model='plane', scale=size*2, color=color.hex("#08080f"), y=0.02, unlit=True)


def build_buildings():
    defs = [(50,30,5,18,5),(55,18,3,10,3),(-45,40,6,22,6),(-50,22,4,14,4),
            (60,-25,7,28,7),(-55,-30,5,16,5),(40,-50,6,20,6),(-30,-45,4,12,4)]
    for bx,bz,sw,sh,sd in defs:
        x0,x1=bx-sw/2,bx+sw/2; z0,z1=bz-sd/2,bz+sd/2
        c=[Vec3(x0,0,z0),Vec3(x1,0,z0),Vec3(x1,0,z1),Vec3(x0,0,z1),
           Vec3(x0,sh,z0),Vec3(x1,sh,z0),Vec3(x1,sh,z1),Vec3(x0,sh,z1)]
        pairs = [(c[a],c[b]) for a,b in [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),
                                          (6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]]
        Entity(model=_line_mesh(pairs), color=color.rgba(0,70,90,120), unlit=True)


# ══════════════════════════════════════════════════════════════════════
# DRONE
# ══════════════════════════════════════════════════════════════════════

class Drone(Entity):
    ARM=1.2; ROT_R=0.5
    def __init__(self):
        super().__init__(position=(0,0.1,0))
        Entity(parent=self, model='cube', color=color.hex("#1e78dc"), scale=(0.7,0.08,0.9))
        Entity(parent=self, model='sphere', color=color.rgba(0,220,255,150),
               scale=(0.44,0.28,0.52), y=0.14, unlit=True)
        self.rotors=[]
        for ax,az,rc in [(self.ARM,self.ARM,color.hex("#28ff78")),(-self.ARM,self.ARM,color.hex("#28ff78")),
                          (self.ARM,-self.ARM,color.hex("#ff3c3c")),(-self.ARM,-self.ARM,color.hex("#ff3c3c"))]:
            L=math.sqrt(ax*ax+az*az)
            Entity(parent=self, model='cube', color=color.hex("#143c64"),
                   scale=(0.16,0.06,L), position=(ax/2,0,az/2),
                   rotation_y=math.degrees(math.atan2(ax,az)))
            Entity(parent=self, model='cylinder', color=color.hex("#10101e"),
                   scale=(0.22,0.12,0.22), position=(ax,0.05,az))
            rot=Entity(parent=self, model='cylinder',
                       color=Color(rc.r,rc.g,rc.b,0.35),
                       scale=(self.ROT_R*2,0.02,self.ROT_R*2), position=(ax,0.10,az), unlit=True)
            Entity(parent=rot, model='cube', color=rc, scale=(1.6,0.05,0.08))
            Entity(parent=rot, model='cube', color=rc, scale=(0.08,0.05,1.6))
            self.rotors.append(rot)
        for sx in (0.55,-0.55):
            Entity(parent=self,model='cube',color=C_GREY,scale=(0.06,0.06,1.6),position=(sx,-0.22,0))
            for fz in (0.7,-0.7):
                Entity(parent=self,model='cube',color=C_GREY,scale=(0.06,0.28,0.06),position=(sx,-0.11,fz))
        Entity(parent=self,model='sphere',color=color.hex("#28283c"),scale=0.14,position=(0,-0.05,0.60))
        Entity(parent=self,model='sphere',color=C_RED,scale=0.07,position=(0,-0.05,0.65))
        Entity(parent=self,model='sphere',color=C_GREEN,scale=0.06,position=(0,0.05,0.55))
        Entity(parent=self,model='sphere',color=C_RED,scale=0.06,position=(0,0.05,-0.55))
        self.vx=self.vy=self.vz=self.target_pitch=self.target_roll=0.
        self.yaw_angle=0.; self.DRAG=0.82; self.THRUST=7.
        self.MOVE_SPEED=9.; self.YAW_RATE=80.
        self.flying=False; self.armed=False; self.mode="IDLE"; self._ra=0.

    def update(self):
        if not self.flying: return
        self._ra+=360*time.dt*10
        for r in self.rotors: r.rotation_y=self._ra


# ══════════════════════════════════════════════════════════════════════
# FLIGHT TRAIL
# ══════════════════════════════════════════════════════════════════════
class FlightTrail:
    def __init__(self):
        self._pos=deque(maxlen=50); self._dots=[]
    def add(self,p): self._pos.appendleft(Vec3(p))
    def refresh(self):
        for e in self._dots: destroy(e)
        self._dots.clear()
        n=len(self._pos)
        for i,p in enumerate(self._pos):
            f=1.-i/max(1,n)
            e=Entity(model='sphere',unlit=True,position=p,scale=max(0.03,0.10*f),
                     color=Color(0,f*0.78,min(1.,f*0.33+0.7),f*0.78))
            self._dots.append(e)


# ══════════════════════════════════════════════════════════════════════
# HUD  — minimal, demo-ready
# Uses window.aspect_ratio so panels stay on-screen at any resolution.
# ══════════════════════════════════════════════════════════════════════

class HUD:
    BANDS=[
        ("C3 μ","c3_mu",  "← LEFT",   color.hex("#00dcff"), 2),
        ("C4 μ","c4_mu",  "→ RIGHT",  color.azure,          3),
        ("C3 β","c3_beta","↑ FWD",    color.hex("#a03cff"), 0),
        ("C4 β","c4_beta","■ HOVER",  color.lime,           4),
    ]

    def __init__(self):
        AR = window.aspect_ratio          # e.g. 1.6 or 1.78
        HALF = AR * 0.5                   # right edge of camera.ui x-axis

        # ── layout constants ──────────────────────────────────────
        MARGIN  = 0.02                    # gap from screen edge
        LW, LH  = 0.22, 0.44             # left panel size
        RW, RH  = 0.30, 0.80             # right panel size

        self._LCX = -HALF + MARGIN + LW/2    # left panel centre-x
        self._LCY =  0.5 - MARGIN - LH/2    # left panel centre-y
        self._RCX =  HALF - MARGIN - RW/2   # right panel centre-x
        self._RCY =  0.5 - MARGIN - RH/2    # right panel centre-y

        LCX,LCY = self._LCX, self._LCY
        RCX,RCY = self._RCX, self._RCY
        LL = LCX - LW/2   # left panel left edge
        RL = RCX - RW/2   # right panel left edge

        # ── helpers ───────────────────────────────────────────────
        def bg(cx,cy,w,h,z=0.0):
            return Entity(parent=camera.ui,model='quad',color=C_PANEL,
                          position=(cx,cy),scale=(w,h),z=z)
        def border(cx,cy,w,h,col,t=0.0025):
            for pos,sc in [((cx,cy+h/2),(w,t)),((cx,cy-h/2),(w,t)),
                            ((cx-w/2,cy),(t,h)),((cx+w/2,cy),(t,h))]:
                Entity(parent=camera.ui,model='quad',color=col,position=pos,scale=sc,z=-0.01)
        def lbl(text,x,y,col=C_GREY,sc=0.44):
            return Text(text=text,parent=camera.ui,position=(x,y),
                        color=col,scale=sc,origin=(-0.5,0),z=-0.02)
        def val_t(text,x,y,col=C_CYAN,sc=0.44):
            return Text(text=text,parent=camera.ui,position=(x,y),
                        color=col,scale=sc,origin=(-0.5,0),z=-0.02)
        def sep(cx,y,w,col=C_CYAN_DIM):
            Entity(parent=camera.ui,model='quad',color=col,
                   position=(cx,y),scale=(w-0.02,0.002),z=-0.01)

        # ══ LEFT PANEL — flight data ══════════════════════════════
        bg(LCX,LCY,LW,LH)
        border(LCX,LCY,LW,LH,C_CYAN)
        lbl("◈ FLIGHT DATA", LL+0.012, LCY+LH/2-0.030, C_CYAN, 0.46)
        sep(LCX, LCY+LH/2-0.058, LW)

        # 5 data rows — label in left col, value in right col
        RROWS = [("MODE","IDLE",C_GREY),("ALT","0.0 m",C_CYAN),
                 ("YAW","0°",C_CYAN),("X","0.0",C_CYAN),("Z","0.0",C_CYAN)]
        self._row_vals={}
        COL_VAL = LL + LW*0.48    # x-start of value column
        for i,(k,v,vc) in enumerate(RROWS):
            ry = LCY + LH/2 - 0.090 - i*0.076
            lbl(k, LL+0.012, ry, C_GREY, 0.40)
            vt = val_t(v, COL_VAL, ry, vc, 0.42)
            self._row_vals[k] = vt

        # mini altitude bar on right edge
        BAR_X = LCX+LW/2-0.022
        self._alt_bh = LH-0.12
        Entity(parent=camera.ui,model='quad',color=C_PANEL_BAR,
               position=(BAR_X,LCY),scale=(0.015,self._alt_bh),z=-0.01)
        self._alt_fill=Entity(parent=camera.ui,model='quad',color=C_CYAN,
               position=(BAR_X,LCY-self._alt_bh/2+0.001),scale=(0.013,0.001),z=-0.015)
        self._alt_bcy=LCY; self._alt_bbx=BAR_X

        # ══ RIGHT PANEL — neural input ════════════════════════════
        bg(RCX,RCY,RW,RH)
        border(RCX,RCY,RW,RH,C_PURPLE)
        lbl("◈ NEURAL INPUT", RL+0.012, RCY+RH/2-0.030, C_PURPLE, 0.46)
        sep(RCX, RCY+RH/2-0.058, RW, C_PURPLE)

        # Intent + confidence
        self.intent_text = Text(text="→ IDLE", parent=camera.ui,
            position=(RCX,RCY+RH/2-0.090), color=C_GREEN,
            scale=0.70, origin=(0,0), z=-0.02)
        lbl("CONF", RL+0.012, RCY+RH/2-0.145, C_GREY, 0.40)
        self.conf_pct=val_t("0%", RL+0.085, RCY+RH/2-0.145, C_GREEN, 0.40)
        BW=RW-0.030
        self._conf_bw=BW; self._conf_bcx=RCX
        Entity(parent=camera.ui,model='quad',color=C_PANEL_BAR,
               position=(RCX,RCY+RH/2-0.175),scale=(BW,0.020),z=-0.01)
        self._conf_fill=Entity(parent=camera.ui,model='quad',color=C_GREEN,
               position=(RCX-BW/2+0.001,RCY+RH/2-0.175),scale=(0.001,0.018),z=-0.015)

        sep(RCX, RCY+RH/2-0.205, RW, C_GREY)

        # Band rows (4 clickable bars)
        self._bfills=[]
        self._bhighs=[]
        self._bcoords=[]  # (xl,xr,yb,yt) for click detection
        BRY_START = RCY+RH/2-0.235
        ROW_H = 0.130
        for i,(blbl,bkey,bhint,bcol,bid) in enumerate(self.BANDS):
            by = BRY_START - i*ROW_H
            xl,xr = RL,RL+RW
            # highlight quad
            hi=Entity(parent=camera.ui,model='quad',
                      color=color.rgba(60,40,80,160),
                      position=(RCX,by+0.012),scale=(RW-0.006,0.095),
                      visible=False,z=0.005)
            self._bhighs.append(hi)
            # label + hint
            lbl(blbl, RL+0.012, by+0.062, bcol, 0.40)
            lbl(bhint, RL+0.090, by+0.062, bcol, 0.40)
            # bar bg + fill
            Entity(parent=camera.ui,model='quad',color=C_PANEL_BAR,
                   position=(RCX,by+0.008),scale=(BW,0.020),z=-0.01)
            fill=Entity(parent=camera.ui,model='quad',color=bcol,
                        position=(RCX-BW/2+0.001,by+0.008),scale=(0.001,0.018),z=-0.015)
            self._bfills.append(fill)
            self._bcoords.append((xl,xr,by-0.020,by+0.080))

        sep(RCX, BRY_START - len(self.BANDS)*ROW_H + 0.050, RW, C_GREY)

        # Mode indicator (bottom of right panel)
        self.mode_row=val_t("MODE: IDLE", RL+0.012, RCY-RH/2+0.035, C_GREY, 0.42)

        # ══ Mode banner (top centre) ══════════════════════════════
        self.mode_banner=Text(text="[ IDLE ]",origin=(0,0),
            position=(0,0.44),color=C_GREY,scale=1.8,parent=camera.ui,z=-0.02)

        # ══ Compass (bottom centre, small) ════════════════════════
        self._build_compass()

        # ══ Controls bar (bottom, one-liner) ══════════════════════
        ctrl_y = -0.475
        Entity(parent=camera.ui,model='quad',color=color.hex("#060a14"),
               position=(0,ctrl_y),scale=(AR,0.040),z=0.0)
        Entity(parent=camera.ui,model='quad',color=C_ORANGE,
               position=(0,ctrl_y+0.020),scale=(AR,0.002),z=-0.01)
        Text(text="T=Takeoff  L=Land  SPACE=Hover  B=BCI  C=Camera  ESC=Quit"
                  "   |   W/S=Throttle  A/D=Yaw  Arrows=Pitch/Roll",
             origin=(0,0),position=(0,ctrl_y),color=C_ORANGE,
             scale=0.40,parent=camera.ui,z=-0.02)

        self._manual_intent=-1

    def _build_compass(self):
        cx,cy,r=0.,-0.390,0.045
        Entity(parent=camera.ui,model='circle',color=color.hex("#0a0e1c"),
               position=(cx,cy),scale=r*2.0,z=0.0)
        Entity(parent=camera.ui,model='circle',color=C_CYAN_DIM,
               position=(cx,cy),scale=r*2.05,z=0.005)
        for i,lb in enumerate(["N","E","S","W"]):
            a=math.radians(i*90); tx=cx+math.sin(a)*r*0.62; ty=cy+math.cos(a)*r*0.62
            Text(text=lb,parent=camera.ui,position=(tx,ty),scale=0.28,
                 color=C_YELLOW if lb=="N" else C_GREY,origin=(0,0),z=-0.02)
        self.compass_needle=Entity(parent=camera.ui,model='quad',color=C_RED,
            position=(cx,cy),scale=(0.003,r*1.0),z=-0.025)

    def update_hud(self, drone, label, conf, feat, bci_active):
        mc=C_GREEN if drone.flying else C_RED
        self._sv("MODE", drone.mode, mc)
        self._sv("ALT",  f"{drone.y:.1f} m", C_CYAN)
        self._sv("YAW",  f"{drone.yaw_angle:.0f}°", C_CYAN)
        self._sv("X",    f"{drone.x:.1f}", C_CYAN)
        self._sv("Z",    f"{drone.z:.1f}", C_CYAN)

        # altitude bar
        frac=min(1.,drone.y/20.)
        fh=max(0.001,frac*self._alt_bh)
        self._alt_fill.scale_y=fh
        self._alt_fill.y=self._alt_bcy - self._alt_bh/2 + fh/2

        # intent + conf
        ic=C_GREEN if conf>0.65 else C_ORANGE
        self.intent_text.text=f"→ {label.upper()}"; self.intent_text.color=ic
        self.conf_pct.text=f"{conf:.0%}"; self.conf_pct.color=ic
        fw=max(0.001,self._conf_bw*conf)
        self._conf_fill.scale_x=fw
        self._conf_fill.x=self._conf_bcx-self._conf_bw/2+fw/2

        # band bars
        vals=[feat.get(k,0) for(_,k,_,_,_) in self.BANDS]
        mv=max(vals)+1e-9
        for i,v in enumerate(vals):
            fw2=max(0.001,self._conf_bw*(v/mv))
            self._bfills[i].scale_x=fw2
            self._bfills[i].x=self._conf_bcx-self._conf_bw/2+fw2/2

        # mode banner
        BM={"FLYING":C_GREEN,"HOVER":C_YELLOW,"LANDING":C_ORANGE,"IDLE":C_GREY}
        self.mode_banner.color=BM.get(drone.mode,C_GREY)
        self.mode_banner.text=f"[ {drone.mode} ]"
        src="BCI" if bci_active else "KB"
        self.mode_row.text=f"MODE: {drone.mode}  |  {src}"
        self.mode_row.color=C_GREEN if bci_active else C_ORANGE

        # compass needle
        self.compass_needle.rotation_z=drone.yaw_angle

        # hover highlights
        mx,my=mouse.position.x,mouse.position.y
        for i,(xl,xr,yb,yt) in enumerate(self._bcoords):
            self._bhighs[i].visible=(xl<mx<xr and yb<my<yt)

    def check_click(self):
        if not mouse.left: return -1,""
        mx,my=mouse.position.x,mouse.position.y
        for i,(xl,xr,yb,yt) in enumerate(self._bcoords):
            if xl<mx<xr and yb<my<yt:
                _,_,hint,_,bid=self.BANDS[i]
                return bid,hint
        return -1,""

    def _sv(self,key,val,col):
        t=self._row_vals.get(key)
        if t: t.text=val; t.color=col


# ══════════════════════════════════════════════════════════════════════
# CAMERA
# ══════════════════════════════════════════════════════════════════════
class CamCtrl:
    PRESETS=[(22,30,-25,"FOLLOW"),(22,55,-25,"HIGH"),(30,85,0,"TOP-DOWN"),(22,20,-90,"SIDE")]
    ZOOM_MIN=6; ZOOM_MAX=80; ZOOM_SPEED=4
    def __init__(self): self._i=0; self._dist=22.
    def cycle(self):
        self._i=(self._i+1)%len(self.PRESETS)
        self._dist=float(self.PRESETS[self._i][0])   # reset dist on preset change
    def zoom(self,delta):
        self._dist=clamp(self._dist - delta*self.ZOOM_SPEED, self.ZOOM_MIN, self.ZOOM_MAX)
    def apply(self,target):
        _,el,az,_=self.PRESETS[self._i]; er,ar=math.radians(el),math.radians(az)
        d=self._dist
        camera.position=target+Vec3(d*math.cos(er)*math.sin(ar),d*math.sin(er),d*math.cos(er)*math.cos(ar))
        camera.look_at(target)


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
app=Ursina(borderless=False)
window.title="Mind Link — 3D BCI Drone Simulator"
window.exit_button.visible=False
window.fps_counter.enabled=True
window.color=C_BG
try: base.setBackgroundColor(4/255,6/255,14/255,1)
except Exception: pass

DirectionalLight(y=20,rotation=(45,30,0),shadows=False)
AmbientLight(intensity=0.22)

build_grid()
build_coord_labels = lambda: None  # skip coord labels for minimal demo
build_landing_pad()
build_buildings()
Entity(model='plane',scale=600,color=color.hex("#04060e"),y=-0.01,unlit=True)

drone    = Drone()
eeg      = EEGSource()
decoder  = BCIDecoder()
sig_map  = SignalMapping()
hud      = HUD()
trail    = FlightTrail()
cam_ctrl = CamCtrl()
cam_ctrl.apply(drone.position)

bci_active=True; _trail_t=0.0


def update():
    global bci_active,_trail_t
    dt=time.dt
    win=eeg.get_window(80)
    intent,label,conf,feat=decoder.decode(win)

    ci,chint=hud.check_click()
    if ci>=0:
        intent=ci; label=chint.strip("←→↑↓■ "); conf=1.0
        print(f"[hud] → {chint}")

    hud.update_hud(drone,label,conf,feat,bci_active)

    if held_keys['t']: drone.flying=True;drone.armed=True;drone.mode="FLYING";drone.vy=2.5
    if held_keys['l']: drone.mode="LANDING";drone.vy=-1.5
    if held_keys['space']: drone.vx=drone.vy=drone.vz=0.;drone.mode="HOVER"
    if held_keys['w']: drone.vz+=drone.MOVE_SPEED*dt
    if held_keys['s']: drone.vz-=drone.MOVE_SPEED*dt
    if held_keys['a']:
        drone.yaw_angle=(drone.yaw_angle-drone.YAW_RATE*dt)%360; drone.rotation_y=drone.yaw_angle
    if held_keys['d']:
        drone.yaw_angle=(drone.yaw_angle+drone.YAW_RATE*dt)%360; drone.rotation_y=drone.yaw_angle
    if held_keys['up arrow']:    drone.target_pitch=lerp(drone.target_pitch,-18,dt*6)
    elif held_keys['down arrow']:drone.target_pitch=lerp(drone.target_pitch, 18,dt*6)
    else:                        drone.target_pitch=lerp(drone.target_pitch,  0,dt*6)
    if held_keys['left arrow']:  drone.target_roll =lerp(drone.target_roll,  18,dt*6)
    elif held_keys['right arrow']:drone.target_roll=lerp(drone.target_roll, -18,dt*6)
    else:                        drone.target_roll =lerp(drone.target_roll,   0,dt*6)

    if drone.flying and bci_active and conf>0.45:
        p,r,y,t=sig_map.get_command(intent); yr=math.radians(drone.yaw_angle)
        drone.vx+=(p*math.sin(yr)+r*math.cos(yr))*drone.MOVE_SPEED*dt
        drone.vz+=(p*math.cos(yr)-r*math.sin(yr))*drone.MOVE_SPEED*dt
        if   t>0: drone.vy+=t*drone.THRUST*dt
        elif t<0: drone.vy+=(t*drone.THRUST-3.)*dt
        else:     drone.vy*=0.5

    if drone.flying:
        drone.rotation_x=lerp(drone.rotation_x,drone.target_pitch,dt*4)
        drone.rotation_z=lerp(drone.rotation_z,drone.target_roll,dt*4)
        drone.x=clamp(drone.x+drone.vx*dt,-90,90)
        drone.z=clamp(drone.z+drone.vz*dt,-90,90)
        drone.y=max(0.,drone.y+drone.vy*dt)
        drone.vx*=drone.DRAG;drone.vy*=drone.DRAG;drone.vz*=drone.DRAG
        if drone.y<=0.:
            drone.vy=0.
            if drone.mode=="LANDING": drone.flying=False;drone.armed=False;drone.mode="IDLE"

    _trail_t+=dt
    if drone.flying and _trail_t>0.06:
        trail.add(drone.position);trail.refresh();_trail_t=0.

    cam_ctrl.apply(drone.position)


def input(key):
    global bci_active
    if key=='escape': quit()
    if key=='c': cam_ctrl.cycle()
    if key=='b': bci_active=not bci_active; print(f"[bci] {'ON' if bci_active else 'OFF'}")
    if key=='scroll up':   cam_ctrl.zoom( 1)   # zoom in
    if key=='scroll down': cam_ctrl.zoom(-1)   # zoom out
    if key in ('+','='): cam_ctrl.zoom( 2)     # + key
    if key=='-':         cam_ctrl.zoom(-2)     # - key


app.run()
