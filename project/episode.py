"""Folgen-Daten: Everyday Unpacked – Episode 01 "The Tiny Hole in Airplane Windows".

Das ist die zentrale, bearbeitbare Quelle:
  * CUES      -> Sprechertext, Untertitel und Timing-Anker (Reihenfolge = Sprechreihenfolge)
  * SCENES    -> welche Szene bei welchem Cue beginnt + Beschreibung für scene_plan.md
  * SFX       -> Soundeffekte, verankert an Cues (folgen automatisch dem echten Voiceover)

Wörter in *Sternchen* werden in den Untertiteln farbig hervorgehoben.
pause: Pause NACH dem Cue im geplanten Timing ("c" Komma, "s" Satzende, "p" Absatz).
"""

EPISODE_TITLE = "Why airplane windows have a tiny hole"

# (id, text, pause)
CUES = [
    ("hook1", "Every airplane window has a *tiny hole* in it.", "s"),
    ("hook2", "You've probably sat *right next to one*", "c"),
    ("hook3", "and *never noticed.*", "s"),
    ("nc1", "It's not a *crack,*", "c"),
    ("nc2", "and it's not a *defect.*", "s"),
    ("purp1", "It's there *on purpose,*", "c"),
    ("purp2", "and it quietly does *two jobs.*", "p"),
    ("ass1", "Most people assume a plane window", "c"),
    ("ass2", "is *one thick sheet.*", "s"),
    ("ass3", "It's actually *three.*", "p"),
    ("scr1", "The pane you can touch", "c"),
    ("scr2", "is just a *scratch shield.*", "s"),
    ("scr3", "It holds back *no pressure* at all.", "s"),
    ("pan1", "Behind it sit two strong *acrylic panes:*", "c"),
    ("pan2", "a *middle* one and an *outer* one.", "p"),
    ("alt1", "At *cruising altitude,*", "c"),
    ("alt2", "the air outside is *thin.*", "s"),
    ("alt3", "The air inside is kept much *denser,*", "c"),
    ("alt4", "so it *pushes outward* on every window", "c"),
    ("alt5", "with *hundreds of kilos* of force.", "p"),
    ("hole1", "That *tiny hole*", "c"),
    ("hole2", "goes through the *middle pane.*", "s"),
    ("flow1", "Cabin air *flows into the gap* behind it,", "c"),
    ("flow2", "so the middle pane feels", "c"),
    ("flow3", "*equal pressure* on both sides.", "s"),
    ("load1", "The *outer pane* carries the whole load,", "c"),
    ("load2", "and the middle pane waits,", "c"),
    ("load3", "unstressed, as a *backup.*", "p"),
    ("fog1", "Job number two:", "c"),
    ("fog2", "that same airflow lets *moisture escape,*", "c"),
    ("fog3", "so the gap stays clear of *fog and frost.*", "p"),
    ("end1", "One *tiny hole.*", "s"),
    ("end2", "A *spare window* and a *defogger.*", "s"),
    ("end3", "What everyday thing", "c"),
    ("end4", "should we *unpack next?*", "s"),
]

# (scene_id, start_cue, title, visual, motion, on-screen text)
SCENES = [
    ("hook", "hook1", "Hook – the tiny hole",
     "Frame 1 is an extreme close-up of the hole with clouds and wing behind it; then the full oval window "
     "on the cabin wall with a passenger (seen from behind) sitting right next to it.",
     "Snap punch-in on frame 1, amber rings pulse, arrow drops onto the hole; fast pull-back reveal, "
     "passenger slides in, then a slow push back toward the hole into the next scene.",
     "'EVERY PLANE WINDOW HAS THIS' (visible from frame 1) -> 'NEVER NOTICED?'"),
    ("purpose", "nc1", "Not a crack, not a defect",
     "Dark navy board with a small window icon and two 'suspect' cards (crack, defect).",
     "Cards slide up, red X marks stamp on, green 'ON PURPOSE' stamp drops on the window, two job badges pop up.",
     "'CRACK?' ✗  'DEFECT?' ✗  'ON PURPOSE'  'JOB 1 ?' 'JOB 2 ?'"),
    ("assume", "ass1", "Common assumption: one sheet",
     "Oblique 3D view of a single thick window slab.",
     "Slab wobbles, then splits along its depth into three separate panes that spread apart, numbers pop.",
     "'ONE THICK SHEET?' -> '3 PANES'"),
    ("layers", "scr1", "The three panes",
     "Side cross-section: warm cabin on the left, cold sky on the right, fuselage frame holding three panes.",
     "Fingertip taps the inner pane (ripple), labels draw in with leader lines, structural panes glow.",
     "'SCRATCH PANE – no pressure', 'MIDDLE', 'OUTER', 'ACRYLIC'"),
    ("pressure", "alt1", "Thin air outside, dense air inside",
     "Plane climbs to cruise altitude; then a split box: dense air particles inside, sparse outside.",
     "Altitude counter rolls to 35,000 ft; particles jiggle; big arrows push the pane outward; weight icon drops.",
     "'35,000 FT', 'OUTSIDE ≈ ¼ sea-level pressure', 'HUNDREDS OF KG OF FORCE'"),
    ("hole", "hole1", "The hole's real job",
     "Cross-section again, now with the breather hole in the middle pane.",
     "Zoom ring on the hole, air particles stream through into the gap, balance arrows on the middle pane, "
     "outer pane glows amber under load arrows, shield icon on the middle pane.",
     "'BREATHER HOLE', 'EQUAL PRESSURE', 'CARRIES THE LOAD', 'BACKUP'"),
    ("fog", "fog1", "Job two: no fog",
     "Front view of the window, glass fogs up and frost creeps in at the corners.",
     "Moisture droplets drift toward the hole and out; fog wipes clear; check mark pops.",
     "'JOB 2', 'NO FOG · NO FROST'"),
    ("outro", "end1", "Payoff + question",
     "Window front view with the hole, two result icons, then a short question card (no channel name, no follow ask).",
     "Icons pop in left/right, question card slides up, comment bubble bounces.",
     "'SPARE WINDOW' + 'DEFOGGER', 'WHAT SHOULD WE UNPACK NEXT?'"),
]

