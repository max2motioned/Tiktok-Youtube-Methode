"""Folge 02 – Szenen "How popcorn pops". Gemeinsame Bausteine kommen aus project/engine.py."""
import math

import numpy as np

from engine import *  # noqa: F401,F403

# ---------------------------------------------------------------- Farben (Folge 02)
HULL = (238, 168, 46)
HULL_D = (178, 104, 20)
HULL_L = (255, 214, 120)
HOT = (255, 108, 52)
TIP = (246, 228, 186)
STARCH = (250, 240, 214)
STARCH_DOT = (236, 222, 188)
GEL = (255, 238, 178)
WATER = (84, 168, 255)
STEAM = (236, 244, 252)
POP = (253, 249, 238)
POP_SH = (226, 212, 180)
STOVE_T = (22, 20, 26)
STOVE_B = (70, 38, 26)
PAN = (58, 58, 66)
PAN_HI = (110, 112, 124)
FLAME_O = (255, 122, 34)
FLAME_Y = (255, 214, 90)


@lru_cache(maxsize=None)
def bg_stove():
    return vgrad(W2, H2, STOVE_T, STOVE_B)


# ---------------------------------------------------------------- Formen
def kwidth(a):
    v = (1 - math.cos(a)) / 2
    s = math.sin(a)
    return math.copysign(abs(s) ** 0.7, s) * (1 - 0.62 * v ** 1.6)


def kshape(v):
    """Halbe Breite (0..1) des Korns auf Höhe v (0 = Krone oben, 1 = Spitze unten)."""
    v = clamp(v)
    c = 1 - 2 * v
    # Umkehrung der y-Verformung aus kpts (Krone flach)
    c = c ** (1 / 0.55) if c > 0 else c
    return abs(kwidth(math.acos(max(-1, min(1, c)))))


def kpts(cx, cy, w, h, rot=0.0, n=60):
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        v = (1 - math.cos(a)) / 2
        x = kwidth(a) * w / 2
        c = math.cos(a)
        y = -(abs(c) ** 0.55 if c > 0 else -abs(c)) * h / 2      # flache, breite Krone oben
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def rot_pt(cx, cy, x, y, rot):
    ca, sa = math.cos(rot), math.sin(rot)
    return cx + x * ca - y * sa, cy + x * sa + y * ca


def kernel(cv, cx, cy, w, h, rot=0.0, heat=0.0, crack=0.0, crack_seed=0):
    body = mix(HULL, HOT, heat * 0.7)
    cv.poly(kpts(cx, cy, w + 10, h + 10, rot), fill=mix(HULL_D, (150, 50, 20), heat))
    cv.poly(kpts(cx, cy, w, h, rot), fill=body)
    # Glanz
    hx, hy = rot_pt(cx, cy, -w * 0.18, -h * 0.2, rot)
    cv.ellipse(hx, hy, w * 0.12, h * 0.16, fill=mix(body, HULL_L, 0.8))
    # Spitze
    tx, ty = rot_pt(cx, cy, 0, h * 0.43, rot)
    cv.ellipse(tx, ty, w * 0.1, h * 0.06, fill=mix(TIP, HOT, heat * 0.4))
    if crack > 0:
        rng = np.random.default_rng(crack_seed)
        for k in range(3):
            pts = [rot_pt(cx, cy, (k - 1) * w * 0.18, -h * 0.42, rot)]
            x, y = (k - 1) * w * 0.18, -h * 0.42
            steps = int(1 + 6 * crack)
            for _ in range(steps):
                x += rng.uniform(-0.09, 0.09) * w
                y += 0.11 * h
                pts.append(rot_pt(cx, cy, x, y, rot))
            cv.line(pts, (60, 24, 10), max(2, w * 0.022))


@lru_cache(maxsize=None)
def drop_layout(n=16, seed=4):
    r = np.random.default_rng(seed)
    return [(float(r.uniform(0.18, 0.86)), float(r.uniform(-0.7, 0.7)), float(r.uniform(0.6, 1.0))) for _ in range(n)]


@lru_cache(maxsize=None)
def starch_dots(n=40, seed=9):
    r = np.random.default_rng(seed)
    return [(float(r.uniform(0.1, 0.92)), float(r.uniform(-0.85, 0.85)), float(r.uniform(3, 7))) for _ in range(n)]


def inside_xy(cx, cy, w, h, v, u):
    """Punkt im Korn-Inneren: v (0..1 oben->unten), u (-1..1 links->rechts)."""
    return cx + u * kshape(v) * w / 2, cy - h / 2 + v * h


