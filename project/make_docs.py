"""Erzeugt output/scene_plan.md aus episode.py + aktuellem Timing (bleibt so immer synchron)."""
import episode as EP
from timeline import clean


def fmt(t):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:04.1f}"


def write_scene_plan(tl, bounds, path):
    starts = {c["id"]: c["start"] for c in tl["cues"]}
    mode = ("geplantes Timing (noch kein Voiceover) – wird beim Render mit input/voiceover.mp3 automatisch angepasst"
            if tl["mode"] == "planned" else "an input/voiceover.mp3 ausgerichtet")
    L = [f"# Scene Plan – {EP.EPISODE_TITLE}", "",
         f"**Format:** 1080 × 1920 (9:16), 30 fps  ",
         f"**Total length:** {tl['total']:.1f} s  ",
         f"**Timing:** {mode}", "",
         "Safe zones: key text & captions stay between y ≈ 220 px and y ≈ 1430 px and x ≈ 60–1000 px "
         "(top status/tabs and bottom description/buttons of TikTok & YouTube Shorts stay clear). "
         "Captions are centred at y = 1350 px on a dark box.", ""]
    cue_by_scene = {}
    order = [c[0] for c in EP.CUES]
    scene_first = [order.index(sc[1]) for sc in EP.SCENES] + [len(order)]
    for k, sc in enumerate(EP.SCENES):
        cue_by_scene[sc[0]] = order[scene_first[k]:scene_first[k + 1]]
    text = {c[0]: c[1] for c in EP.CUES}
    for k, ((sid, _, title, visual, motion, onscreen), (_, s0, s1)) in enumerate(zip(EP.SCENES, bounds)):
        s1 = min(s1, tl["total"])
        L += [f"## Scene {k + 1} – {title}  `{fmt(s0)} – {fmt(s1)}`", ""]
        L += ["**Voiceover:** " + " ".join(clean(text[c]) for c in cue_by_scene[sid]), ""]
        L += [f"**Visual:** {visual}", "", f"**Motion:** {motion}", "", f"**On-screen text:** {onscreen}", ""]
        fx = [f"{fmt(starts[c] + off)} {name}" for c, off, name, _ in EP.SFX if c in cue_by_scene[sid]]
        L += ["**Sound effects:** " + (", ".join(fx) if fx else "–") + " (plus quiet cabin-hum bed throughout)", ""]
    L += ["## Transitions", "", "Transitions alternate between a zoom-through and an upward whip with motion blur (0.36 s). Global effects: slow camera push-in per scene, impact punches (zoom jolt + shake + sub-bass hit) on every pop/stamp/burst, soft floating light specks, light vignette, karaoke captions (current word highlighted), auto whoosh on scene changes. No fade-in/out: the last 0.7 s zoom back onto frame 1 for a seamless loop.", "",
          "## Caption cues", "", "| # | Start | End | Text |", "|---|---|---|---|"]
    for i, c in enumerate(tl["cues"]):
        L.append(f"| {i + 1} | {fmt(c['start'])} | {fmt(c['end'])} | {clean(c['text'])} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
