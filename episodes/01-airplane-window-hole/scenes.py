"""Folge 01 – Szenen (episodenspezifische Zeichnungen). Gemeinsame Bausteine kommen aus project/engine.py."""
import math

import numpy as np
from PIL import Image

from engine import *  # noqa: F401,F403

@lru_cache(maxsize=None)
def fog_base():
    rng = np.random.default_rng(3)
    small = Image.fromarray((rng.uniform(0, 255, (18, 13))).astype(np.uint8), "L")
    big = np.asarray(small.resize((260, 360), Image.BICUBIC), dtype=float) / 255
    yy, xx = np.mgrid[0:360, 0:260]
    corner = np.maximum(0, 1 - np.minimum(np.hypot(xx - 0, yy - 0), np.hypot(xx - 260, yy - 360)) / 150)
    return np.clip(0.55 + 0.35 * big + 0.4 * corner, 0, 1)


def front_window(cv, cx, cy, w, h, t, shade=0.2, fog=0.0, clear=0.0, drops=None, hole=True):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    cv.rrect(x0 - 78, y0 - 86, x1 + 78, y1 + 86, w / 2 + 78, fill=BEZEL, outline=(205, 196, 181), w=3)
    cv.rrect(x0 - 30, y0 - 32, x1 + 30, y1 + 32, w / 2 + 30, fill=BEZEL_IN)

    def paint(sub, box):
        X0, Y0, X1, Y1 = box
        lw, lh = sub.img.size
        g = vgrad(1, 64, SKY_T, SKY_B).resize((1, max(1, int(Y1 - Y0))), Image.BILINEAR)
        g = g.resize((lw, max(1, int(Y1 - Y0))), Image.NEAREST)
        sub.img.paste(g, (0, int(Y0)))
        if Y0 > 0:
            sub.d.rectangle([0, 0, lw, Y0], fill=SKY_T)
        # Wolken ziehen vorbei
        for (yy, sp, sc, ph) in CLOUDS:
            span = w + 400
            xx = x0 - 200 + ((ph * span - sp * t * 2.2) % span)
            cloud(sub, xx, cy + yy * h, sc * w / 520)
        # Tragfläche
        sub.poly([(x0 - 40, y1 - 0.18 * h), (x1 + 20, y1 - 0.06 * h), (x1 + 20, y1 + 10), (x0 - 40, y1 + 10)],
                 fill=(205, 212, 222))
        sub.poly([(x0 - 40, y1 - 0.18 * h), (x1 + 20, y1 - 0.06 * h), (x1 + 20, y1 - 0.045 * h),
                  (x0 - 40, y1 - 0.16 * h)], fill=(236, 240, 246))
        # Glanz
        for k, off in ((0.0, 0), (1, 70)):
            sub.line([(x0 + 60 + off, y0 + 0.5 * h), (x0 + 0.55 * w + off, y0 + 40)], (226, 240, 252), 10 - 4 * k)
        # Beschlag
        if fog > 0:
            base = fog_base()
            yy = np.linspace(0, 1, base.shape[0])[:, None]
            wipe = np.clip((yy - (1 - clear * 1.3)) / 0.2 + 1, 0, 1) if clear > 0 else 1
            alpha = np.clip(base * fog * (1 - wipe if clear > 0 else 1), 0, 1)
            am = Image.fromarray((alpha * 235).astype(np.uint8), "L").resize(
                (max(1, int(X1 - X0)), max(1, int(Y1 - Y0))), Image.BILINEAR)
            white = Image.new("RGB", am.size, (236, 242, 248))
            sub.img.paste(white, (int(X0), int(Y0)), am)
        if drops:
            for (dx, dy, r) in drops:
                sub.circle(dx, dy, r, fill=(214, 232, 248), outline=(150, 190, 225), w=2)
        # Sonnenblende
        if shade > 0:
            sy = y0 + shade * h
            sub.rrect(x0 - 10, y0 - 40, x1 + 10, sy, 20, fill=(244, 240, 233))
            sub.rrect(cx - 50, sy - 26, cx + 50, sy - 8, 9, fill=(214, 206, 192))

    clip_layer(cv, x0, y0, x1, y1, w / 2, paint)
    cv.rrect(x0, y0, x1, y1, w / 2, outline=(176, 166, 150), w=4)
    if hole:
        hx, hy = cx, y1 - 0.075 * h
        cv.circle(hx, hy, 6.5, fill=(150, 160, 172))
        cv.circle(hx, hy, 4.2, fill=(52, 62, 76))
    return (cx, y1 - 0.075 * h)