def cutaway(cv, cx, cy, w, h, t, heat=0.0, gel=0.0, water=1.0, steam=0.0, steam_t0=0.0, shell_glow=0.0,
            tremble=0.0):
    cx += math.sin(t * 47) * tremble * 3
    shell = mix(HULL, HOT, heat * 0.6)
    if shell_glow > 0:
        cv.poly(kpts(cx, cy, w + 40, h + 40), fill=mix(NAVY, AMBER, shell_glow * 0.5))
    cv.poly(kpts(cx, cy, w + 10, h + 10), fill=mix(HULL_D, (150, 50, 20), heat))
    cv.poly(kpts(cx, cy, w, h), fill=shell)
    iw, ih, icy = w * 0.80, h * 0.84, cy + h * 0.02
    st = mix(STARCH, GEL, gel)
    cv.poly(kpts(cx, icy, iw, ih), fill=st)
    for v, u, r in starch_dots():
        x, y = inside_xy(cx, icy, iw, ih, v, u * 0.9)
        cv.circle(x, y, r * w / 440, fill=mix(STARCH_DOT, mix(GEL, WHITE, 0.4), gel))
    if gel > 0:
        cv.line([inside_xy(cx, icy, iw, ih, 0.2, -0.5), inside_xy(cx, icy, iw, ih, 0.45, -0.62)],
                mix(st, WHITE, 0.7 * gel), 8 * w / 440)
    # Wassertropfen / Dampf
    drops = drop_layout()
    for i, (v, u, r) in enumerate(drops):
        k = clamp((steam * len(drops) - i) / 1.0) if steam > 0 else 0.0
        jit_v = v + 0.012 * math.sin(t * 2.0 + i)
        jit_u = u + 0.03 * math.cos(t * 1.7 + i * 2)
        if k < 1 and water > 0:
            x, y = inside_xy(cx, icy, iw, ih, jit_v, jit_u)
            rr = (11 + 7 * r) * w / 440 * (1 - k)
            if rr > 0.5:
                cv.circle(x, y, rr, fill=mix(st, WATER, water))
                cv.circle(x - rr * 0.3, y - rr * 0.3, rr * 0.3, fill=mix(st, (200, 228, 255), water))
        if k > 0:
            # schneller Dampf, prallt im Inneren hin und her
            sv = 0.12 + 0.76 * tri(v + (t - steam_t0) * (1.2 + r))
            su = 0.85 * (2 * tri(u + 1 + (t - steam_t0) * (1.6 + r * 1.3)) - 1)
            x, y = inside_xy(cx, icy, iw, ih, sv, su)
            rr = (12 + 6 * r) * w / 440
            cv.circle(x, y, rr + 3 * w / 440, fill=mix(st, (120, 160, 210), k))
            cv.circle(x, y, rr, fill=mix(st, WHITE, k))
    return icy, iw, ih


def flame(cv, cx, base, width, t, a=1.0, bg=NAVY):
    if a <= 0:
        return
    n = 5
    for layer, (col, sc) in enumerate(((FLAME_O, 1.0), (FLAME_Y, 0.6))):
        c = mix(bg, col, a)
        for i in range(n):
            fx = cx + (i - (n - 1) / 2) * width / n
            hgt = width * 0.55 * sc * (0.8 + 0.2 * math.sin(t * 13 + i * 1.7)) * (1 - 0.25 * abs(i - 2) / 2)
            wd = width / n * 0.62 * sc
            sway = math.sin(t * 9 + i) * wd * 0.25
            pts = [(fx - wd, base)]
            for k in np.linspace(0, 1, 8):
                pts.append((fx - wd * (1 - k) ** 0.8 + sway * k, base - hgt * k))
            for k in np.linspace(1, 0, 8):
                pts.append((fx + wd * (1 - k) ** 0.8 + sway * k, base - hgt * k))
            cv.poly(pts, fill=c)


def gauge(cv, x, y, r, value, label_txt="", danger=0.7):
    """Manometer: value 0..1."""
    cv.circle(x, y, r + 10, fill=(70, 80, 100))
    cv.circle(x, y, r, fill=(240, 242, 246))
    for i in range(11):
        ang = math.radians(225 - 270 * i / 10)
        r0 = r * (0.78 if i % 5 else 0.70)
        col = CORAL if i / 10 >= danger else (60, 70, 90)
        cv.line([(x + math.cos(ang) * r0, y - math.sin(ang) * r0),
                 (x + math.cos(ang) * r * 0.9, y - math.sin(ang) * r * 0.9)], col, 4 if i % 5 else 6, caps=False)
    ang = math.radians(225 - 270 * clamp(value))
    cv.line([(x, y), (x + math.cos(ang) * r * 0.72, y - math.sin(ang) * r * 0.72)], CORAL, 8)
    cv.circle(x, y, 12, fill=(40, 48, 64))
    if label_txt:
        cv.put(txt(label_txt, 30, (40, 48, 64), "black"), x, y + r * 0.45)


