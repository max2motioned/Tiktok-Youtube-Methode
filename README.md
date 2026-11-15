# Everyday Unpacked – Animations-Pipeline

Folge 01: **Why airplane windows have a tiny hole** (Englisch, 9:16, 1080 × 1920, 30 fps, ≈ 82 s)

## Ordner
| Pfad | Inhalt |
|---|---|
| `project/episode.py` | **Hier bearbeiten:** Sprechertext-Cues, Szenen, Soundeffekte, Themen-Tags |
| `project/render.py` | Zeichnet alle Szenen (PIL, 2×-Supersampling) und rendert über ffmpeg |
| `project/timeline.py` | Geplantes Timing bzw. Ausrichtung am echten Voiceover |
| `project/sfx.py` | Selbst synthetisierte Soundeffekte (keine fremden Samples/Musik) |
| `project/make_docs.py` | Erzeugt `output/scene_plan.md` passend zum aktuellen Timing |
| `project/assets/fonts/` | Inter (SIL OFL 1.1, Lizenz liegt bei) |
| `output/` | Ergebnisse: `voiceover.txt`, `scene_plan.md`, `captions.srt`, `social_caption.txt`, `sources.md`, `animation_preview.mp4` (+ `final.mp4`, `timeline.json`) |
| `episodes.md` | Übersicht bereits produzierter Themen |

## Voraussetzungen
Python 3.10+, `pip install pillow numpy`, ffmpeg/ffprobe im PATH.

## Neu rendern
```bash
python3 project/render.py
```
Optional: `--workers 8` (Parallelität), `--still 12.5 40` (nur Standbilder nach `output/stills/` zum Prüfen).

## Mit ElevenLabs-Voiceover
1. Text aus `output/voiceover.txt` in ElevenLabs vertonen, als `input/voiceover.mp3` speichern.
2. `python3 project/render.py` erneut ausführen.
   - Dauer und Sprechpausen der Datei werden gemessen (ffmpeg `silencedetect`); Szenenwechsel, Animationen,
     Soundeffekte und Untertitel folgen automatisch den Satzgrenzen. Das Tempo der Stimme wird nicht verändert.
   - Ergebnis: `animation_preview.mp4` (ohne Stimme, neues Timing) und `final.mp4` (Stimme + Soundeffekte).
   - Ist die Datei kürzer als 60 s, wird **kein** `final.mp4` erzeugt; das Skript meldet, dass der Text länger sein muss.
3. Kontrolle: `output/timeline.json` zeigt `matched_pauses` (gefundene Satzpausen). Liegen Untertitel daneben,
   in `project/timeline.py` `detect_silences(noise_db=…, min_dur=…)` anpassen.

## Text ändern
In `project/episode.py` die `CUES` anpassen (ein Cue = eine Untertitelzeile, `*Wort*` = gelb hervorgehoben).
Animationen sind an Cue-IDs gebunden – IDs beibehalten oder in `render.py` mitändern. `output/voiceover.txt`
danach ebenfalls aktualisieren.

## Safe Zones
Wichtige Texte liegen zwischen y ≈ 220 und 1430 px; Untertitel mittig bei y = 1350 px. Oben (Tabs/Status) und
unten (Beschreibung/Buttons von TikTok & Shorts) bleibt frei.
