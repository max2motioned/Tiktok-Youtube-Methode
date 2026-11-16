"""Timing: geplantes Timing (ohne Voiceover) oder Ausrichtung an input/voiceover.mp3.

Ohne Voiceover: Sprechdauer aus Wortzahl, Ziel-Gesamtlänge TARGET_TOTAL.
Mit Voiceover:  1. Wort-genaue Ausrichtung des Skripts an die Aufnahme (pocketsphinx, offline, optional).
                2. Rückfall: Sprechpausen (ffmpeg silencedetect) per dynamischer Programmierung den
                   Cue-Grenzen zuordnen, Cues dazwischen nach Wortzahl verteilen.
                Die Sprechgeschwindigkeit wird NIE verändert.
"""
import json
import re
import subprocess

from episode import CUES, PRONUNCIATIONS

LEAD_IN = 0.35         # Sekunden vor dem ersten Wort (Pop auf dem ersten Bild)
TAIL = 1.2             # nach dem letzten Wort: kurze Frage-Karte + Loop-Zoom zurück zum Anfang
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
    for c in cues:
        c["words"] = even_word_times(c)
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


SKIP_BOUNDARY = {"c": 0.6, "s": 3.0, "p": 4.0}  # Kosten, wenn eine Cue-Grenze keine Pause bekommt
SKIP_PAUSE = 1.0                                  # Kosten für eine Pause mitten in einem Cue


def match_pauses(inner, speech_start, speech_end):
    """Ordnet erkannte Sprechpausen den Cue-Grenzen zu (dynamische Programmierung).

    Bewertet jeden Abschnitt zwischen zwei Ankern danach, wie gut seine Dauer zum Wortanteil passt
    (gleichmäßiges Sprechtempo), plus Strafkosten für übersprungene Grenzen/Pausen.
    Rückgabe: {cue_index: (pause_start, pause_end)} = Ende von Cue i / Start von Cue i+1.
    """
    M = len(CUES) - 1                        # Grenzen zwischen Cues
    wcum = [0]
    for _, t, _ in CUES:
        wcum.append(wcum[-1] + words(t))
    wcum[M + 1] = wcum[-1]
    rate = (speech_end - speech_start) / wcum[-1]
    P = [(speech_start, speech_start)] + list(inner) + [(speech_end, speech_end)]
    N = len(inner)
    mid = [(a + b) / 2 for a, b in P]
    skipb = [0.0] + [SKIP_BOUNDARY[CUES[k][2]] for k in range(M)] + [0.0]
    skipb_cum = [0.0]
    for v in skipb:
        skipb_cum.append(skipb_cum[-1] + v)

    def seg(b0, j0, b1, j1):
        d = (wcum[b1] - wcum[b0]) * rate
        act = mid[j1] - mid[j0]
        cost = ((act - d) / (0.18 * d + 0.25)) ** 2
        cost += skipb_cum[b1] - skipb_cum[b0 + 1]     # Grenzen dazwischen ohne Pause
        cost += SKIP_PAUSE * (j1 - j0 - 1)            # Pausen dazwischen ohne Grenze
        return cost

    INF = float("inf")
    best = {(0, 0): (0.0, None)}
    states = [(b, j) for b in range(1, M + 1) for j in range(1, N + 1)] + [(M + 1, N + 1)]
    for b, j in states:
        cand = (INF, None)
        for (b0, j0), (c0, _) in best.items():
            if b0 < b and j0 < j:
                c = c0 + seg(b0, j0, b, j)
                if c < cand[0]:
                    cand = (c, (b0, j0))
        if cand[1] is not None:
            best[(b, j)] = cand
    bounds = {}
    node = best[(M + 1, N + 1)][1]
    while node and node != (0, 0):
        b, j = node
        bounds[b - 1] = P[j]
        node = best[node][1]
    return bounds


def norm_words(text):
    t = re.sub(r"[^a-z' ]", " ", clean(text).lower())
    return t.split()