def thermo(cv, x, y0, y1, frac, a=1.0):
    cv.rrect(x - 26, y0 - 26, x + 26, y1, 26, fill=mix(NAVY, (230, 236, 244), a))
    cv.circle(x, y1 + 20, 44, fill=mix(NAVY, (230, 236, 244), a))
    cv.circle(x, y1 + 20, 32, fill=mix(NAVY, CORAL, a))
    top = lerp(y1, y0 + 10, clamp(frac))
    cv.rrect(x - 13, top, x + 13, y1 + 10, 13, fill=mix(NAVY, CORAL, a))
    for i in range(6):
        yy = lerp(y1 - 20, y0 + 20, i / 5)
        cv.line([(x + 30, yy), (x + 46, yy)], mix(NAVY, SOFT, a), 4, caps=False)


@lru_cache(maxsize=None)
def puff_layout(seed=2):
    r = np.random.default_rng(seed)
    blobs = [(0.0, 0.0, 1.0)]
    for i in range(10):
        ang = 2 * math.pi * i / 10 + r.uniform(-0.25, 0.25)
        d = r.uniform(0.6, 1.0)
        blobs.append((math.cos(ang) * d, math.sin(ang) * d * 0.85, r.uniform(0.5, 0.78)))
    return blobs


def popcorn(cv, cx, cy, s, k=1.0, gloss=0.0, seed=2, flakes=True):
    """Popcorn-Wolke; s = Radius bei k=1."""
    if k <= 0:
        return
    col = mix(POP, GEL, gloss)
    sh = mix(POP_SH, (230, 196, 110), gloss)
    for dx, dy, r in puff_layout(seed):
        cv.circle(cx + dx * s * k ** 0.85, cy + dy * s * k ** 0.85 + s * 0.08 * k, r * s * 0.62 * k, fill=sh)
    for dx, dy, r in puff_layout(seed):
        cv.circle(cx + dx * s * k ** 0.85, cy + dy * s * k ** 0.85, r * s * 0.58 * k, fill=col)
        cv.circle(cx + dx * s * k ** 0.85 - r * s * 0.18 * k, cy + dy * s * k ** 0.85 - r * s * 0.2 * k,
                  r * s * 0.16 * k, fill=mix(col, WHITE, 0.7))
    if flakes:
        for i, dx in enumerate((-0.32, 0.18)):
            fx, fy = cx + dx * s * k, cy + s * 0.72 * k
            q = 26 * k * s / 200
            cv.poly([(fx - q, fy - q * 0.3), (fx + q, fy - q * 0.5), (fx + q * 0.2, fy + q * 0.9)], fill=HULL)


def pan_surface(cv, y):
    cv.rrect(-200, y, 1280, y + 90, 20, fill=PAN)
    cv.rrect(-200, y, 1280, y + 10, 5, fill=PAN_HI)


PAN_Y = 1180
MAIN = (540, 1080, 150, 200)                       # Haupt-Korn (Hook/Loop)
OTHERS = [(150, 1120, 112, 150, -0.5), (330, 1112, 124, 164, 0.35), (760, 1115, 120, 160, -0.3),
          (930, 1122, 108, 146, 0.55)]


def pan_scene(cv, t, z, fx, fy, ty, tremble=0.0, glow=0.0):
    cv.img.paste(bg_stove())
    cv.cam(z, fx, fy, 540, ty)
    # Hitze-Schimmer unter der Pfanne
    for i in range(3):
        cv.ellipse(540, PAN_Y + 160, 700 - i * 160, 120 - i * 30, fill=mix(STOVE_B, (150, 60, 30), 0.25 + i * 0.2 + glow * 0.2))
    pan_surface(cv, PAN_Y)
    for i, (x, y, w, h, r) in enumerate(OTHERS):
        jig = math.sin(t * (31 + i * 7) + i) * 1.5 * tremble
        kernel(cv, x + jig, y, w, h, r)
    x, y, w, h = MAIN
    kernel(cv, x + math.sin(t * 43) * 2.0 * tremble, y, w, h, 0.0, heat=0.15 * tremble)
    cv.reset()


