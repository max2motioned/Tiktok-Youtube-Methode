# Everyday Unpacked – Animations-Pipeline

Folge 01: **Why airplane windows have a tiny hole** (Englisch, 9:16, 1080 × 1920, 30 fps)
Aktueller Stand: `final.mp4` mit ElevenLabs-Voiceover (66,4 s Stimme → 69,1 s Video), −14 LUFS.

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
Empfohlen für Voiceover-Folgen: `pip install pocketsphinx` (Wort-genaue Ausrichtung, läuft offline, Modell ist im Paket).

## Neu rendern
```bash
python3 project/render.py
```
Optional: `--workers 8` (Parallelität), `--still 12.5 40` (nur Standbilder nach `output/stills/` zum Prüfen).

## Mit ElevenLabs-Voiceover
1. Text aus `output/voiceover.txt` in ElevenLabs vertonen, als `input/voiceover.mp3` speichern.
2. `python3 project/render.py` erneut ausführen.
   - Mit `pocketsphinx` wird das Skript Wort für Wort an die Aufnahme ausgerichtet (exakte Untertitel/Szenenwechsel).
     Ohne das Paket – oder wenn ein Wort unbekannt ist – werden die Sprechpausen (ffmpeg `silencedetect`) den
     Cue-Grenzen zugeordnet. Unbekannte Wörter in `PRONUNCIATIONS` (episode.py) eintragen.
   - Das Tempo der Stimme wird nie verändert. Animationen und Soundeffekte folgen automatisch den Cues.
   - Ergebnis: `animation_preview.mp4` (ohne Stimme, echtes Timing) und `final.mp4` (Stimme + Soundeffekte,
     auf ca. −14 LUFS / −1,5 dBTP gebracht).
   - Ist die Datei kürzer als 60 s, wird **kein** `final.mp4` erzeugt; das Skript meldet, dass der Text länger sein muss.
   - Videolänge = Voiceover + 0,35 s Vorlauf + 2,4 s Endkarte. Für 75–85 s braucht die Stimme 72–82 s
     (bei diesem Sprecher ≈ 3 Wörter/s → ca. 215–240 Wörter).
3. Kontrolle: `output/timeline.json` zeigt `alignment` (verwendete Methode) und alle Cue-Zeiten.

## Text ändern
In `project/episode.py` die `CUES` anpassen (ein Cue = eine Untertitelzeile, `*Wort*` = gelb hervorgehoben).
Animationen sind an Cue-IDs gebunden – IDs beibehalten oder in `render.py` mitändern. `output/voiceover.txt`
danach ebenfalls aktualisieren.

## Safe Zones
Wichtige Texte liegen zwischen y ≈ 220 und 1430 px; Untertitel mittig bei y = 1350 px. Oben (Tabs/Status) und
unten (Beschreibung/Buttons von TikTok & Shorts) bleibt frei.