# ---------------------------------------------------------------- Querschnitt
IN_X, MID_X, OUT_X = 270, 560, 724
IN_T, MID_T, OUT_T = 14, 26, 34
PY0, PY1 = 600, 1150
HOLE_Y = 1080


def section_bg(cv, gap_col=GAP_AIR):
    cv.rrect(-20, 520, MID_X, 1230, 0, fill=CABIN_AIR)
    cv.rrect(MID_X, 520, OUT_X, 1230, 0, fill=gap_col)
    cv.rrect(OUT_X, 520, 1100, 1230, 0, fill=COLD_AIR)
    for i, (sx, sy) in enumerate(((860, 640), (980, 760), (900, 940), (1010, 1060), (830, 1150), (950, 560))):
        cv.circle(sx, sy, 3 + (i % 2), fill=(120, 150, 200))


def section_frame(cv):
    # Rumpfrahmen oben/unten + Verkleidung
    for y0, y1 in ((520, PY0), (PY1, 1230)):
        cv.rrect(MID_X - 40, y0, OUT_X + 40, y1, 10, fill=FRAME)
        cv.rrect(MID_X - 40, y0 + 8 if y0 == 520 else y0, OUT_X + 40, y0 + 22 if y0 == 520 else y0 + 14, 4,
                 fill=FRAME_D)
        cv.rrect(IN_X - 34, y0, IN_X + 34, y1, 10, fill=(214, 204, 188))
    cv.rrect(OUT_X + 20, 480, OUT_X + 44, 1270, 8, fill=FRAME_D)  # Außenhaut


def pane(cv, x, th, color, glow=0.0, glow_col=AMBER, hole_y=None, bulge=0.0):
    if glow > 0:
        cv.rrect(x - th / 2 - 12, PY0 - 6, x + th / 2 + 12, PY1 + 6, th / 2 + 12, fill=mix(NAVY, glow_col, glow * 0.55))
    if bulge > 0:
        pts = []
        for k in np.linspace(0, 1, 30):
            pts.append((x - th / 2 + bulge * math.sin(math.pi * k), PY0 + (PY1 - PY0) * k))
        for k in np.linspace(1, 0, 30):
            pts.append((x + th / 2 + bulge * math.sin(math.pi * k), PY0 + (PY1 - PY0) * k))
        cv.poly(pts, fill=color)
        return
    if hole_y is None:
        cv.rrect(x - th / 2, PY0, x + th / 2, PY1, th / 2, fill=color)
        cv.line([(x - th / 2 + 5, PY0 + 30), (x - th / 2 + 5, PY1 - 30)], mix(color, WHITE, 0.6), 3)
    else:
        g = 9
        cv.rrect(x - th / 2, PY0, x + th / 2, hole_y - g, th / 2, fill=color)
        cv.rrect(x - th / 2, hole_y + g, x + th / 2, PY1, th / 2, fill=color)
        cv.line([(x - th / 2 + 5, PY0 + 30), (x - th / 2 + 5, hole_y - 40)], mix(color, WHITE, 0.6), 3)


def region_labels(cv, t, t0):
    label(cv, "CABIN", 130, 560, t, t0, P_WARM, 36, "xb")
    label(cv, "OUTSIDE", 905, 560, t, t0, P_COLD, 36, "xb")


# ================================================================ SZENEN

def passenger(cv, x, y, a=1.0):
    """Passagier von hinten (Hinterkopf + Schultern), sitzt direkt am Fenster."""
    bg = WALL_B
    cv.rrect(x - 250, y + 95, x + 260, y + 700, 210, fill=mix(bg, (46, 92, 118), a))
    cv.rrect(x - 52, y + 40, x + 52, y + 140, 30, fill=mix(bg, (206, 160, 126), a))
    cv.ellipse(x + 104, y + 12, 22, 30, fill=mix(bg, (222, 172, 136), a))
    cv.ellipse(x, y, 112, 124, fill=mix(bg, (58, 44, 38), a))
    cv.ellipse(x - 30, y - 50, 44, 30, fill=mix(bg, (78, 60, 50), a))


