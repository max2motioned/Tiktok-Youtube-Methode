"""Everyday Unpacked – Startskript.

Aufruf (aus dem Repo-Hauptordner):
    python3 project/render.py episodes/02-popcorn                 # Timing, Untertitel, SFX, Video (+ final.mp4)
    python3 project/render.py episodes/02-popcorn --still 12.5    # nur Standbilder nach <folge>/output/stills
    python3 project/render.py episodes/02-popcorn --workers 8
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", help="Ordner der Folge, z. B. episodes/01-airplane-window-hole")
    ap.add_argument("--still", type=float, nargs="*", help="nur Standbilder bei diesen Sekunden")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    ep_dir = os.path.abspath(args.episode)
    if not os.path.isfile(os.path.join(ep_dir, "episode.py")):
        raise SystemExit(f"Keine episode.py in {ep_dir}")
    sys.path[:0] = [ep_dir, HERE]
    import engine
    engine.main(args)
