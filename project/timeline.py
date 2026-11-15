"""Timing: geplantes Timing (ohne Voiceover) oder Ausrichtung an input/voiceover.mp3.

Ohne Voiceover: Sprechdauer aus Wortzahl, Ziel-Gesamtlänge TARGET_TOTAL.
Mit Voiceover:  Dauer + Pausen (ffmpeg silencedetect) der echten Datei. Satzgrenzen werden auf
                die nächstgelegene Sprechpause gelegt, Cues innerhalb eines Satzes nach Wortzahl verteilt.
                Die Sprechgeschwindigkeit wird NIE verändert.
"""
import json
import re
import subprocess

from episode import CUES

LEAD_IN = 0.35         # Sekunden vor dem ersten Wort (Pop auf dem ersten Bild)
TAIL = 2.4             # Endkarte nach dem letzten Wort
TARGET_TOTAL = 82.0    # geplante Länge ohne Voiceover (75–85 s gefordert)
PAUSES = {"c": 0.12, "s": 0.38, "p": 0.75}


def clean(text):
    return text.replace("*", "")


def words(text):
    return len(clean(text).split())


def planned():
    """Geplante Zeiten ohne Audiodatei."""
    n_words = sum(words(t) for _, t, _ in CUES)
    pause_total = sum(PAUSES[p] for _, _, p in CUES[:-1])
    speech = TARGET_TOTAL - LEAD_IN - TAIL - pause_total
    sec_per_word = speech / n_words
    t = LEAD_IN
    cues = []
    for cid, text, p in CUES:
        d = words(text) * sec_per_word
        cues.append({"id": cid, "text": text, "start": round(t, 3), "end": round(t + d, 3)})
        t += d + PAUSES[p]
    total = cues[-1]["end"] + TAIL
    return {"mode": "planned", "total": round(total, 3), "speech_rate_wpm": round(60 / sec_per_word, 1),
            "audio_offset": 0.0, "cues": cues}


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def detect_silences(path, noise_db=-35, min_dur=0.18):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                          f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
                         capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out.stderr)]
    return list(zip(starts, ends))


def aligned(vo_path):
    dur = probe_duration(vo_path)
    sil = detect_silences(vo_path)
    speech_start = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    speech_end = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 else dur
    inner = [(a, b) for a, b in sil if a > speech_start + 0.05 and b < speech_end - 0.05]

    # Geplante Struktur auf echte Sprechdauer skalieren
    plan = planned()
    p0 = plan["cues"][0]["start"]
    p1 = plan["cues"][-1]["end"]
    k = (speech_end - speech_start) / (p1 - p0)
    est = [(speech_start + (c["start"] - p0) * k, speech_start + (c["end"] - p0) * k) for c in plan["cues"]]

    # Satz-/Absatzgrenzen auf echte Pausen legen (monoton, je Pause nur einmal)
    bounds = {}  # index i -> (end_of_cue_i, start_of_cue_i+1)
    used = set()
    last = speech_start
    for i, (_, _, p) in enumerate(CUES[:-1]):
        if p not in ("s", "p"):
            continue
        target = (est[i][1] + est[i + 1][0]) / 2
        best = None
        for j, (a, b) in enumerate(inner):
            if j in used or a <= last:
                continue
            dist = abs((a + b) / 2 - target)
            if dist < 2.5 * max(k, 0.5) and (best is None or dist < best[0]):
                best = (dist, j)
        if best:
            a, b = inner[best[1]]
            used.add(best[1])
            bounds[i] = (a, b)
            last = b

    # Anker: Start, Satzgrenzen, Ende -> Cues dazwischen nach Wortzahl verteilen
    anchors = [(-1, speech_start)] + [(i, None) for i in sorted(bounds)] + [(len(CUES) - 1, speech_end)]
    cues = []
    seg_start = speech_start
    first = 0
    for idx, _ in anchors[1:]:
        seg_end = bounds[idx][0] if idx in bounds else speech_end
        group = list(range(first, idx + 1))
        n = sum(words(CUES[g][1]) for g in group)
        small = 0.10 * (len(group) - 1)  # kleine Lücken innerhalb des Satzes
        rate = max(seg_end - seg_start - small, 0.1) / n
        t = seg_start
        for g in group:
            d = words(CUES[g][1]) * rate
            cues.append({"id": CUES[g][0], "text": CUES[g][1], "start": round(t, 3), "end": round(t + d, 3)})
            t += d + 0.10
        if idx in bounds:
            seg_start = bounds[idx][1]
        first = idx + 1

    offset = LEAD_IN  # Audio startet nach dem Vorlauf
    for c in cues:
        c["start"] = round(c["start"] + offset, 3)
        c["end"] = round(c["end"] + offset, 3)
    total = max(dur + offset, cues[-1]["end"]) + TAIL
    return {"mode": "voiceover", "voiceover_duration": round(dur, 3), "total": round(total, 3),
            "audio_offset": offset, "matched_pauses": len(bounds),
            "sentence_boundaries": sum(1 for _, _, p in CUES[:-1] if p in "sp"), "cues": cues}


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(tl, path):
    lines = []
    cues = tl["cues"]
    for i, c in enumerate(cues):
        end = c["end"] + 0.15
        if i + 1 < len(cues):
            end = min(end, cues[i + 1]["start"] - 0.02)
        lines += [str(i + 1), f"{srt_time(c['start'])} --> {srt_time(end)}", clean(c["text"]), ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def save(tl, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tl, f, indent=2, ensure_ascii=False)