def sc_hook(cv, t, C, s0, s1):
    cv.img.paste(bg_wall())
    T = C.T
    hx, hy = 540, 780 + 360 - 0.075 * 720          # Loch in Weltkoordinaten
    # Bild 1: extreme Nahaufnahme mit "Punch", dann Rückzoom zum ganzen Fenster, dann langsam wieder hin
    punch = 1 + 0.22 * (1 - out_cubic(ramp(t, 0, 0.45)))
    back = smooth(ramp(t, T["hook2"] - 0.05, 1.1))
    push = smooth(ramp(t, T["hook3"] + 0.3, max(0.6, s1 - T["hook3"])))
    z = lerp(3.2 * punch, 1.0, back) * (1 + 0.35 * push)
    fx, fy = lerp(hx, 540, back), lerp(hy, 800, back)
    fx, fy = lerp(fx, hx, push * 0.5), lerp(fy, hy, push * 0.5)
    ty = lerp(800, 860, back)
    if t < 0:  # Loop-Übergang am Videoende: ganzes Fenster -> Nahaufnahme, endet genau auf Bild 1
        zin = smooth(ramp(t, -LOOP_ZOOM, LOOP_ZOOM)) ** 1.6
        z = lerp(1.0, 3.2 * punch, zin)
        fx, fy, ty = 540, lerp(800, hy, zin), 800
    cv.cam(z, fx, fy, 540, ty)
    front_window(cv, 540, 780, 500, 720, t, shade=0.17)
    for k in range(3):
        ph = (t * 0.9 + k / 3) % 1
        cv.circle(hx, hy, 9 + 30 * ph, outline=mix(SKY_B, AMBER, 1 - ph), w=2.4 / max(1, z * 0.45))
    cv.circle(hx, hy, 14, outline=AMBER, w=2.6 / max(1, z * 0.45))
    cv.reset()
    # Pfeil auf das Loch (nur in der Nahaufnahme)
    aa = (1 - ramp(t, T["hook2"] - 0.1, 0.25)) * ramp(t, -0.25, 0.2)
    if aa > 0:
        k = out_back(ramp(t, 0.15, 0.4))
        X, Y = cv_point(z, fx, fy, ty, hx, hy)
        cv.arrow(X, 470 + 40 * (1 - k), X, Y - 64, mix(SKY_B, AMBER, aa), 14, 40)
    # Passagier gleitet von links ins Bild
    pk = out_cubic(ramp(t, T["hook2"] + 0.35, 0.6))
    if pk > 0:
        passenger(cv, lerp(-260, 215, pk) - push * 40, 1020 + push * 30)
    headline(cv, "EVERY PLANE WINDOW HAS THIS", t, -0.35, T["hook2"] - 0.05, y=400, size=58)
    headline(cv, "NEVER NOTICED?", t, T["hook3"] - 0.05, s1 + 1, y=400, fg=AMBER, size=60)


