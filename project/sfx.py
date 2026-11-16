"""Synthetische Soundeffekte (numpy) – keine fremden Samples, keine Musik mit Rechtefragen.

Alle Klänge werden hier per Code erzeugt und an Cue-Zeiten gemischt.
"""
import wave

import numpy as np

SR = 48000
RNG = np.random.default_rng(7)


def _t(d):
    return np.arange(int(SR * d)) / SR


def _env(n, attack=0.005, release=0.1):
    e = np.ones(n)
    a = max(1, int(SR * attack))
    r = max(1, int(SR * release))
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def _lowpass(x, cutoff):
    """One-pole Tiefpass; cutoff darf ein Array (zeitvariabel) sein."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _noise(d):
    return RNG.uniform(-1, 1, int(SR * d))


def _bandnoise(d, lo, hi):
    x = _noise(d)
    return _lowpass(x, hi) - _lowpass(x, lo)


def _norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def whoosh(d=0.55, up=True):
    n = int(SR * d)
    p = np.linspace(0, 1, n)
    cutoff = 300 + 4200 * (np.sin(np.pi * p) if up else (1 - p))
    x = _lowpass(_noise(d), cutoff)
    x = x - _lowpass(x, 150)
    return _norm(x * np.sin(np.pi * p) ** 1.5, 0.9)


def whoosh_in():
    n = int(SR * 0.7)
    p = np.linspace(0, 1, n)
    x = _lowpass(_noise(0.7), 400 + 5000 * p ** 2)
    return _norm(x * p ** 2 * _env(n, 0.01, 0.06), 0.9)


def pop(f0=520, f1=140, d=0.12):
    t = _t(d)
    f = f1 + (f0 - f1) * np.exp(-t * 40)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return _norm(np.sin(ph) * np.exp(-t * 28) * _env(len(t), 0.002, 0.02), 0.95)


def tick():
    t = _t(0.05)
    x = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 120) + 0.3 * _noise(0.05) * np.exp(-t * 200)
    return _norm(x, 0.8)


def tap():
    t = _t(0.12)
    x = np.sin(2 * np.pi * 900 * t) * np.exp(-t * 60) + 0.6 * _lowpass(_noise(0.12), 3000) * np.exp(-t * 90)
    return _norm(x, 0.9)


def chime(freqs, d=1.6, decay=3.0):
    t = _t(d)
    x = sum(np.sin(2 * np.pi * f * t) * (0.6 ** i) for i, f in enumerate(freqs))
    return _norm(x * np.exp(-t * decay) * _env(len(t), 0.004, 0.2), 0.8)


def cabin_chime():
    # generischer Zwei-Ton-Gong (selbst synthetisiert)
    a = chime([659.25, 1318.5, 1977.8], 1.4, 2.6)
    b = chime([523.25, 1046.5, 1569.8], 1.6, 2.4)
    out = np.zeros(int(SR * 2.3))
    out[:len(a)] += a
    out[int(SR * 0.55):int(SR * 0.55) + len(b)] += b
    return _norm(out, 0.8)


def ding():
    return chime([1046.5, 2093, 3140], 1.1, 4.0)


def sparkle():
    out = np.zeros(int(SR * 0.7))
    for i, f in enumerate([1568, 2093, 2637, 3136]):
        c = chime([f, f * 2], 0.4, 9)
        s = int(SR * 0.06 * i)
        out[s:s + len(c)] += c * 0.6
    return _norm(out, 0.7)


def shimmer():
    t = _t(0.9)
    x = sum(np.sin(2 * np.pi * f * t + i) for i, f in enumerate([1200, 1500, 1800, 2400]))
    x *= (0.5 + 0.5 * np.sin(2 * np.pi * 14 * t)) * np.sin(np.pi * t / 0.9)
    return _norm(x, 0.6)


def buzz():
    t = _t(0.28)
    x = np.sign(np.sin(2 * np.pi * 150 * t)) * 0.5 + np.sin(2 * np.pi * 300 * t) * 0.5
    x = _lowpass(x, 1800)
    return _norm(x * _env(len(t), 0.005, 0.06), 0.7)


def thud():
    t = _t(0.45)
    f = 45 + 90 * np.exp(-t * 18)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    x += 0.4 * _lowpass(_noise(0.45), 600) * np.exp(-t * 25)
    return _norm(x, 1.0)


def stamp():
    out = thud() * 0.9
    c = tap()
    out[:len(c)] += c * 0.6
    return _norm(out, 1.0)


def split():
    a = whoosh(0.4)
    out = np.zeros(int(SR * 0.6))
    out[:len(a)] += a * 0.6
    for i in range(3):
        p = pop(700 + 150 * i, 220, 0.1)
        s = int(SR * (0.05 + 0.09 * i))
        out[s:s + len(p)] += p * 0.7
    return _norm(out, 0.9)


def rise():
    d = 1.6
    t = _t(d)
    f = 110 * 2 ** (t / d * 1.5)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    x = x * 0.6 + 0.4 * _lowpass(_noise(d), 800 + 1500 * t / d)
    return _norm(x * np.sin(np.pi * t / d) ** 0.8, 0.7)


def air_hiss(d=1.4):
    x = _bandnoise(d, 900, 6000)
    p = np.linspace(0, 1, len(x))
    return _norm(x * np.sin(np.pi * p) ** 0.7, 0.6)


def push():
    t = _t(0.6)
    f = 70 + 40 * t
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.6)
    x += 0.5 * _lowpass(_noise(0.6), 400) * np.sin(np.pi * t / 0.6)
    return _norm(x, 0.9)


def balance():
    a = chime([784, 1568], 0.6, 6)
    b = chime([784, 1568], 0.8, 5)
    out = np.zeros(int(SR * 1.0))
    out[:len(a)] += a
    out[int(SR * 0.18):int(SR * 0.18) + len(b)] += b
    return _norm(out, 0.7)


def shield():
    a = chime([523.25, 659.25, 783.99, 1046.5], 1.4, 2.5)
    sh = shimmer()
    a[:len(sh)] += 0.3 * sh[:len(a)]
    return _norm(a, 0.8)


def wipe():
    n = int(SR * 0.6)
    p = np.linspace(0, 1, n)
    x = _lowpass(_noise(0.6), 2500 + 3000 * p) - _lowpass(_noise(0.6), 600)
    return _norm(x * np.sin(np.pi * p), 0.6)


def outro_chime():
    out = np.zeros(int(SR * 2.0))
    for i, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        c = chime([f, f * 2], 1.4, 3)
        s = int(SR * 0.11 * i)
        out[s:s + len(c)] += c
    return _norm(out, 0.8)


def sizzle(d=1.4):
    x = _bandnoise(d, 2500, 9000)
    n = len(x)
    crack = (RNG.uniform(0, 1, n) > 0.9993) * RNG.uniform(0.4, 1.0, n)
    crack = np.convolve(crack, np.exp(-np.arange(200) / 25), mode="same")
    p = np.linspace(0, 1, n)
    return _norm((x * 0.5 + crack * RNG.uniform(-1, 1, n)) * np.sin(np.pi * p) ** 0.5, 0.6)


def flame(d=1.2):
    x = _lowpass(_noise(d), 700) - _lowpass(_noise(d), 90)
    t = _t(d)
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 7 * t)
    return _norm(x * np.sin(np.pi * t / d) ** 0.6, 0.6)


def drip():
    t = _t(0.25)
    f = 900 + 1400 * (1 - np.exp(-t * 30))
    return _norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 22), 0.7)


def crackle(d=0.8):
    n = int(SR * d)
    out = np.zeros(n)
    for i in range(14):
        s = int(RNG.uniform(0, n - 3000))
        c = tick() * RNG.uniform(0.3, 1.0)
        out[s:s + len(c)] += c
    return _norm(out, 0.8)


def burst():
    out = np.zeros(int(SR * 0.9))
    th = thud()
    out[:len(th)] += th * 0.8
    p = pop(1100, 180, 0.14)
    out[:len(p)] += p
    hs = air_hiss(0.6)
    out[int(SR * 0.02):int(SR * 0.02) + len(hs)] += hs * 0.5
    return _norm(out, 1.0)


def projector(d=1.6):
    t = _t(d)
    clicks = np.zeros(len(t))
    step = int(SR / 24)
    for i in range(0, len(t) - 400, step):
        c = tick()[:400] * 0.5
        clicks[i:i + len(c)] += c
    hum = 0.15 * np.sin(2 * np.pi * 120 * t)
    return _norm((clicks + hum) * np.sin(np.pi * t / d) ** 0.3, 0.6)


def spring():
    t = _t(0.45)
    f = 220 + 900 * t / 0.45
    x = np.sin(2 * np.pi * np.cumsum(f) / SR + 3 * np.sin(2 * np.pi * 18 * t))
    return _norm(x * np.exp(-t * 4) * _env(len(t), 0.005, 0.08), 0.7)


SOUNDS = {
    "sizzle": sizzle, "flame": flame, "drip": drip, "crackle": crackle, "burst": burst,
    "projector": projector, "spring": spring,
    "cabin_chime": cabin_chime, "whoosh": whoosh, "whoosh_in": whoosh_in, "pop": pop,
    "pop_high": lambda: pop(900, 300, 0.1), "sparkle": sparkle, "buzz": buzz, "stamp": stamp,
    "thud": thud, "split": split, "tick": tick, "tap": tap, "shimmer": shimmer, "rise": rise,
    "air_hiss": air_hiss, "push": push, "ding": ding, "balance": balance, "shield": shield,
    "wipe": wipe, "outro_chime": outro_chime,
}


def cabin_ambience(d):
    """Leises Kabinenrauschen als Klangbett (braunes Rauschen, tiefpassgefiltert)."""
    n = int(SR * d)
    spec = np.fft.rfft(RNG.normal(0, 1, n))
    f = np.fft.rfftfreq(n, 1 / SR)
    shape = 1 / np.maximum(f, 40) / (1 + (f / 450) ** 4)  # rotes Rauschen, Tiefpass ~450 Hz
    shape[f < 25] = 0
    x = np.fft.irfft(spec * shape, n)
    x = _norm(x, 1.0)
    return x  # FFT-Rauschen ist periodisch: Ende geht nahtlos in den Anfang über (Loop)


def build_track(timeline, sfx_events, path, ambience_gain=0.06):
    total = timeline["total"]
    n = int(SR * total)
    mix = np.zeros(n)
    mix[:int(SR * total)] += cabin_ambience(total)[:int(SR * total)] * ambience_gain
    starts = {c["id"]: c["start"] for c in timeline["cues"]}
    starts["_end"] = total  # für Effekte relativ zum Videoende (Loop-Übergang)
    cache = {}
    for cue, off, name, gain in sfx_events:
        if name not in cache:
            cache[name] = SOUNDS[name]()
        s = cache[name]
        i = max(0, int(SR * (starts[cue] + off)))
        j = min(n, i + len(s))
        mix[i:j] += s[:j - i] * gain * 0.5
        if i + len(s) > n:  # Überhang am Ende landet am Anfang (nahtloser Loop)
            rest = s[j - i:]
            mix[:len(rest)] += rest * gain * 0.5
    mix = mix[:int(SR * total)]
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)  # weicher Limiter
    mix = _norm(mix, 0.89)
    pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
