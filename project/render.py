"""Everyday Unpacked – Renderer.

Aufruf (aus dem Repo-Hauptordner):
    python3 project/render.py                # Timing, Untertitel, SFX, Video (+ final.mp4 falls Voiceover da)
    python3 project/render.py --still 12.5   # nur ein Standbild bei 12,5 s (zum Prüfen)
    python3 project/render.py --workers 8

Alle Grafiken werden hier per Code gezeichnet (PIL, 2x-Supersampling), Sounds in sfx.py synthetisiert.
"""
import argparse
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import episode as EP  # noqa: E402
import sfx  # noqa: E402
import timeline as TL  # noqa: E402

W, H, FPS = 1080, 1920, 30
S = 2                      # Supersampling
W2, H2 = W * S, H * S
OUT = os.path.join(ROOT, "output")
VO_PATH = os.path.join(ROOT, "input", "voiceover.mp3")

# ---------------------------------------------------------------- Farben
NAVY = (13, 22, 40)
NAVY2 = (24, 40, 68)
CARD = (30, 48, 80)
CARD_LINE = (62, 88, 128)
WHITE = (246, 248, 252)
SOFT = (170, 186, 210)
AMBER = (255, 184, 72)
MINT = (84, 222, 164)
CORAL = (255, 102, 102)
SKY_T = (74, 146, 226)
SKY_B = (178, 216, 248)
WALL_T = (238, 233, 223)
WALL_B = (214, 206, 192)
BEZEL = (226, 219, 206)
BEZEL_IN = (196, 186, 170)
CABIN_AIR = (58, 42, 34)
COLD_AIR = (14, 34, 66)
GAP_AIR = (22, 36, 60)
P_WARM = (255, 214, 160)
P_COLD = (150, 200, 255)
GLASS_IN = (196, 228, 248)
GLASS_MID = (128, 194, 238)
GLASS_OUT = (88, 160, 226)
FRAME = (122, 132, 150)
FRAME_D = (88, 98, 116)

FONT_DIR = os.path.join(HERE, "assets", "fonts")
FONTS = {"black": "InterDisplay-Black.otf", "xb": "InterDisplay-ExtraBold.otf",
         "bold": "InterDisplay-Bold.otf", "semi": "InterDisplay-SemiBold.otf", "med": "Inter-Medium.otf"}


@lru_cache(maxsize=None)
def font(name, px):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[name]), int(px))