def sc_purpose(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    front_window(cv, 540, 650, 230, 330, t, shade=0.15)
    jobs = ramp(t, T["purp2"] + 0.4, 0.3)
    for i, (cid, word, cx) in enumerate((("nc1", "CRACK?", 290), ("nc2", "DEFECT?", 790))):
        k = out_cubic(ramp(t, T[cid] - 0.05, 0.35))
        if k <= 0:
            continue
        fade = k * (1 - jobs)
        y = 1080 + 60 * (1 - k)
        cv.rrect(cx - 200, y - 105, cx + 200, y + 105, 30, fill=mix(NAVY, CARD, fade), outline=mix(NAVY, CARD_LINE, fade), w=3)
        ic = mix(NAVY, WHITE, fade)
        if i == 0:
            cv.line([(cx - 10, y - 88), (cx + 14, y - 58), (cx - 16, y - 34), (cx + 18, y - 4), (cx + 4, y + 18)], ic, 8)
            cv.line([(cx - 16, y - 34), (cx - 46, y - 22)], ic, 6)
        else:
            cv.poly([(cx, y - 78), (cx + 44, y), (cx - 44, y)], fill=ic)
            cv.line([(cx, y - 52), (cx, y - 26)], mix(NAVY, CARD, fade), 8)
            cv.circle(cx, y - 13, 5, fill=mix(NAVY, CARD, fade))
        cv.put(txt(word, 50, WHITE, "black"), cx, y + 58, fade)
        xk = out_back(ramp(t, T[cid] + 0.45, 0.25))
        if xk > 0 and fade > 0:
            col = mix(NAVY, CORAL, fade)
            r = 120 * xk
            cv.line([(cx - r, y - r * 0.75), (cx + r, y + r * 0.75)], col, 16)
            cv.line([(cx - r, y + r * 0.75), (cx + r, y - r * 0.75)], col, 16)
    sk = ramp(t, T["purp1"] + 0.2, 0.28)
    if sk > 0:
        sc = lerp(2.0, 1.0, out_cubic(sk))
        cv.put(stamp_sprite("ON PURPOSE", MINT, 8), 540, 650, min(1, sk * 2), sc * 0.85)
    for i, (cx, word) in enumerate(((290, "JOB 1"), (790, "JOB 2"))):
        k = out_back(ramp(t, T["purp2"] + 0.5 + 0.25 * i, 0.35))
        if k > 0:
            cv.rrect(cx - 170 * k, 1080 - 95 * k, cx + 170 * k, 1080 + 95 * k, 40 * k, fill=AMBER)
            cv.put(txt(word, 64, NAVY, "black"), cx, 1050, 1, k)
            cv.put(txt("?", 54, NAVY, "black"), cx, 1118, 1, k)


def slab(cv, cx, cy, off, thick, face, side, n=None, w=330, h=470):
    dx, dy = 0.78, -0.62
    n = n or max(2, int(thick / 3))
    for i in range(n, -1, -1):
        o = off + thick * i / n
        col = face if i == 0 else side
        x, y = cx + dx * o, cy + dy * o
        cv.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, w / 2, fill=col,
                 outline=mix(col, WHITE, 0.35) if i == 0 else None, w=3 if i == 0 else 0)
    x, y = cx + dx * off, cy + dy * off
    cv.line([(x - w * 0.28, y + h * 0.1), (x + w * 0.05, y - h * 0.3)], mix(face, WHITE, 0.6), 8)
    return x, y


