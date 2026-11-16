"""Folgen-Daten: Everyday Unpacked – Episode 02 "How popcorn pops".

  * CUES      -> Sprechertext, Untertitel und Timing-Anker (Reihenfolge = Sprechreihenfolge)
  * SCENES    -> welche Szene bei welchem Cue beginnt + Beschreibung für scene_plan.md
  * SFX       -> Soundeffekte, verankert an Cues ("_end" = Videoende, für den Loop)

Wörter in *Sternchen* werden in den Untertiteln farbig hervorgehoben.
pause: Pause NACH dem Cue im geplanten Timing ("c" Komma, "s" Satzende, "p" Absatz).
"""

EPISODE_TITLE = "How popcorn pops"

# (id, text, pause)
CUES = [
    ("hook1", "Every popcorn kernel is a *tiny pressure cooker.*", "s"),
    ("hook2", "And every single one", "c"),
    ("hook3", "is counting down to an *explosion.*", "p"),
    ("ass1", "Most people think heat just makes", "c"),
    ("ass2", "the corn *burst open.*", "s"),
    ("ass3", "But the real trick is *hiding inside.*", "p"),
    ("an1", "Each kernel holds a *tiny drop of water,*", "c"),
    ("an2", "about *fourteen percent* of its weight,", "c"),
    ("an3", "packed into *soft starch.*", "s"),
    ("an4", "Around it sits a *hard shell*", "c"),
    ("an5", "that barely lets anything out.", "p"),
    ("pr1", "Heat it up,", "c"),
    ("pr2", "and that water turns into *steam.*", "s"),
    ("pr3", "The shell *traps it.*", "s"),
    ("pr4", "Pressure climbs to nearly *ten times*", "c"),
    ("pr5", "normal air pressure,", "c"),
    ("pr6", "while the starch inside softens", "c"),
    ("pr7", "into a *hot gel.*", "p"),
    ("bu1", "At around *one hundred eighty degrees Celsius,*", "c"),
    ("bu2", "the shell finally *gives up.*", "p"),
    ("fo1", "In a split second,", "c"),
    ("fo2", "the steam *rushes out*", "c"),
    ("fo3", "and puffs the gel into a *foam,*", "c"),
    ("fo4", "up to *forty times bigger.*", "s"),
    ("fo5", "It cools almost instantly", "c"),
    ("fo6", "and sets into that *crunchy white cloud.*", "p"),
    ("so1", "And the *pop* you hear?", "s"),
    ("so2", "Scientists filmed it at", "c"),
    ("so3", "*thousands of frames per second.*", "s"),
    ("so4", "The sound comes from the *steam escaping,*", "c"),
    ("so5", "not from the *shell cracking.*", "s"),
    ("ju1", "Even the jump is wild:", "c"),
    ("ju2", "a little *leg of starch*", "c"),
    ("ju3", "kicks the kernel *into the air.*", "p"),
    ("du1", "The kernels that *never pop?*", "s"),
    ("du2", "Usually a *damaged or dried-out shell.*", "s"),
    ("du3", "The steam *leaks away,*", "c"),
    ("du4", "so the pressure *never builds.*", "p"),
    ("end1", "One drop of water, one tough shell,", "c"),
    ("end2", "one *tiny explosion.*", "s"),
    ("end3", "What everyday thing", "c"),
    ("end4", "should we *unpack next?*", "s"),
]