# ---------------------------------------------------------------- Easing / Zeit
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def ramp(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def out_back(x, s=1.7):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def lerp(a, b, k):
    return a + (b - a) * k


def mix(c1, c2, k):
    k = clamp(k)
    return tuple(int(round(a + (b - a) * k)) for a, b in zip(c1, c2))


def tri(v):
    v = v % 2.0
    return 1 - abs(v - 1)


def window(t, t0, t1, fin=0.25, fout=0.25):
    """Sichtbarkeit 0..1: Einblenden ab t0, Ausblenden bis t1."""
    return min(ramp(t, t0, fin), 1 - ramp(t, t1 - fout, fout))


# ---------------------------------------------------------------- Zeichenfläche
class Cv:
    def __init__(self, img, z=1.0, ox=0.0, oy=0.0):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.z, self.ox, self.oy = z, ox, oy

    def cam(self, z, fx, fy, tx, ty):
        """Weltpunkt (fx,fy) erscheint bei Bildschirmpunkt (tx,ty) mit Zoom z."""
        self.z, self.ox, self.oy = z, tx - fx * z, ty - fy * z

    def reset(self):
        self.z, self.ox, self.oy = 1.0, 0.0, 0.0

    def P(self, x, y):
        return ((x * self.z + self.ox) * S, (y * self.z + self.oy) * S)

    def L(self, v):
        return v * self.z * S

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, w=0):
        X0, Y0 = self.P(x0, y0)
        X1, Y1 = self.P(x1, y1)
        if X1 - X0 < 1 or Y1 - Y0 < 1:
            return
        rr = max(0, min(self.L(r), (X1 - X0) / 2 - 0.01, (Y1 - Y0) / 2 - 0.01))
        self.d.rounded_rectangle([X0, Y0, X1, Y1], radius=rr, fill=fill, outline=outline,
                                 width=int(self.L(w)) if w else 0)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, w=0):
        X, Y = self.P(cx, cy)
        RX, RY = self.L(rx), self.L(ry)
        self.d.ellipse([X - RX, Y - RY, X + RX, Y + RY], fill=fill, outline=outline,
                       width=max(1, int(self.L(w))) if w else 0)

    def circle(self, cx, cy, r, fill=None, outline=None, w=0):
        self.ellipse(cx, cy, r, r, fill, outline, w)

    def poly(self, pts, fill=None, outline=None, w=0):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=fill, outline=outline,
                       width=int(self.L(w)) if w else 0)

    def line(self, pts, color, w, caps=True):
        P = [self.P(x, y) for x, y in pts]
        self.d.line(P, fill=color, width=max(1, int(self.L(w))), joint="curve")
        if caps:
            for x, y in (pts[0], pts[-1]):
                self.circle(x, y, w / 2, fill=color)

    def arrow(self, x0, y0, x1, y1, color, w=14, head=34):
        ang = math.atan2(y1 - y0, x1 - x0)
        bx, by = x1 - math.cos(ang) * head * 0.8, y1 - math.sin(ang) * head * 0.8
        self.line([(x0, y0), (bx, by)], color, w)
        pa = ang + math.pi / 2
        hw = head * 0.62
        self.poly([(x1, y1), (bx + math.cos(pa) * hw, by + math.sin(pa) * hw),
                   (bx - math.cos(pa) * hw, by - math.sin(pa) * hw)], fill=color)

    def put(self, im, x, y, a=1.0, sc=1.0, world=False, anchor="mm"):
        """RGBA-Sprite (in 2x-Auflösung) einfügen; x,y in Design-Koordinaten."""
        if a <= 0.004 or sc <= 0.01:
            return
        if world:
            X, Y = self.P(x, y)
            sc = sc * self.z
        else:
            X, Y = x * S, y * S
        if abs(sc - 1) > 0.01:
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
        m = im.getchannel("A")
        if a < 0.999:
            m = m.point(lambda v: int(v * a))
        ax = {"l": 0, "m": 0.5, "r": 1}[anchor[0]]
        ay = {"t": 0, "m": 0.5, "b": 1}[anchor[1]]
        self.img.paste(im, (int(X - im.width * ax), int(Y - im.height * ay)), m)


# ---------------------------------------------------------------- Sprites (gecacht)
@lru_cache(maxsize=4096)
def txt(s, size, color=WHITE, fnt="black", track=0):
    f = font(fnt, size * S)
    if track:
        widths = [f.getlength(ch) + track * S for ch in s]
        tw = int(sum(widths))
    else:
        tw = int(f.getlength(s))
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (tw + 8 * S, asc + desc + 4 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if track:
        x = 4 * S
        for ch, wch in zip(s, widths):
            d.text((x, 2 * S), ch, font=f, fill=color)
            x += wch
    else:
        d.text((4 * S, 2 * S), s, font=f, fill=color)
    return im


@lru_cache(maxsize=512)
def pill(s, size=64, fg=WHITE, bg=(10, 18, 34, 235), fnt="black", padx=34, pady=16, border=None):
    t = txt(s, size, fg, fnt)
    w, h = t.width + 2 * padx * S, int(size * 1.25 * S) + 2 * pady * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=bg,
                        outline=border, width=3 * S if border else 0)
    im.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2 + int(size * 0.02 * S)))
    return im


@lru_cache(maxsize=64)
def stamp_sprite(s, color, angle):
    t = txt(s, 92, color, "black")
    pad = 28 * S
    w, h = t.width + 2 * pad, t.height + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6 * S, 6 * S, w - 6 * S, h - 6 * S], radius=26 * S, fill=(10, 30, 26, 220),
                        outline=color, width=8 * S)
    im.alpha_composite(t, (pad, pad))
    return im.rotate(angle, resample=Image.BICUBIC, expand=True)


# ---------------------------------------------------------------- Hintergründe
def vgrad(w, h, c1, c2):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(c1)[None, None, :] * (1 - t) + np.array(c2)[None, None, :] * t)
    return Image.fromarray(np.broadcast_to(arr, (h, w, 3)).astype(np.uint8), "RGB")