# ================================================================ SZENEN
def sc_hook(cv, t, C, s0, s1):
    T = C.T
    x, y, w, h = MAIN
    punch = 1 + 0.22 * (1 - out_cubic(ramp(t, 0, 0.45)))
    back = smooth(ramp(t, T["hook2"] - 0.05, 1.0))
    push = smooth(ramp(t, T["hook3"] + 1.2, max(0.5, s1 - T["hook3"] - 1.2)))
    z = lerp(3.0 * punch, 1.1, back) * (1 + 0.5 * push)
    fy = lerp(y - 20, 1000, back)
    fy = lerp(fy, y - 20, push * 0.6)
    ty = lerp(800, 860, back)
    if t < 0:  # Loop-Übergang am Videoende: Pfanne -> Nahaufnahme, endet genau auf Bild 1
        zin = smooth(ramp(t, -LOOP_ZOOM, LOOP_ZOOM)) ** 1.6
        z, fy, ty = lerp(1.1, 3.0 * punch, zin), lerp(1000, y - 20, zin), lerp(860, 800, zin)
    tremble = 1.0 + 2.5 * ramp(t, T["hook3"], 1.4)
    pan_scene(cv, t, z, 540, fy, ty, tremble)
    # Countdown-Ring 3-2-1
    if t > T["hook3"] - 0.1:
        cv.cam(z, 540, fy, 540, ty)
        k = ramp(t, T["hook3"], 1.35)
        X, Y = cv.P(x, y)
        R = cv.L(150)
        cv.d.arc([X - R, Y - R, X + R, Y + R], -90 + 360 * k, 270, fill=AMBER, width=int(cv.L(10)))
        cv.reset()
        for i, num in enumerate("321"):
            ti = T["hook3"] + 0.45 * i
            a = ramp(t, ti, 0.08) * (1 - ramp(t, ti + 0.4, 0.08)) if i < 2 else ramp(t, ti, 0.08)
            if a > 0:
                cv.put(txt(num, 150, AMBER, "black"), 540, 520, a, out_back(ramp(t, ti, 0.25)))
    headline(cv, "A TINY PRESSURE COOKER", t, -0.35, T["hook2"] - 0.05, y=400, size=60)