# (scene_id, start_cue, title, visual, motion, on-screen text)
SCENES = [
    ("hook", "hook1", "Hook – a pressure cooker with a countdown",
     "Frame 1: extreme close-up of one golden kernel on a hot pan, heat glow underneath. "
     "Then a wider shot of the pan with a row of kernels.",
     "Snap punch-in on frame 1, kernel trembles; pull back to the pan; a countdown ring 3-2-1 closes around the kernel.",
     "'A TINY PRESSURE COOKER' (from frame 1) -> '3 · 2 · 1'"),
    ("assume", "ass1", "Common assumption",
     "Kernel above a stylised flame on dark navy; then a cut-away view slides open.",
     "Flame flickers, kernel wobbles, '?' pops; kernel splits along its middle and reveals the inside.",
     "'HEAT = BURST?' -> 'THE TRICK IS INSIDE'"),
    ("anatomy", "an1", "Inside the kernel",
     "Big cut-away kernel: thick golden shell, cream starch, blue water droplets.",
     "Droplets fade in and drift, 14 % pie fills, labels draw in, droplets bounce off the shell wall.",
     "'WATER ≈ 14 %', 'SOFT STARCH', 'HARD SHELL'"),
    ("pressure", "pr1", "Steam under pressure",
     "Same cut-away above a flame, pressure gauge on the right.",
     "Shell glows, droplets turn into fast steam particles, gauge needle sweeps to ≈10×, starch turns glossy, "
     "kernel trembles and swells slightly.",
     "'STEAM', '≈ 10× AIR PRESSURE', 'HOT GEL'"),
    ("burst", "bu1", "The breaking point",
     "Thermometer next to the kernel.",
     "Mercury rises to 180 °C, cracks race across the shell, white flash on 'gives up'.",
     "'180 °C'"),
    ("foam", "fo1", "Inside out: the foam",
     "The kernel explodes into a white popcorn cloud; size comparison kernel vs. popcorn.",
     "Steam jets out, foam blobs balloon outward, then freeze with a sparkle.",
     "'UP TO 40× BIGGER', 'SET IN A SPLIT SECOND'"),
    ("sound", "so1", "Where the pop comes from",
     "High-speed film strip with frames of a popping kernel; steam jet with sound-wave arcs.",
     "Film strip scrolls, frame counter runs, sound waves ripple out of the steam jet; ✓ / ✗ cards.",
     "'≈ 2,900 FPS', 'STEAM ESCAPING ✓', 'SHELL CRACKING ✗'"),
    ("jump", "ju1", "The gymnast kernel",
     "Side view of a kernel on the pan.",
     "A starch 'leg' pushes out, the kernel flips into the air along a dotted arc and lands.",
     "'A LEG OF STARCH'"),
    ("dud", "du1", "Why some never pop",
     "Unpopped kernel with a crack, small gauge next to it.",
     "Steam wisps leak out through the crack, gauge needle stays low and shakes.",
     "'DAMAGED OR DRIED-OUT SHELL', 'NO PRESSURE = NO POP'"),
    ("outro", "end1", "Payoff + question + loop",
     "Three icons (drop, shell, burst), then the question card on the pan.",
     "Icons pop in one by one, question card snaps up, flies out, camera zooms into one kernel and lands "
     "exactly on frame 1 (seamless loop).",
     "'WATER + SHELL = POP', 'WHAT SHOULD WE UNPACK NEXT?'"),
]

# Soundeffekte: (cue_id, offset_seconds, sound_name, gain)
SFX = [
    ("hook1", -0.33, "pop", 0.70),
    ("hook1", -0.30, "sizzle", 0.30),
    ("hook2", -0.05, "whoosh", 0.50),
    ("hook3", 0.00, "tick", 0.55),
    ("hook3", 0.45, "tick", 0.55),
    ("hook3", 0.90, "tick", 0.55),
    ("ass1", -0.20, "whoosh", 0.45),
    ("ass1", 0.20, "flame", 0.40),
    ("ass2", 0.30, "pop_high", 0.45),
    ("ass3", 0.10, "split", 0.55),
    ("an1", -0.15, "whoosh_in", 0.35),
    ("an1", 0.40, "drip", 0.50),
    ("an2", 0.30, "tick", 0.45),
    ("an4", 0.20, "thud", 0.40),
    ("pr1", -0.10, "flame", 0.45),
    ("pr2", 0.20, "air_hiss", 0.35),
    ("pr4", 0.00, "rise", 0.45),
    ("pr7", 0.10, "sizzle", 0.35),
    ("bu1", 0.00, "rise", 0.40),
    ("bu2", 0.10, "crackle", 0.55),
    ("bu2", 0.55, "burst", 0.80),
    ("fo2", 0.00, "air_hiss", 0.45),
    ("fo3", 0.10, "whoosh", 0.45),
    ("fo4", 0.20, "pop", 0.55),
    ("fo6", 0.30, "sparkle", 0.40),
    ("so1", 0.00, "pop", 0.70),
    ("so2", 0.10, "projector", 0.45),
    ("so4", 0.20, "air_hiss", 0.35),
    ("so4", 0.80, "ding", 0.40),
    ("so5", 0.40, "buzz", 0.35),
    ("ju1", -0.15, "whoosh", 0.40),
    ("ju2", 0.30, "spring", 0.55),
    ("ju3", 0.90, "tap", 0.50),
    ("du1", -0.15, "whoosh", 0.40),
    ("du2", 0.20, "crackle", 0.30),
    ("du3", 0.10, "air_hiss", 0.30),
    ("du4", 0.40, "buzz", 0.30),
    ("end1", -0.10, "pop", 0.45),
    ("end1", 0.80, "pop_high", 0.45),
    ("end2", 0.10, "burst", 0.45),
    ("end3", 0.00, "whoosh_in", 0.35),
    ("end4", 0.20, "outro_chime", 0.45),
    ("_end", -0.72, "whoosh_in", 0.50),   # Loop: Zoom zurück aufs Korn, Pop am Anfang schließt ihn ab
]

# Aussprache für Wörter, die das pocketsphinx-Wörterbuch nicht kennt (CMU-Phoneme)
PRONUNCIATIONS = {}

TOPIC_TAGS = ["#FoodScience", "#Popcorn"]
