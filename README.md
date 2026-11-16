# Everyday Unpacked – Animations-Pipeline

Englischsprachige Erklär-Shorts (9:16, 1080 × 1920, 30 fps) für TikTok und YouTube Shorts.
Jede Folge endet mit einer kurzen Frage und läuft als **Endlos-Loop** zurück in Bild 1.

| Folge | Ordner | Stand |
|---|---|---|
| 01 – Why airplane windows have a tiny hole | `episodes/01-airplane-window-hole/` | `final.mp4` mit Voiceover (69,1 s) |
| 02 – How popcorn pops | `episodes/02-popcorn/` | Vorschau (82 s, geplantes Timing) – wartet auf Voiceover |

Übersicht bereits verwendeter Themen: `episodes.md`.

## Aufbau
| Pfad | Inhalt |
|---|---|
| `project/render.py` | Startskript: `python3 project/render.py <folgen-ordner>` |
| `project/engine.py` | Gemeinsamer Motor: Zeichenfläche, Texte, Untertitel, Loop-Übergang, Encoding, Voiceover-Mix |
| `project/timeline.py` | Geplantes Timing bzw. Ausrichtung am echten Voiceover |
| `project/sfx.py` | Selbst synthetisierte Soundeffekte (keine fremden Samples, keine Musik) |
| `project/make_docs.py` | Erzeugt `scene_plan.md` passend zum aktuellen Timing |
| `project/assets/fonts/` | Inter (SIL OFL 1.1, Lizenz liegt bei) |
| `episodes/<nr-thema>/episode.py` | **Inhalt der Folge:** Sprechertext-Cues, Szenen, Soundeffekte, Themen-Tags |
| `episodes/<nr-thema>/scenes.py` | Zeichnungen/Animationen der Folge |
| `episodes/<nr-thema>/input/voiceover.mp3` | ElevenLabs-Voiceover (optional) |
| `episodes/<nr-thema>/output/` | `voiceover.txt`, `scene_plan.md`, `captions.srt`, `social_caption.txt`, `sources.md`, `animation_preview.mp4`, `final.mp4`, `timeline.json` |

## Voraussetzungen
Python 3.10+, `pip install pillow numpy`, ffmpeg/ffprobe im PATH.
Empfohlen für Voiceover-Folgen: `pip install pocketsphinx` (Wort-genaue Ausrichtung, offline, Modell ist im Paket).

## Rendern
```bash
python3 project/render.py episodes/02-popcorn
```
Optional: `--workers 8` (Parallelität), `--still 12.5 40` (nur Standbilder nach `output/stills/` zum Prüfen).

## Mit ElevenLabs-Voiceover
1. Text aus `output/voiceover.txt` der Folge vertonen und als `input/voiceover.mp3` im Folgen-Ordner speichern.
2. Rendern wie oben.
   - Mit `pocketsphinx` wird das Skript Wort für Wort an die Aufnahme ausgerichtet. Ohne das Paket – oder wenn
     ein Wort unbekannt ist – werden die Sprechpausen (ffmpeg `silencedetect`) den Cue-Grenzen zugeordnet.
     Unbekannte Wörter in `PRONUNCIATIONS` (episode.py) eintragen.
   - Das Tempo der Stimme wird nie verändert. Animationen, Untertitel und Soundeffekte folgen automatisch.
   - Ergebnis: `animation_preview.mp4` (ohne Stimme) und `final.mp4` (Stimme + leise Soundeffekte, ca. −14 LUFS).
   - Ist die Aufnahme kürzer als 60 s, wird **kein** `final.mp4` erzeugt; das Skript meldet, dass der Text länger sein muss.
   - Videolänge = Voiceover + 0,35 s Vorlauf + 1,2 s Ende (Frage-Karte + Loop-Zoom). Für 75–85 s braucht die
     Stimme etwa 73–83 s (Sprecher „Adam“ ≈ 2,8 Wörter/s → ca. 205–235 Wörter).

## Neue Folge anlegen
1. Thema wählen, das noch nicht in `episodes.md` steht.
2. Ordner `episodes/<nr>-<thema>/` mit `episode.py` (Cues, Szenen, SFX) und `scenes.py` anlegen – am einfachsten
   eine bestehende Folge als Vorlage kopieren.
3. Regeln für `scenes.py`: `SCENE_FUNCS` mit einer Funktion pro Szene aus `SCENES`. Die **erste Szene** muss
   für `t < 0` den Zoom „zurück auf Bild 1“ zeichnen (Loop); die letzte Szene endet mit der Frage-Karte
   (`endcard_sprite()`), die in den letzten `LOOP_ZOOM` Sekunden verschwindet.
4. `python3 project/render.py episodes/<nr>-<thema> --still …` zum Prüfen, danach komplett rendern.

## Safe Zones
Wichtige Texte liegen zwischen y ≈ 220 und 1430 px; Untertitel mittig bei y = 1350 px. Oben (Tabs/Status) und
unten (Beschreibung/Buttons von TikTok & Shorts) bleibt frei. Kein Kanalname/Handle im Video.