def sc_assume(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    cx, cy, w, h = 540, 800, 230, 300
    sp = smooth(ramp(t, T["ass3"] + 0.05, 0.6))
    flame(cv, 540, 1180, 300, t, smooth(ramp(t, s0, 0.4)) * (1 - sp * 0.6))
    wob = math.sin(t * 30) * 4 * ramp(t, T["ass2"], 0.2) * (1 - sp)
    if sp < 1:
        # Korn teilt sich in zwei Hälften
        pts = kpts(cx, cy, w, h)
        n = len(pts)
        right = [p for p in pts[:n // 2 + 1]]
        left = [pts[0]] + pts[n // 2:]
        a = 1 - sp
        if sp > 0:
            cutaway(cv, cx, cy, w * lerp(0.9, 1.25, sp), h * lerp(0.9, 1.25, sp), t)
        cv.poly([(px - 180 * sp + wob, py) for px, py in left], fill=mix(NAVY, HULL, a))
        cv.poly([(px + 180 * sp + wob, py) for px, py in right], fill=mix(NAVY, mix(HULL, HULL_D, 0.25), a))
        if sp == 0:
            kernel(cv, cx + wob, cy, w, h)
    else:
        cutaway(cv, cx, cy, w * 1.25, h * 1.25, t)
    q = ramp(t, T["ass2"] + 0.25, 0.15) * (1 - ramp(t, T["ass3"], 0.2))
    if q > 0:
        cv.put(txt("?", 160, AMBER, "black"), 800, 640, q, out_back(ramp(t, T["ass2"] + 0.25, 0.3)))
    headline(cv, "HEAT = BURST?", t, T["ass1"] + 0.2, T["ass3"] + 0.05, y=400)
    headline(cv, "THE TRICK IS INSIDE", t, T["ass3"] + 0.1, s1 + 1, y=400, fg=AMBER)


def sc_anatomy(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    cx, cy, w, h = 540, 860, 420, 560
    water = ramp(t, T["an1"] + 0.2, 0.5)
    glow = ramp(t, T["an4"] + 0.1, 0.3) * (0.6 + 0.4 * math.sin(t * 6))
    cutaway(cv, cx, cy, w, h, t, water=water, shell_glow=glow * (1 - ramp(t, s1 - 0.4, 0.3)))
    # Abprallen an der Schale
    if t > T["an5"]:
        for k, (v, side) in enumerate(((0.35, 1), (0.6, -1), (0.48, 1))):
            ph = ((t - T["an5"]) * 1.4 + k / 3) % 1
            x, y = inside_xy(cx, cy + h * 0.02, w * 0.8, h * 0.84, v, side * 0.97)
            cv.circle(x, y, 10 + 30 * ph, outline=mix(STARCH, WATER, 1 - ph), w=4)
    # 14-%-Kreis
    pk = out_back(ramp(t, T["an2"], 0.35))
    if pk > 0:
        px, py, r = 190, 640, 80 * pk
        cv.circle(px, py, r, fill=STARCH)
        X, Y = cv.P(px, py)
        R = cv.L(r)
        cv.d.pieslice([X - R, Y - R, X + R, Y + R], -90, -90 + 360 * 0.14 * ramp(t, T["an2"] + 0.15, 0.4), fill=WATER)
        cv.put(txt("14 %", 40, WATER, "black"), px, py + 120, pk)
    label(cv, "WATER", 190, 470, t, T["an1"] + 0.3, WATER, 42)
    label(cv, "SOFT STARCH", 205, 1065, t, T["an3"], STARCH, 38)
    if t > T["an3"]:
        k = out_cubic(ramp(t, T["an3"] + 0.1, 0.3))
        cv.line([(330, 1040), (330 + 90 * k, 1000 - 20 * k)], mix(NAVY, STARCH, k), 5)
    label(cv, "HARD SHELL", 860, 610, t, T["an4"], HULL_L, 38)
    if t > T["an4"]:
        k = out_cubic(ramp(t, T["an4"] + 0.1, 0.3))
        cv.line([(800, 640), (800 - 50 * k, 680 + 20 * k)], mix(NAVY, HULL_L, k), 5)
    label(cv, "barely lets anything out", 540, 1210, t, T["an5"], SOFT, 32, "semi")
    headline(cv, "≈ 14 % WATER", t, T["an2"], s1 + 1, y=400, fg=WATER, size=60)


def sc_pressure(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    cx, cy, w, h = 460, 820, 380, 500
    fl = smooth(ramp(t, T["pr1"] - 0.1, 0.4))
    heat = ramp(t, T["pr1"], 3.0)
    steam = ramp(t, T["pr2"] + 0.1, 1.0)
    gel = smooth(ramp(t, T["pr6"], 1.2))
    tremble = ramp(t, T["pr4"], 2.5)
    sc = 1 + 0.04 * tremble
    flame(cv, cx, 1190, 260, t, fl)
    cutaway(cv, cx, cy, w * sc, h * sc, t, heat=heat, gel=gel, steam=steam, steam_t0=T["pr2"], tremble=tremble,
            shell_glow=0.5 * ramp(t, T["pr3"], 0.3) * (1 - ramp(t, T["pr4"], 0.4)))
    gk = out_back(ramp(t, T["pr4"] - 0.2, 0.35))
    if gk > 0:
        val = smooth(ramp(t, T["pr4"], max(0.8, C.E["pr5"] - T["pr4"]))) * 0.95
        val += 0.01 * math.sin(t * 40) * tremble
        cv.cam(gk, 850, 640, 850, 640)
        gauge(cv, 850, 640, 115, val, "×10" if val > 0.9 else "")
        cv.reset()
        label(cv, "≈ 10× air pressure", 850, 800, t, T["pr5"], SOFT, 32, "semi")
    label(cv, "STEAM", 850, 960, t, T["pr2"] + 0.2, STEAM, 44)
    label(cv, "HOT GEL", 850, 1080, t, T["pr7"], GEL, 44)
    headline(cv, "TRAPPED", t, T["pr3"], T["pr4"] - 0.1, y=400, fg=AMBER)
    headline(cv, "PRESSURE RISING", t, T["pr4"] - 0.05, s1 + 1, y=400, fg=CORAL, size=60)


def sc_burst(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    temp = smooth(ramp(t, T["bu1"], max(0.8, T["bu2"] - T["bu1"])))
    crack = ramp(t, T["bu2"] - 0.05, 0.5)
    shake = 3 + 10 * crack
    cx, cy, w, h = 600, 830, 300, 400
    kernel(cv, cx + math.sin(t * 50) * shake, cy + math.cos(t * 43) * shake * 0.5, w, h, 0.0,
           heat=0.4 + 0.5 * temp, crack=crack, crack_seed=3)
    thermo(cv, 230, 560, 1060, 0.1 + 0.88 * temp)
    deg = int(round(lerp(20, 180, temp)))
    cv.put(txt(f"{deg} °C", 64, CORAL, "black"), 230, 480)
    fk = ramp(t, T["bu2"] + 0.5, 0.18)
    if fk > 0:
        cv.circle(cx, cy, 80 + 1300 * out_cubic(fk), fill=mix(NAVY, (255, 250, 236), 1 - ramp(t, T["bu2"] + 0.68, 0.3)))
    headline(cv, "180 °C", t, T["bu1"] + 0.3, T["bu2"] + 0.5, y=400, fg=CORAL, size=60)


def sc_foam(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    cx, cy = 540, 820
    grow = out_back(ramp(t, T["fo1"] - 0.1, max(0.8, T["fo4"] - T["fo1"] + 0.3)), 1.2)
    gloss = 1 - smooth(ramp(t, T["fo5"], 1.0))
    # Dampfstrahlen
    ja = ramp(t, T["fo2"] - 0.1, 0.2) * (1 - ramp(t, T["fo3"] + 0.6, 0.4))
    if ja > 0:
        for i in range(10):
            ang = 2 * math.pi * i / 10 + 0.3
            r0 = 120 + 260 * grow
            r1 = r0 + 90 + 40 * math.sin(t * 20 + i)
            cv.line([(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0),
                     (cx + math.cos(ang) * r1, cy + math.sin(ang) * r1)], mix(NAVY, STEAM, ja), 10)
    popcorn(cv, cx, cy, 300, max(0.05, grow), gloss)
    # Größenvergleich
    ck = out_back(ramp(t, T["fo4"], 0.35))
    if ck > 0:
        kernel(cv, 160, 1150, 60 * ck, 80 * ck)
        cv.put(txt("1×", 34, SOFT, "black"), 160, 1225, ck)
    if t > T["fo6"] + 0.3:
        for i in range(5):
            ph = ((t - T["fo6"] - 0.3) * 1.1 + i / 5) % 1
            ang = i * 1.3
            sx, sy = cx + math.cos(ang) * 260, cy + math.sin(ang) * 230
            sz = 22 * math.sin(math.pi * ph)
            cv.poly([(sx, sy - sz), (sx + sz * 0.3, sy), (sx, sy + sz), (sx - sz * 0.3, sy)], fill=WHITE)
            cv.poly([(sx - sz, sy), (sx, sy + sz * 0.3), (sx + sz, sy), (sx, sy - sz * 0.3)], fill=WHITE)
    headline(cv, "INSIDE OUT", t, T["fo1"], T["fo4"] - 0.05, y=400)
    headline(cv, "UP TO 40× BIGGER", t, T["fo4"], T["fo5"] + 0.1, y=400, fg=AMBER)
    headline(cv, "SETS INSTANTLY", t, T["fo5"] + 0.1, s1 + 1, y=400, fg=MINT)


def film_strip(cv, t, y0, y1, speed, a=1.0):
    cv.rrect(-20, y0, 1100, y1, 0, fill=mix(NAVY, (16, 16, 20), a))
    hole = mix(NAVY, (70, 70, 80), a)
    off = (t * speed) % 120
    for i in range(-1, 11):
        x = i * 120 - off
        cv.rrect(x + 20, y0 + 14, x + 70, y0 + 40, 6, fill=hole)
        cv.rrect(x + 20, y1 - 40, x + 70, y1 - 14, 6, fill=hole)
    fw = 230
    off2 = (t * speed) % (fw + 30)
    for i in range(-1, 6):
        x = i * (fw + 30) - off2 + 20
        cv.rrect(x, y0 + 56, x + fw, y1 - 56, 10, fill=mix(NAVY, (40, 46, 60), a))
        stage = ((i + int((t * speed) // (fw + 30))) % 5) / 4
        fx, fy = x + fw / 2, (y0 + y1) / 2
        if stage < 0.5:
            kernel(cv, fx, fy, 70, 92, crack=stage * 2, crack_seed=5)
        else:
            popcorn(cv, fx, fy, 75 * (stage - 0.25) * 1.33, 1.0, flakes=False)


def check_card(cv, x, y, text_s, ok, k):
    if k <= 0:
        return
    col = MINT if ok else CORAL
    cv.rrect(x - 230 * k, y - 62 * k, x + 230 * k, y + 62 * k, 30 * k, fill=CARD, outline=col, w=4)
    cv.circle(x - 170 * k, y, 34 * k, fill=col)
    if ok:
        cv.line([(x - 186 * k, y), (x - 174 * k, y + 14 * k), (x - 152 * k, y - 14 * k)], NAVY, 8 * k)
    else:
        cv.line([(x - 184 * k, y - 14 * k), (x - 156 * k, y + 14 * k)], NAVY, 8 * k)
        cv.line([(x - 184 * k, y + 14 * k), (x - 156 * k, y - 14 * k)], NAVY, 8 * k)
    cv.put(txt(text_s, 34, WHITE, "black"), x + 30 * k, y, 1, k)


def sc_sound(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    fa = smooth(ramp(t, T["so2"] - 0.1, 0.35))
    if fa > 0:
        film_strip(cv, t, 500, 790, 260, fa)
    pa = 1 - fa
    if pa > 0:
        popcorn(cv, 540, 820, 230, 1.0)
        k = out_back(ramp(t, T["so1"] + 0.05, 0.3))
        for i in range(3):
            ph = ((t - T["so1"]) * 1.3 + i / 3) % 1
            X, Y = cv.P(540, 820)
            R = cv.L(250 + 120 * ph)
            cv.d.arc([X - R, Y - R, X + R, Y + R], -40, 40, fill=mix(NAVY, AMBER, pa * (1 - ph)), width=int(cv.L(8)))
            cv.d.arc([X - R, Y - R, X + R, Y + R], 140, 220, fill=mix(NAVY, AMBER, pa * (1 - ph)), width=int(cv.L(8)))
        cv.put(txt("POP?", 110, AMBER, "black"), 540, 470, pa, k)
    # Dampfstrahl mit Schallwellen
    ja = ramp(t, T["so4"] - 0.1, 0.3)
    if ja > 0:
        kx, ky = 250, 1030
        kernel(cv, kx, ky, 130, 170, 0.5, heat=0.3, crack=1.0, crack_seed=8)
        for i in range(6):
            ph = (t * 2.2 + i / 6) % 1
            x0 = kx + 80 + 140 * ph
            cv.circle(x0, ky - 40 - 30 * ph + 10 * math.sin(t * 9 + i), 12 + 18 * ph, fill=mix(NAVY, STEAM, ja * (1 - ph)))
        for i in range(3):
            ph = (t * 1.4 + i / 3) % 1
            X, Y = cv.P(kx + 90, ky - 40)
            R = cv.L(60 + 140 * ph)
            cv.d.arc([X - R, Y - R, X + R, Y + R], -35, 35, fill=mix(NAVY, AMBER, ja * (1 - ph)), width=int(cv.L(7)))
    check_card(cv, 720, 960, "STEAM ESCAPING", True, out_back(ramp(t, T["so4"] + 0.75, 0.35)))
    check_card(cv, 720, 1120, "SHELL CRACKING", False, out_back(ramp(t, T["so5"] + 0.35, 0.35)))
    headline(cv, "≈ 2,900 FRAMES / SEC", t, T["so3"] - 0.1, T["so4"] + 0.2, y=400, size=56)
    headline(cv, "SO WHAT MAKES THE POP?", t, T["so4"] + 0.2, s1 + 1, y=400, fg=AMBER, size=56)


def sc_jump(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    py = 1150
    pan_surface(cv, py)
    leg = out_cubic(ramp(t, T["ju2"] + 0.1, 0.45))
    fly = ramp(t, T["ju3"] + 0.1, 1.1)
    k = smooth(fly)
    x0, y0 = 360, py - 105
    x1, y1 = 760, py - 160
    x = lerp(x0, x1, k)
    y = lerp(y0, y1, k) - 560 * 4 * k * (1 - k)
    rot = -2.6 * k
    # Flugbahn
    if fly > 0:
        for q in np.linspace(0, k, 14):
            cv.circle(lerp(x0, x1, q), lerp(y0, y1, q) - 560 * 4 * q * (1 - q), 5, fill=SOFT)
    # Stärke-"Bein"
    if leg > 0 and fly < 0.25:
        la = 1 - ramp(fly, 0.0, 0.25)
        lx, ly = x, y + 90
        cv.rrect(lx - 26, ly - 20, lx + 26, ly + 55 * leg, 22, fill=mix(NAVY, POP, la))
    kernel(cv, x, y - 40 * leg * (1 - k), 150, 200, rot, heat=0.3, crack=0.6, crack_seed=11)
    if k > 0.55:
        popcorn(cv, x, y, 130 * smooth((k - 0.55) / 0.45), 1.0)
    label(cv, "A LEG OF STARCH", 560, 1240, t, T["ju2"] + 0.1, POP, 40)
    if T["ju2"] + 0.1 < t:
        a = out_cubic(ramp(t, T["ju2"] + 0.2, 0.3)) * (1 - ramp(t, T["ju3"] + 0.1, 0.3))
        if a > 0:
            cv.arrow(470, 1220, 405, 1170, mix(NAVY, POP, a), 6, 18)
    headline(cv, "IT EVEN JUMPS", t, T["ju1"], s1 + 1, y=400, fg=AMBER)


def sc_dud(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    cx, cy, w, h = 470, 820, 300, 400
    flame(cv, cx, 1190, 240, t, smooth(ramp(t, s0, 0.4)))
    kernel(cv, cx, cy, w, h, 0.15, heat=0.35, crack=0.8, crack_seed=21)
    # Dampf entweicht
    la = ramp(t, T["du3"] - 0.2, 0.3)
    if la > 0:
        for i in range(7):
            ph = (t * 0.9 + i / 7) % 1
            sx = cx + 70 + 60 * ph + 25 * math.sin(t * 4 + i)
            sy = cy - 120 - 260 * ph
            cv.circle(sx, sy, 16 + 26 * ph, fill=mix(NAVY, (150, 160, 180), la * (1 - ph) * 0.9))
    gk = out_back(ramp(t, T["du1"] + 0.1, 0.35))
    if gk > 0:
        cv.cam(gk, 840, 640, 840, 640)
        gauge(cv, 840, 640, 100, 0.12 + 0.04 * math.sin(t * 7), "")
        cv.reset()
    nk = out_back(ramp(t, T["du4"] + 0.2, 0.35))
    if nk > 0:
        cv.circle(840, 820, 48 * nk, fill=CORAL)
        cv.line([(820, 800), (860, 840)], NAVY, 10 * nk)
        cv.line([(820, 840), (860, 800)], NAVY, 10 * nk)
    headline(cv, "NEVER POPPED?", t, T["du1"], T["du2"], y=400, fg=AMBER)
    headline(cv, "DAMAGED OR DRY SHELL", t, T["du2"], T["du4"] + 0.1, y=400, size=56)
    headline(cv, "NO PRESSURE = NO POP", t, T["du4"] + 0.1, s1 + 1, y=400, fg=CORAL, size=56)


def icon_card(cv, x, y, k, kind):
    if k <= 0:
        return
    cv.rrect(x - 120 * k, y - 120 * k, x + 120 * k, y + 120 * k, 34 * k, fill=(13, 22, 40), outline=CARD_LINE, w=3)
    if kind == "drop":
        drop_icon(cv, x, y - 4, 64 * k, WATER)
    elif kind == "shell":
        kernel(cv, x, y, 100 * k, 134 * k)
    else:
        popcorn(cv, x, y, 76 * k, 1.0, flakes=False)


def sc_outro(cv, t, C, s0, s1):
    T = C.T
    pan_scene(cv, t, 1.1, 540, 1000, 860, tremble=1.0)
    ek = smooth(ramp(t, T["end3"] - 0.15, 0.35))
    out = smooth(ramp(t, C.total - LOOP_ZOOM - 0.3, 0.3))
    d1 = T["end1"]
    d2 = lerp(T["end1"], C.E["end1"], 0.55)
    d3 = T["end2"]
    for (x, ti, kind) in ((250, d1, "drop"), (540, d2, "shell"), (830, d3, "burst")):
        k = out_back(ramp(t, ti, 0.3)) * (1 - ek)
        icon_card(cv, x, 640, k, kind)
    if ek > 0 and out < 1:
        y = lerp(1500, 700, out_cubic(ek)) - 700 * out ** 2
        bob = math.sin(max(0, t - T["end4"]) * 6) * 4 * ramp(t, T["end4"], 0.2)
        cv.put(endcard_sprite(), 540, y + bob, min(1, ek * 1.5) * (1 - out), 1 + 0.15 * out)


SCENE_FUNCS = {"hook": sc_hook, "assume": sc_assume, "anatomy": sc_anatomy, "pressure": sc_pressure,
               "burst": sc_burst, "foam": sc_foam, "sound": sc_sound, "jump": sc_jump, "dud": sc_dud,
               "outro": sc_outro}