def forced_align(vo_path):
    """Wort-genaue Ausrichtung des bekannten Skripts an die Aufnahme (pocketsphinx, offline).

    Gibt Liste (start, end) je Cue in Audio-Sekunden zurück oder None, wenn nicht möglich.
    """
    try:
        from pocketsphinx import Decoder
    except ImportError:
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", vo_path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    per_cue = [norm_words(t) for _, t, _ in CUES]
    try:
        d = Decoder(samprate=16000, bestpath=False, loglevel="FATAL")
        for w, ph in PRONUNCIATIONS.items():
            if d.lookup_word(w) is None:
                d.add_word(w, ph, True)
        d.set_align_text(" ".join(w for ws in per_cue for w in ws))
        d.start_utt()
        d.process_raw(raw, full_utt=True)
        d.end_utt()
        segs = [(s.start_frame / 100, s.end_frame / 100) for s in d.seg()
                if not s.word.startswith("<") and s.word != "[NOISE]"]
    except Exception as e:  # unbekanntes Wort o. Ä. -> Rückfall auf Pausen-Methode
        print(f"Wort-Ausrichtung nicht möglich ({e}); nutze Pausen-Methode.")
        return None
    if len(segs) != sum(len(ws) for ws in per_cue):
        return None
    out, k = [], 0
    for ws in per_cue:
        out.append(segs[k:k + len(ws)])
        k += len(ws)
    return out


def caption_word_times(text, token_times):
    """Erkannte Token-Zeiten auf die sichtbaren Untertitel-Wörter (Leerzeichen-getrennt) abbilden."""
    res, k, last = [], 0, token_times[0][0]
    for wd in clean(text).split():
        n = len(norm_words(wd))
        if n == 0:
            res.append([round(last, 3), round(last, 3)])
            continue
        a, b = token_times[k][0], token_times[k + n - 1][1]
        res.append([round(a, 3), round(b, 3)])
        k += n
        last = b
    return res


def even_word_times(cue):
    """Wörter gleichmäßig (nach Zeichenzahl) über die Cue-Dauer verteilen."""
    ws = clean(cue["text"]).split()
    lens = [len(w) + 2 for w in ws]
    tot = sum(lens)
    t, d, out = cue["start"], cue["end"] - cue["start"], []
    for n in lens:
        out.append([round(t, 3), round(t + d * n / tot, 3)])
        t += d * n / tot
    return out


def aligned(vo_path):
    dur = probe_duration(vo_path)
    sil = detect_silences(vo_path)
    speech_start = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    speech_end = sil[-1][0] if sil and sil[-1][1] >= dur - 0.05 else dur
    inner = [(a, b) for a, b in sil if a > speech_start + 0.05 and b < speech_end - 0.05]

    # 1. Wahl: Wort-Ausrichtung; Rückfall: Sprechpausen den Cue-Grenzen zuordnen
    words_al = forced_align(vo_path)
    if words_al:
        cues = [{"id": cid, "text": text, "start": round(tt[0][0], 3), "end": round(tt[-1][1], 3),
                 "words": caption_word_times(text, tt)}
                for (cid, text, _), tt in zip(CUES, words_al)]
        method, bounds = "forced alignment (pocketsphinx, word level)", {}
    else:
        method = "pause matching (ffmpeg silencedetect)"
        bounds = match_pauses(inner, speech_start, speech_end)
        cues = pause_cues(bounds, speech_start, speech_end)
    offset = LEAD_IN  # Audio startet nach dem Vorlauf
    for c in cues:
        c["start"] = round(c["start"] + offset, 3)
        c["end"] = round(c["end"] + offset, 3)
        if "words" in c:
            c["words"] = [[round(a + offset, 3), round(b + offset, 3)] for a, b in c["words"]]
        else:
            c["words"] = even_word_times(c)
    total = max(dur + offset, cues[-1]["end"]) + TAIL
    return {"mode": "voiceover", "alignment": method, "voiceover_duration": round(dur, 3), "total": round(total, 3),
            "audio_offset": offset, "matched_pauses": len(bounds), "detected_pauses": len(inner),
            "cues": cues}


def pause_cues(bounds, speech_start, speech_end):
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

    return cues


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
