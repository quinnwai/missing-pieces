#!/usr/bin/env python3
"""Check a guide.json and render it into a publishable HTML page.

Usage:
    render_guide.py guides/<video_id>/guide.json [-o OUT] [--standalone]

Video details and chapters come from meta.json in the same folder, so
guide.json only needs short_title, people and entries. Exits non-zero with a
list of problems if the guide is malformed.

--standalone adds <!doctype html> and a head so the file opens correctly in a
browser. Leave it off for the Artifact tool, which adds its own skeleton.
"""

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
CATEGORIES = {"music", "people", "places", "history", "culture", "slang", "inside-joke", "other"}
CONFIDENCE = {"green", "yellow", "red"}


def check(guide):
    errors, warnings = [], []
    if not str(guide.get("short_title", "")).strip():
        errors.append("short_title is missing (2 to 4 words, used as the page name)")
    people = guide.get("people")
    if not isinstance(people, dict) or not str(people.get("summary", "")).strip():
        errors.append("people.summary is missing")
    elif not people.get("speakers"):
        errors.append("people.speakers is empty")

    entries = guide.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("entries is empty")
        return errors, warnings

    for i, e in enumerate(entries):
        where = f"entries[{i}] ({e.get('name', '?')})"
        if not isinstance(e.get("t"), (int, float)) or e["t"] < 0:
            errors.append(f"{where}: t must be seconds from the start, as a number")
        for field in ("name", "what", "why"):
            if not str(e.get(field, "")).strip():
                errors.append(f"{where}: {field} is missing")
        if e.get("category") not in CATEGORIES:
            errors.append(f"{where}: category must be one of {sorted(CATEGORIES)}")
        if e.get("confidence") not in CONFIDENCE:
            errors.append(f"{where}: confidence must be green, yellow or red")
        elif e["confidence"] != "green" and not str(e.get("heard", "")).strip():
            warnings.append(f"{where}: {e['confidence']} entry has no 'heard' caption text")
        for link in e.get("links") or []:
            if not str(link.get("url", "")).startswith("https://") or not link.get("label"):
                errors.append(f"{where}: each link needs a label and an https:// url")
        for t in e.get("also_at") or []:
            if not isinstance(t, (int, float)):
                errors.append(f"{where}: also_at must be a list of seconds")
    return errors, warnings


def safe_json(data):
    """JSON that cannot close the surrounding <script> tag."""
    return (json.dumps(data, ensure_ascii=False)
            .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("guide")
    ap.add_argument("-o", "--out", help="default: guide.html next to guide.json")
    ap.add_argument("--standalone", action="store_true", help="add doctype and head for opening locally")
    args = ap.parse_args()

    guide_path = Path(args.guide)
    guide = json.loads(guide_path.read_text(encoding="utf-8"))
    meta_path = guide_path.parent / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    video = {k: meta.get(k) for k in ("id", "url", "title", "channel", "upload_date", "duration", "caption_source")}
    video.update(guide.get("video") or {})
    guide["video"] = video
    guide.setdefault("chapters", meta.get("chapters") or [])

    errors, warnings = check(guide)
    if not video.get("id"):
        errors.append("video id is missing (no meta.json next to guide.json and no video.id)")
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        print("guide.json has problems:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    guide["entries"].sort(key=lambda e: e["t"])
    page = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__GUIDE_TITLE__", html.escape(guide["short_title"].strip()))
            .replace("__GUIDE_DATA__", safe_json(guide)))
    if args.standalone:
        page = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '</head><body>\n' + page + '\n</body></html>\n')

    out = Path(args.out) if args.out else guide_path.with_name("guide.html")
    out.write_text(page, encoding="utf-8")

    conf = Counter(e["confidence"] for e in guide["entries"])
    cats = Counter(e["category"] for e in guide["entries"])
    print(f"Wrote {out}")
    print(f"{len(guide['entries'])} entries: {conf['green']} green, {conf['yellow']} yellow, {conf['red']} red")
    print("By category: " + ", ".join(f"{k} {v}" for k, v in cats.most_common()))


if __name__ == "__main__":
    main()