def sc_assume(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    sp = smooth(ramp(t, T["ass3"] + 0.1, 0.8))
    shake = math.sin((t - T["ass2"]) * 40) * 10 * (ramp(t, T["ass2"], 0.05) - ramp(t, T["ass2"] + 0.5, 0.2)) \
        if t > T["ass2"] else 0
    cx, cy = 470 + shake, 860
    if sp <= 0:
        slab(cv, cx, cy, 0, 110, (150, 200, 238), (70, 120, 172), n=36)
    else:
        offs = [0, 75 + 120 * sp, 150 + 240 * sp]
        cols = [(GLASS_IN, (110, 160, 200)), (GLASS_MID, (80, 140, 196)), (GLASS_OUT, (56, 112, 176))]
        thick = [lerp(36, 14, sp), lerp(36, 24, sp), lerp(38, 30, sp)]
        pos = []
        for k in (2, 1, 0):
            pos.append(slab(cv, cx - 120 * sp, cy + 90 * sp, offs[k], thick[k], cols[k][0], cols[k][1], n=10))
        for j, (x, y) in enumerate(reversed(pos)):
            kk = out_back(ramp(t, T["ass3"] + 0.35 + 0.25 * j, 0.3))
            if kk > 0:
                bx, by = x + 150, y - 210
                cv.circle(bx, by, 40 * kk, fill=AMBER)
                cv.put(txt(str(j + 1), 50, NAVY, "black"), bx, by, 1, kk)
    if T["ass2"] - 0.2 < t < T["ass3"] + 0.25:
        q = out_back(ramp(t, T["ass2"] + 0.1, 0.3))
        cv.put(txt("?", 150, AMBER, "black"), 780, 600, ramp(t, T["ass2"] + 0.1, 0.15) * (1 - ramp(t, T["ass3"], 0.2)), q)
    headline(cv, "ONE THICK SHEET?", t, T["ass1"] + 0.2, T["ass3"] + 0.05, y=420)
    headline(cv, "ACTUALLY: 3 PANES", t, T["ass3"] + 0.1, s1 + 1, y=420, fg=AMBER)


def sc_layers(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    section_bg(cv)
    particles(cv, 40, 30, MID_X - 30, 540, 1210, t, 1, P_WARM, 6, 0.5, CABIN_AIR, 0.35)
    section_frame(cv)
    g = smooth(ramp(t, T["pan1"] + 0.3, 0.5))
    tap_t = T["scr1"] + 0.75
    pane(cv, IN_X, IN_T, GLASS_IN, glow=0.6 * ramp(t, tap_t, 0.1) * (1 - ramp(t, tap_t + 0.6, 0.5)), glow_col=WHITE)
    pane(cv, MID_X, MID_T, GLASS_MID, glow=g)
    pane(cv, OUT_X, OUT_T, GLASS_OUT, glow=g)
    # Finger
    fk = out_cubic(ramp(t, T["scr1"], 0.75)) * (1 - smooth(ramp(t, T["scr2"] + 0.6, 0.6)))
    if fk > 0:
        fx = lerp(-150, IN_X - IN_T / 2 - 4, fk)
        cv.rrect(fx - 360, 830, fx, 900, 35, fill=(236, 190, 152))
        cv.rrect(fx - 60, 840, fx - 12, 890, 18, fill=(250, 220, 200))
    if t > tap_t:
        for k in range(2):
            ph = clamp((t - tap_t - k * 0.15) / 0.7)
            if 0 < ph < 1:
                cv.circle(IN_X, 865, 20 + 120 * ph, outline=mix(CABIN_AIR, WHITE, 1 - ph), w=4)
    region_labels(cv, t, s0 + 0.2)
    label(cv, "SCRATCH", 415, 985, t, T["scr2"], WHITE, 40)
    label(cv, "PANE", 415, 1030, t, T["scr2"] + 0.1, WHITE, 40)
    label(cv, "no pressure", 415, 1080, t, T["scr3"], SOFT, 30, "semi")
    if t > T["scr2"]:
        k = out_cubic(ramp(t, T["scr2"] + 0.1, 0.3))
        cv.arrow(330, 985, 330 - 40 * k, 985, mix(CABIN_AIR, WHITE, k), 6, 18)
    label(cv, "MIDDLE", MID_X - 20, 475, t, T["pan2"] + 0.1, AMBER, 40)
    label(cv, "OUTER", OUT_X + 60, 475, t, T["pan2"] + 0.75, AMBER, 40)
    headline(cv, "2 STRONG ACRYLIC PANES", t, T["pan1"] + 0.1, s1 + 1, y=372, size=54)


def sc_pressure(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    pa = 1 - smooth(ramp(t, T["alt2"] - 0.1, 0.4))
    if pa > 0:
        k = smooth(ramp(t, s0 + 0.1, max(0.6, T["alt2"] - s0 - 0.4)))
        cv.rrect(60, 1150, 1020, 1160, 4, fill=mix(NAVY, (60, 84, 120), pa))
        pts = [(lerp(150, 760, q), lerp(1130, 640, q ** 1.6)) for q in np.linspace(0, k, 25)]
        if len(pts) > 1:
            for i in range(0, len(pts) - 1, 2):
                cv.line([pts[i], pts[i + 1]], mix(NAVY, SOFT, pa * 0.8), 5)
        x, y = pts[-1]
        ang = -0.55 * (1 - k) - 0.12
        plane_icon(cv, x, y, 110, mix(NAVY, WHITE, pa), ang)
        alt = int(round(35000 * smooth(k) / 500) * 500)
        cv.put(txt(f"{alt:,} FT", 96, AMBER, "black"), 540, 470, pa)
        cv.put(txt("≈ 10.7 km cruising altitude", 34, SOFT, "semi"), 540, 545, pa * ramp(t, T["alt1"] + 0.6, 0.3))
    ba = smooth(ramp(t, T["alt2"] - 0.1, 0.4))
    if ba > 0:
        inside = (80, 720, 500, 1215)
        outside = (580, 720, 1000, 1215)
        cv.rrect(*inside, 30, fill=mix(NAVY, CABIN_AIR, ba))
        cv.rrect(*outside, 30, fill=mix(NAVY, COLD_AIR, ba))
        oa = ramp(t, T["alt2"], 0.4)
        particles(cv, 20, 600, 980, 740, 1195, t, 11, P_COLD, 8, 0.6, COLD_AIR, oa)
        ia = ramp(t, T["alt3"], 0.4)
        particles(cv, 64, 100, 470, 740, 1195, t, 12, P_WARM, 8, 0.8, CABIN_AIR, ia)
        bulge = 26 * smooth(ramp(t, T["alt4"] + 0.2, 0.6))
        cv.rrect(525, 690, 555, 725, 6, fill=FRAME)
        cv.rrect(525, 1210, 555, 1245, 6, fill=FRAME)
        pts = []
        for k in np.linspace(0, 1, 30):
            pts.append((526 + bulge * math.sin(math.pi * k), 725 + 485 * k))
        for k in np.linspace(1, 0, 30):
            pts.append((554 + bulge * math.sin(math.pi * k), 725 + 485 * k))
        cv.poly(pts, fill=mix(NAVY, GLASS_OUT, ba))
        label(cv, "OUTSIDE", 790, 625, t, T["alt2"], P_COLD, 40)
        label(cv, "≈ ¼ of sea-level pressure", 790, 672, t, T["alt2"] + 0.3, SOFT, 30, "semi")
        label(cv, "INSIDE", 290, 625, t, T["alt3"], P_WARM, 40)
        label(cv, "kept much denser", 290, 672, t, T["alt3"] + 0.3, SOFT, 30, "semi")
        ak = out_cubic(ramp(t, T["alt4"] + 0.1, 0.5))
        if ak > 0:
            for i, yy in enumerate((850, 965, 1080)):
                kk = out_cubic(ramp(t, T["alt4"] + 0.1 + 0.1 * i, 0.4))
                wob = math.sin(t * 9 + i) * 6
                cv.arrow(250 + wob, yy, 250 + 240 * kk + wob, yy, AMBER, 22, 54)
    headline(cv, "HUNDREDS OF KG OF FORCE", t, T["alt5"] + 0.15, s1 + 1, y=372, fg=AMBER, size=54)
    if t > T["alt5"]:
        label(cv, "per window · rough estimate", 540, 448, t, T["alt5"] + 0.5, SOFT, 28, "semi")


def sc_hole(cv, t, C, s0, s1):
    cv.img.paste(bg_navy())
    T = C.T
    fill_k = ramp(t, T["flow1"] + 0.1, 1.6)
    section_bg(cv, mix(GAP_AIR, CABIN_AIR, fill_k * 0.8))
    particles(cv, 46, 30, MID_X - 22, 540, 1210, t, 1, P_WARM, 7, 0.6)
    particles(cv, 7, OUT_X + 30, 1060, 540, 1210, t, 2, P_COLD, 7, 0.4)
    # Partikel strömen durch das Loch in den Spalt
    n_gap = 16
    hole_in = (MID_X - 30, HOLE_Y)
    hole_out = (MID_X + 26, HOLE_Y)
    for i in range(n_gap):
        ti = T["flow1"] + 0.05 + i * 0.09
        k = ramp(t, ti, 0.75)
        if k <= 0:
            continue
        gx, gy = particle_pos(i, n_gap, MID_X + 26, OUT_X - 26, 540, 1210, t, 5, 0.5)
        if k < 0.4:
            q = smooth(k / 0.4)
            x, y = lerp(hole_in[0] - 60, hole_out[0], q), lerp(HOLE_Y - 20, HOLE_Y, q)
        else:
            q = smooth((k - 0.4) / 0.6)
            x, y = lerp(hole_out[0], gx, q), lerp(HOLE_Y, gy, q)
        cv.circle(x, y, 7, fill=P_WARM)
    section_frame(cv)
    load = smooth(ramp(t, T["load1"] + 0.1, 0.5))
    backup = smooth(ramp(t, T["load3"] + 0.2, 0.5))
    pane(cv, IN_X, IN_T, GLASS_IN)
    pane(cv, MID_X, MID_T, GLASS_MID, glow=backup, glow_col=MINT, hole_y=HOLE_Y)
    pane(cv, OUT_X, OUT_T, GLASS_OUT, glow=load, glow_col=AMBER)
    # Ring um das Loch
    rk = ramp(t, T["hole1"] + 0.1, 0.3) * (1 - ramp(t, T["flow2"], 0.4))
    if rk > 0:
        for k in range(2):
            ph = ((t - T["hole1"]) * 0.9 + k / 2) % 1
            cv.circle(MID_X, HOLE_Y, 24 + 40 * ph, outline=mix(CABIN_AIR, AMBER, rk * (1 - ph)), w=4)
        cv.circle(MID_X, HOLE_Y, 30, outline=mix(CABIN_AIR, AMBER, rk), w=5)
    # gleiche Druckpfeile am Mittelglas
    ea = ramp(t, T["flow2"] + 0.1, 0.3) * (1 - ramp(t, T["load1"], 0.3))
    if ea > 0:
        for yy in (760, 900):
            k = out_cubic(ramp(t, T["flow2"] + 0.1, 0.4))
            cv.arrow(MID_X - 110, yy, MID_X - 110 + 80 * k, yy, mix(CABIN_AIR, WHITE, ea), 12, 30)
            cv.arrow(MID_X + 110, yy, MID_X + 110 - 80 * k, yy, mix(GAP_AIR, WHITE, ea), 12, 30)
        cv.put(txt("=", 80, MINT, "black"), MID_X, 830, ea * ramp(t, T["flow3"], 0.3))
    # Last auf der Außenscheibe
    if load > 0:
        for i, yy in enumerate((720, 860, 1000)):
            kk = out_cubic(ramp(t, T["load1"] + 0.1 + 0.08 * i, 0.4))
            cv.arrow(OUT_X - 108, yy, OUT_X - 108 + 70 * kk, yy, AMBER, 14, 32)
    if backup > 0:
        shield_icon(cv, 410, 830, 70 * out_back(ramp(t, T["load3"] + 0.2, 0.4)), MINT)
    region_labels(cv, t, s0)
    label(cv, "MIDDLE", MID_X - 20, 475, t, s0, AMBER, 40)
    label(cv, "OUTER", OUT_X + 60, 475, t, s0, AMBER, 40)
    label(cv, "breather hole", 400, 1010, t, T["hole2"], WHITE, 34)
    if t > T["hole2"]:
        k = out_cubic(ramp(t, T["hole2"] + 0.1, 0.3))
        cv.arrow(470, 1035, 470 + 50 * k, 1035 + 30 * k, mix(CABIN_AIR, WHITE, k), 6, 18)
    headline(cv, "THE TINY HOLE", t, T["hole1"], T["flow3"], y=372, size=54)
    headline(cv, "EQUAL PRESSURE", t, T["flow3"], T["load1"], y=372, fg=MINT, size=54)
    headline(cv, "OUTER PANE: FULL LOAD", t, T["load1"], T["load2"] + 0.2, y=372, fg=AMBER, size=54)
    headline(cv, "MIDDLE PANE: BACKUP", t, T["load2"] + 0.2, s1 + 1, y=372, fg=MINT, size=54)


DROPS = [(-120, -200, 9), (60, -260, 7), (150, -60, 10), (-60, -20, 8), (100, 120, 7), (-150, 140, 9),
         (20, 40, 6), (-30, -140, 7), (130, -170, 6)]


def sc_fog(cv, t, C, s0, s1):
    cv.img.paste(bg_wall())
    T = C.T
    cx, cy, w, h = 540, 820, 440, 620
    hx, hy = cx, cy + h / 2 - 0.075 * h
    fog = smooth(ramp(t, s0 + 0.2, 1.0))
    clear = smooth(ramp(t, T["fog3"] + 0.5, 1.2))
    dk = ramp(t, T["fog2"] + 0.2, max(0.8, T["fog3"] - T["fog2"] + 0.3))
    drops = []
    for i, (dx, dy, r) in enumerate(DROPS):
        k = smooth(clamp(dk * 1.6 - i * 0.07))
        x, y = lerp(cx + dx, hx, k), lerp(cy + dy, hy, k)
        rr = r * (1 - 0.7 * k) * ramp(t, s0 + 0.4 + i * 0.05, 0.3)
        if k < 0.98 and rr > 0.5:
            drops.append((x, y, rr))
    front_window(cv, cx, cy, w, h, t, shade=0.0, fog=fog, clear=clear, drops=drops)
    # Strömungspfeile zum Loch
    fa = ramp(t, T["fog2"], 0.3) * (1 - ramp(t, T["fog3"] + 0.6, 0.4))
    if fa > 0:
        for side in (-1, 1):
            p = [(hx + side * 150, hy - 200), (hx + side * 90, hy - 90), (hx + side * 22, hy - 24)]
            cv.line(p, mix((205, 220, 235), (60, 120, 190), fa), 7)
        cv.arrow(hx, hy + 6, hx, hy + 120, mix(BEZEL, (60, 120, 190), fa), 10, 28)
    ck = out_back(ramp(t, T["fog3"] + 1.1, 0.35))
    if ck > 0:
        cv.circle(820, 600, 62 * ck, fill=MINT)
        cv.line([(795, 600), (814, 622), (848, 580)], NAVY, 13 * ck)
    headline(cv, "JOB 2", t, T["fog1"] - 0.05, T["fog3"] + 0.3, y=400, fg=AMBER)
    headline(cv, "NO FOG · NO FROST", t, T["fog3"] + 0.3, s1 + 1, y=400, fg=MINT, size=58)


def sc_outro(cv, t, C, s0, s1):
    cv.img.paste(bg_wall())
    T = C.T
    ek = smooth(ramp(t, T["end3"] - 0.15, 0.35))
    out = smooth(ramp(t, C.total - LOOP_ZOOM - 0.3, 0.3))      # Karte fliegt raus, Loop beginnt
    gk = smooth(ramp(t, C.total - LOOP_ZOOM - 0.45, 0.45))     # Fenster -> Hook-Geometrie
    hx, hy = front_window(cv, 540, lerp(760 - 60 * ek, 780, gk), lerp(380, 500, gk), lerp(540, 720, gk), t,
                          shade=lerp(0.12, 0.17, gk))
    a = ramp(t, T["end1"], 0.3)
    for k in range(3):
        ph = ((t - T["end1"]) * 0.9 + k / 3) % 1
        cv.circle(hx, hy, 10 + 26 * ph, outline=mix(BEZEL_IN, AMBER, a * (1 - ph)), w=2.2)
    for i, (cx, word, cue_off) in enumerate(((270, "SPARE WINDOW", 0.1), (810, "DEFOGGER", 1.0))):
        k = out_back(ramp(t, T["end2"] + cue_off, 0.35)) * (1 - ek)
        if k <= 0.01:
            continue
        y = 1160
        cv.rrect(cx - 175 * k, y - 120 * k, cx + 175 * k, y + 120 * k, 36 * k, fill=NAVY)
        if i == 0:
            shield_icon(cv, cx, y - 30, 52 * k, MINT)
        else:
            drop_icon(cv, cx, y - 30, 52 * k, P_COLD)
            cv.line([(cx - 44 * k, y - 76 * k), (cx + 44 * k, y + 16 * k)], CORAL, 10 * k)
        cv.put(txt(word, 40, WHITE, "black"), cx, y + 72 * k, 1, k)
    if ek > 0 and out < 1:
        y = lerp(1500, 760, out_cubic(ek)) - 700 * out ** 2
        bob = math.sin(max(0, t - T["end4"]) * 6) * 4 * ramp(t, T["end4"], 0.2)
        cv.put(endcard_sprite(), 540, y + bob, min(1, ek * 1.5) * (1 - out), 1 + 0.15 * out)


SCENE_FUNCS = {"hook": sc_hook, "purpose": sc_purpose, "assume": sc_assume, "layers": sc_layers,
               "pressure": sc_pressure, "hole": sc_hole, "fog": sc_fog, "outro": sc_outro}