@lru_cache(maxsize=None)
def bg_navy():
    im = vgrad(W2, H2, NAVY2, NAVY)
    d = ImageDraw.Draw(im)
    # feines Punktraster als Textur
    for y in range(0, H2, 72 * S // 2):
        for x in range(0, W2, 72 * S // 2):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(34, 52, 84))
    return im


@lru_cache(maxsize=None)
def bg_wall():
    im = vgrad(W2, H2, WALL_T, WALL_B)
    d = ImageDraw.Draw(im)
    for x in (70 * S, 1010 * S):  # Paneel-Fugen
        d.line([(x, 0), (x, H2)], fill=(205, 196, 181), width=3 * S)
    return im


def headline(cv, s, t, t0, t1, y=400, fg=WHITE, size=64, fade=0.25):
    a = window(t, t0, t1, fade, fade)
    if a <= 0:
        return
    rise = (1 - out_cubic(ramp(t, t0, 0.35))) * 26
    cv.put(pill(s, size, fg), 540, y + rise, a, 0.92 + 0.08 * out_back(ramp(t, t0, 0.3)))


def label(cv, s, x, y, t, t0, color=WHITE, size=40, fnt="black", anchor="mm", t1=1e9):
    a = window(t, t0, t1, 0.25, 0.25)
    if a > 0:
        cv.put(txt(s, size, color, fnt), x, y + (1 - out_cubic(ramp(t, t0, 0.3))) * 14, a, anchor=anchor)


# ---------------------------------------------------------------- Bausteine
CLOUDS = [(-0.30, 26, 1.00, 0.10), (0.05, 18, 0.70, 0.55), (0.32, 34, 1.25, 0.30), (-0.05, 22, 0.55, 0.85),
          (0.45, 14, 0.85, 0.75)]


def cloud(cv, x, y, s, col=(252, 253, 255), shade=(222, 234, 246)):
    for dx, dy, r in ((-60, 10, 46), (0, -14, 62), (64, 6, 48), (110, 18, 34), (-104, 22, 30)):
        cv.ellipse(x + dx * s, y + dy * s + 8 * s, r * s, r * s * 0.8, fill=shade)
    for dx, dy, r in ((-60, 10, 46), (0, -14, 62), (64, 6, 48), (110, 18, 34), (-104, 22, 30)):
        cv.ellipse(x + dx * s, y + dy * s, r * s, r * s * 0.8, fill=col)


def clip_layer(cv, x0, y0, x1, y1, r, painter):
    X0, Y0 = cv.P(x0, y0)
    X1, Y1 = cv.P(x1, y1)
    bx0, by0 = max(0, int(X0)), max(0, int(Y0))
    bx1, by1 = min(cv.img.width, int(X1) + 1), min(cv.img.height, int(Y1) + 1)
    if bx1 <= bx0 or by1 <= by0:
        return
    layer = Image.new("RGB", (bx1 - bx0, by1 - by0))
    sub = Cv(layer, cv.z, cv.ox - bx0 / S, cv.oy - by0 / S)
    painter(sub, (X0 - bx0, Y0 - by0, X1 - bx0, Y1 - by0))
    mask = Image.new("L", layer.size, 0)
    rr = min(cv.L(r), (X1 - X0) / 2 - 0.01, (Y1 - Y0) / 2 - 0.01)
    ImageDraw.Draw(mask).rounded_rectangle([X0 - bx0, Y0 - by0, X1 - bx0, Y1 - by0], radius=rr, fill=255)
    cv.img.paste(layer, (bx0, by0), mask)


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


@lru_cache(maxsize=None)
def pseeds(seed, n):
    r = np.random.default_rng(seed)
    return r.uniform(0, 2, n), r.uniform(0, 2, n), r.uniform(-1, 1, n), r.uniform(-1, 1, n)


def particles(cv, n, x0, x1, y0, y1, t, seed, color, r=7.0, speed=1.0, bg=None, a=1.0, count=None):
    ux, uy, vx, vy = pseeds(seed, n)
    col = mix(bg, color, a) if bg is not None else color
    k = n if count is None else int(count)
    for i in range(k):
        x = x0 + tri(ux[i] + vx[i] * t * speed * 140 / max(1, x1 - x0)) * (x1 - x0)
        y = y0 + tri(uy[i] + vy[i] * t * speed * 140 / max(1, y1 - y0)) * (y1 - y0)
        cv.circle(x, y, r, fill=col)


def particle_pos(i, n, x0, x1, y0, y1, t, seed, speed=1.0):
    ux, uy, vx, vy = pseeds(seed, n)
    x = x0 + tri(ux[i] + vx[i] * t * speed * 140 / max(1, x1 - x0)) * (x1 - x0)
    y = y0 + tri(uy[i] + vy[i] * t * speed * 140 / max(1, y1 - y0)) * (y1 - y0)
    return x, y


def shield_icon(cv, x, y, s, color, check=True):
    pts = [(0, -1), (0.82, -0.68), (0.74, 0.18), (0, 1), (-0.74, 0.18), (-0.82, -0.68)]
    cv.poly([(x + px * s, y + py * s) for px, py in pts], fill=color)
    if check:
        cv.line([(x - 0.32 * s, y + 0.02 * s), (x - 0.06 * s, y + 0.3 * s), (x + 0.38 * s, y - 0.28 * s)],
                NAVY, 0.16 * s)


def drop_icon(cv, x, y, s, color):
    pts = [(x + math.sin(a) * 0.62 * s, y + 0.25 * s - math.cos(a) * 0.62 * s) for a in np.linspace(-2.2, 2.2, 24)]
    pts = [(x, y - 1.0 * s)] + [(x + math.sin(a) * 0.62 * s, y + 0.28 * s + math.cos(a) * 0.62 * s)
                                for a in np.linspace(math.pi * 0.72, -math.pi * 0.72, 30)]
    cv.poly(pts, fill=color)


def plane_icon(cv, x, y, s, color, ang=0.0):
    base = [(-1.0, -0.06), (0.78, -0.1), (1.0, 0.0), (0.78, 0.1), (-1.0, 0.08)]
    tail = [(-1.0, -0.06), (-0.82, -0.06), (-0.98, -0.48), (-1.1, -0.48)]
    wing = [(0.1, 0.0), (-0.3, 0.0), (-0.55, 0.55), (-0.38, 0.55)]
    ca, sa = math.cos(ang), math.sin(ang)

    def tr(pts):
        return [(x + (px * ca - py * sa) * s, y + (px * sa + py * ca) * s) for px, py in pts]
    cv.poly(tr(base), fill=color)
    cv.poly(tr(tail), fill=color)
    cv.poly(tr(wing), fill=mix(color, NAVY, 0.25))


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
class Ctx:
    def __init__(self, tl):
        self.T = {c["id"]: c["start"] for c in tl["cues"]}
        self.E = {c["id"]: c["end"] for c in tl["cues"]}
        self.total = tl["total"]


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
    cv.cam(z, fx, fy, 540, lerp(800, 860, back))
    front_window(cv, 540, 780, 500, 720, t, shade=0.17)
    for k in range(3):
        ph = (t * 0.9 + k / 3) % 1
        cv.circle(hx, hy, 9 + 30 * ph, outline=mix(SKY_B, AMBER, 1 - ph), w=2.4 / max(1, z * 0.45))
    cv.circle(hx, hy, 14, outline=AMBER, w=2.6 / max(1, z * 0.45))
    cv.reset()
    # Pfeil auf das Loch (nur in der Nahaufnahme)
    aa = 1 - ramp(t, T["hook2"] - 0.1, 0.25)
    if aa > 0:
        k = out_back(ramp(t, 0.15, 0.4))
        X, Y = cv_point(z, fx, fy, lerp(800, 860, back), hx, hy)
        cv.arrow(X, 470 + 40 * (1 - k), X, Y - 64, mix(SKY_B, AMBER, aa), 14, 40)
    # Passagier gleitet von links ins Bild
    pk = out_cubic(ramp(t, T["hook2"] + 0.35, 0.6))
    if pk > 0:
        passenger(cv, lerp(-260, 215, pk) - push * 40, 1020 + push * 30)
    headline(cv, "EVERY PLANE WINDOW HAS THIS", t, -1, T["hook2"] - 0.05, y=400, size=58)
    headline(cv, "NEVER NOTICED?", t, T["hook3"] - 0.05, s1 + 1, y=400, fg=AMBER, size=60)


def cv_point(z, fx, fy, ty, x, y):
    return (x - fx) * z + 540, (y - fy) * z + ty


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


@lru_cache(maxsize=None)
def endcard_sprite():
    w, h = 900 * S, 380 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=48 * S, fill=(13, 22, 40, 246), outline=CARD_LINE, width=3 * S)
    for i, line in enumerate(("WHAT SHOULD WE", "UNPACK NEXT?")):
        tsp = txt(line, 76, WHITE if i == 0 else AMBER, "black")
        im.alpha_composite(tsp, ((w - tsp.width) // 2, int((150 + 92 * i) * S)))
    # Kommentar-Blase
    bx, by = w // 2, 78 * S
    d.rounded_rectangle([bx - 56 * S, by - 40 * S, bx + 56 * S, by + 30 * S], radius=26 * S, fill=MINT)
    d.polygon([(bx - 20 * S, by + 28 * S), (bx - 36 * S, by + 54 * S), (bx + 4 * S, by + 28 * S)], fill=MINT)
    for k in (-1, 0, 1):
        d.ellipse([bx + k * 28 * S - 8 * S, by - 13 * S, bx + k * 28 * S + 8 * S, by + 3 * S], fill=NAVY)
    return im


def sc_outro(cv, t, C, s0, s1):
    cv.img.paste(bg_wall())
    T = C.T
    ek = smooth(ramp(t, T["end3"] - 0.1, 0.6))
    hx, hy = front_window(cv, 540, 760 - 60 * ek, 380, 540, t, shade=0.12)
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
    if ek > 0:
        y = lerp(1500, 760, out_cubic(ek))
        bob = math.sin(max(0, t - T["end4"]) * 5) * 4 * ramp(t, T["end4"], 0.3)
        cv.put(endcard_sprite(), 540, y + bob, min(1, ek * 1.5))


SCENE_FUNCS = {"hook": sc_hook, "purpose": sc_purpose, "assume": sc_assume, "layers": sc_layers,
               "pressure": sc_pressure, "hole": sc_hole, "fog": sc_fog, "outro": sc_outro}
XFADE = 0.32


# ---------------------------------------------------------------- Untertitel (1x)
def parse_rich(text):
    out, hi = [], False
    for word in text.split():
        start = word.startswith("*")
        w = word.strip("*") if word.count("*") else word
        if start:
            hi = True
        out.append((w.replace("*", ""), hi))
        if word.endswith("*") or word.endswith("*,") or word.endswith("*:") or "*" in word[1:]:
            hi = False
    return out


@lru_cache(maxsize=256)
def caption_img(text):
    f = font("black", 58)
    words = parse_rich(text)
    space = f.getlength(" ")
    maxw = 840
    lines, cur, cw = [], [], 0
    for wd, hi in words:
        ww = f.getlength(wd)
        if cur and cw + space + ww > maxw:
            lines.append(cur)
            cur, cw = [], 0
        cw = cw + (space if cur else 0) + ww
        cur.append((wd, hi, ww))
    lines.append(cur)
    if len(lines) == 2 and len(lines[1]) == 1 and len(lines[0]) > 2:  # Einzelwort vermeiden
        lines[1].insert(0, lines[0].pop())
    lh = 72
    widths = [sum(w for _, _, w in ln) + space * (len(ln) - 1) for ln in lines]
    bw, bh = int(max(widths)) + 64, lh * len(lines) + 34
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=26, fill=(8, 14, 28, 190))
    y = 14
    for ln, lw in zip(lines, widths):
        x = (bw - lw) / 2
        for wd, hi, ww in ln:
            d.text((x, y), wd, font=f, fill=AMBER if hi else WHITE)
            x += ww + space
        y += lh
    return im


def draw_caption(frame, tl, t):
    cues = tl["cues"]
    cur = None
    for i, c in enumerate(cues):
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else tl["total"]
        hold = nxt if nxt - c["end"] < 0.9 else c["end"] + 0.35
        if c["start"] - 0.03 <= t < hold:
            cur = c
            break
    if not cur:
        return
    im = caption_img(cur["text"])
    k = out_back(ramp(t, cur["start"] - 0.03, 0.14), 1.2)
    sc = 0.9 + 0.1 * k
    if sc < 0.999:
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
    m = im.getchannel("A")
    a = clamp(ramp(t, cur["start"] - 0.03, 0.1))
    if a < 1:
        m = m.point(lambda v: int(v * a))
    cy = 1350
    frame.paste(im, (int(540 - im.width / 2), int(cy - im.height / 2)), m)


# ---------------------------------------------------------------- Frame-Rendering
G = {}


def scene_bounds(tl):
    T = {c["id"]: c["start"] for c in tl["cues"]}
    starts = [0.0] + [T[sc[1]] - 0.25 for sc in EP.SCENES[1:]]
    ends = starts[1:] + [tl["total"] + 1]
    return [(sc[0], s0, s1) for sc, s0, s1 in zip(EP.SCENES, starts, ends)]


def init_worker(tl):
    G["tl"] = tl
    G["ctx"] = Ctx(tl)
    G["bounds"] = scene_bounds(tl)


def draw_scene(name, t, s0, s1):
    img = Image.new("RGB", (W2, H2))
    cv = Cv(img)
    SCENE_FUNCS[name](cv, t, G["ctx"], s0, s1)
    return img.reduce(S)


def render_frame(i):
    t = i / FPS
    bounds = G["bounds"]
    idx = 0
    for k, (_, s0, s1) in enumerate(bounds):
        if s0 <= t:
            idx = k
    name, s0, s1 = bounds[idx]
    frame = draw_scene(name, t, s0, s1)
    if idx > 0 and t < s0 + XFADE:
        pname, p0, p1 = bounds[idx - 1]
        prev = draw_scene(pname, t, p0, p1)
        frame = Image.blend(prev, frame, smooth((t - s0) / XFADE))
    draw_caption(frame, G["tl"], t)
    # kein Einblenden: Bild 1 ist sofort voll sichtbar (Hook); nur am Ende sanft ausblenden
    fade = 1 - ramp(t, G["tl"]["total"] - 0.4, 0.4)
    if fade < 1:
        frame = Image.blend(Image.new("RGB", frame.size, (0, 0, 0)), frame, fade)
    return frame.tobytes()


def build_timeline():
    if os.path.exists(VO_PATH):
        tl = TL.aligned(VO_PATH)
    else:
        tl = TL.planned()
    return tl


def encode(tl, path, audio_wav, workers):
    n = int(math.ceil(tl["total"] * FPS))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{n / FPS:.3f}", "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers, initializer=init_worker, initargs=(tl,)) as pool:
        for k, buf in enumerate(pool.imap(render_frame, range(n), chunksize=4)):
            p.stdin.write(buf)
            if k % 150 == 0:
                print(f"  frame {k}/{n}", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg failed")


def mux_voiceover(tl, video, audio_wav, vo, path):
    """Voiceover (unverändertes Tempo) + Soundeffekte unter das fertige Video legen."""
    off_ms = int(round(tl["audio_offset"] * 1000))
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-i", audio_wav, "-i", vo,
           "-filter_complex",
           f"[2:a]aresample=48000,aformat=channel_layouts=stereo,adelay={off_ms}|{off_ms}[vo];"
           f"[1:a]volume=0.40[fx];[vo][fx]amix=inputs=2:duration=longest:normalize=0,"
           f"alimiter=limit=0.95[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{tl['total']:.3f}", "-movflags", "+faststart", path]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", type=float, nargs="*", help="nur Standbilder bei diesen Sekunden")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    tl = build_timeline()
    if args.still:
        init_worker(tl)
        os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
        for s in args.still:
            buf = render_frame(int(round(s * FPS)))
            Image.frombytes("RGB", (W, H), buf).save(os.path.join(OUT, "stills", f"still_{s:05.1f}.png"))
        return

    print(f"Timing-Modus: {tl['mode']}, Länge {tl['total']:.1f} s")
    if tl["mode"] == "voiceover" and tl["voiceover_duration"] < 60:
        TL.save(tl, os.path.join(OUT, "timeline_voiceover_REJECTED.json"))
        print(f"FEHLER: Voiceover ist nur {tl['voiceover_duration']:.1f} s lang (< 60 s). "
              "Der Sprechertext muss länger werden – final.mp4 wird nicht exportiert.")
        tl = TL.planned()
        vo_ok = False
    else:
        vo_ok = tl["mode"] == "voiceover"

    TL.save(tl, os.path.join(OUT, "timeline.json"))
    TL.write_srt(tl, os.path.join(OUT, "captions.srt"))
    import make_docs
    make_docs.write_scene_plan(tl, scene_bounds(tl), os.path.join(OUT, "scene_plan.md"))

    wav = os.path.join(OUT, "sfx_track.wav")
    sfx.build_track(tl, EP.SFX, wav)
    print("SFX-Spur fertig")
    encode(tl, os.path.join(OUT, "animation_preview.mp4"), wav, args.workers)
    print("animation_preview.mp4 fertig")
    if vo_ok:
        mux_voiceover(tl, os.path.join(OUT, "animation_preview.mp4"), wav, VO_PATH, os.path.join(OUT, "final.mp4"))
        print("final.mp4 fertig")


if __name__ == "__main__":
    main()