# Soundeffekte: (cue_id, offset_seconds, sound_name, gain)
SFX = [
    ("hook1", -0.33, "pop", 0.70),
    ("hook1", -0.28, "sparkle", 0.35),
    ("hook1", 0.15, "cabin_chime", 0.35),
    ("hook2", -0.05, "whoosh", 0.55),
    ("hook2", 0.45, "tap", 0.35),
    ("hook3", 0.05, "pop_high", 0.45),
    ("hook3", 0.55, "whoosh_in", 0.35),
    ("nc1", -0.15, "whoosh", 0.40),
    ("nc1", 0.45, "buzz", 0.35),
    ("nc2", 0.45, "buzz", 0.35),
    ("purp1", 0.25, "stamp", 0.75),
    ("purp2", 0.55, "pop", 0.55),
    ("purp2", 0.80, "pop_high", 0.55),
    ("ass1", -0.20, "whoosh", 0.45),
    ("ass2", 0.20, "thud", 0.50),
    ("ass3", 0.15, "split", 0.60),
    ("ass3", 0.35, "tick", 0.50),
    ("ass3", 0.60, "tick", 0.50),
    ("ass3", 0.85, "tick", 0.50),
    ("scr1", -0.20, "whoosh", 0.45),
    ("scr1", 0.75, "tap", 0.70),
    ("scr3", 0.10, "pop", 0.40),
    ("pan1", 0.40, "shimmer", 0.40),
    ("pan2", 0.20, "tick", 0.45),
    ("pan2", 0.85, "tick", 0.45),
    ("alt1", -0.20, "rise", 0.45),
    ("alt2", 0.00, "whoosh", 0.35),
    ("alt3", 0.30, "air_hiss", 0.30),
    ("alt4", 0.25, "push", 0.55),
    ("alt5", 0.40, "thud", 0.70),
    ("hole1", -0.20, "whoosh_in", 0.45),
    ("hole1", 0.30, "ding", 0.45),
    ("flow1", 0.10, "air_hiss", 0.45),
    ("flow3", 0.20, "balance", 0.50),
    ("load1", 0.20, "push", 0.50),
    ("load3", 0.30, "shield", 0.55),
    ("fog1", -0.20, "whoosh", 0.45),
    ("fog1", 0.20, "pop", 0.50),
    ("fog2", 0.20, "air_hiss", 0.40),
    ("fog3", 0.60, "wipe", 0.50),
    ("fog3", 1.20, "ding", 0.45),
    ("end1", -0.10, "whoosh", 0.40),
    ("end2", 0.10, "pop", 0.55),
    ("end2", 1.00, "pop_high", 0.55),
    ("end3", 0.00, "whoosh_in", 0.40),
    ("end4", 0.40, "outro_chime", 0.55),
]

# Aussprache für Wörter, die das pocketsphinx-Wörterbuch nicht kennt (CMU-Phoneme), für die Wort-Ausrichtung
PRONUNCIATIONS = {
    "defogger": "D IY F AA G ER",
}

# Keywords for the description
TOPIC_TAGS = ["#Aviation", "#AirplaneFacts"]
