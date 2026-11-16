"""Everyday Unpacked – gemeinsamer Render-Motor für alle Folgen.

Wird über project/render.py gestartet (siehe README). Die Folge (episode.py + scenes.py) liegt in
episodes/<ordner>/ und wird vorher in sys.path eingetragen. Alle Grafiken werden per Code gezeichnet
(PIL, 2x-Supersampling), Sounds in sfx.py synthetisiert.
"""
import importlib
import math
import os
import re
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.append(HERE)

import episode as EP  # noqa: E402  (aus dem Folgen-Ordner)
import sfx  # noqa: E402
import timeline as TL  # noqa: E402

W, H, FPS = 1080, 1920, 30
S = 2                      # Supersampling
W2, H2 = W * S, H * S
EP_DIR = os.path.dirname(os.path.abspath(EP.__file__))
OUT = os.path.join(EP_DIR, "output")
VO_PATH = os.path.join(EP_DIR, "input", "voiceover.mp3")

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


# ---------------------------------------------------------------- Szenen-Kontext
class Ctx:
    def __init__(self, tl):
        self.T = {c["id"]: c["start"] for c in tl["cues"]}
        self.E = {c["id"]: c["end"] for c in tl["cues"]}
        self.total = tl["total"]


def cv_point(z, fx, fy, ty, x, y):
    return (x - fx) * z + 540, (y - fy) * z + ty


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


LOOP_ZOOM = 0.7   # Sekunden am Ende: Zoom ins Loch, mündet nahtlos in Bild 1
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
    G["funcs"] = importlib.import_module("scenes").SCENE_FUNCS
    G["tl"] = tl
    G["ctx"] = Ctx(tl)
    G["bounds"] = scene_bounds(tl)


def draw_scene(name, t, s0, s1):
    img = Image.new("RGB", (W2, H2))
    cv = Cv(img)
    G["funcs"][name](cv, t, G["ctx"], s0, s1)
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
    total = G["tl"]["total"]
    if t >= total - LOOP_ZOOM:
        # Endlos-Loop: Hook-Szene "vor" Sekunde 0 – das letzte Bild geht direkt in Bild 1 über
        first = bounds[0][0]   # erste Szene muss t < 0 als "Zoom zurück auf Bild 1" zeichnen
        hook = draw_scene(first, t - total, -LOOP_ZOOM, bounds[1][1])
        frame = Image.blend(frame, hook, smooth(ramp(t, total - LOOP_ZOOM, 0.22)))
    draw_caption(frame, G["tl"], t)
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


def measure_lufs(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    vals = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
    return float(vals[-1]) if vals else None


def mux_voiceover(tl, video, audio_wav, vo, path, target_lufs=-14.0):
    """Voiceover (unverändertes Tempo) + Soundeffekte unter das fertige Video legen, auf ~-14 LUFS bringen."""
    off_ms = int(round(tl["audio_offset"] * 1000))
    mix_wav = os.path.splitext(path)[0] + "_mix.wav"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", audio_wav, "-i", vo,
                    "-filter_complex",
                    f"[1:a]aresample=48000,aformat=channel_layouts=stereo,adelay={off_ms}|{off_ms}[vo];"
                    f"[0:a]volume=0.26[fx];[vo][fx]amix=inputs=2:duration=longest:normalize=0[a]",
                    "-map", "[a]", "-t", f"{tl['total']:.3f}", "-c:a", "pcm_s16le", mix_wav], check=True)
    lufs = measure_lufs(mix_wav)
    gain = 0.0 if lufs is None else max(-6.0, min(12.0, target_lufs - lufs))
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-i", mix_wav,
                    "-af", f"volume={gain:.2f}dB,alimiter=limit=0.79:attack=1:release=60:level=disabled",
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{tl['total']:.3f}", "-movflags", "+faststart", path], check=True)
    os.remove(mix_wav)
    print(f"  Lautheit: {lufs} LUFS -> Gain {gain:+.1f} dB")


def main(args):
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
