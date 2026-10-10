#!/usr/bin/env python3
"""Fetch a YouTube video's captions and details for a Missing Pieces guide.

Usage:
    fetch_transcript.py URL [--out-root guides] [--refresh]

Writes <out-root>/<video_id>/meta.json and transcript.txt, then prints a short
summary. If both files already exist it reuses them unless --refresh is given.

Needs yt-dlp (brew install yt-dlp). Run it from a home connection: YouTube
blocks most cloud and datacenter IPs.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BLOCK_SECONDS = 20  # one transcript line per ~20s of speech

ID_PATTERNS = [
    r"(?:v=|vi=)([A-Za-z0-9_-]{11})",
    r"youtu\.be/([A-Za-z0-9_-]{11})",
    r"/(?:shorts|live|embed|v)/([A-Za-z0-9_-]{11})",
]


def video_id(url):
    for pattern in ID_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url
    return None


def fmt_time(seconds, long_form):
    s = int(seconds)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if long_form else f"{m:02d}:{s:02d}"


def parse_json3(text):
    """YouTube json3 captions -> [(start_seconds, text)]."""
    segments = []
    for ev in json.loads(text).get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        line = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
        if line:
            segments.append((ev.get("tStartMs", 0) / 1000, line))
    return segments


VTT_TIME = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{3})\s+-->")
VTT_TAG = re.compile(r"<[^>]+>")


def parse_vtt(text):
    """WebVTT captions -> [(start_seconds, text)].

    Auto captions repeat the previous line at the top of each cue, so a line
    equal to the last emitted line is dropped.
    """
    segments = []
    last = None
    start = None
    for raw in text.splitlines():
        m = VTT_TIME.match(raw)
        if m:
            h, mi, s, ms = m.groups()
            start = int(h or 0) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000
            continue
        if start is None:
            continue
        line = html.unescape(VTT_TAG.sub("", raw)).strip()
        if not line or line == last:
            continue
        segments.append((start, line))
        last = line
    return segments


def group_blocks(segments, block_seconds=BLOCK_SECONDS):
    """Merge caption segments into ~block_seconds chunks -> [(start, text)]."""
    blocks = []
    cur_start, cur = None, []
    for start, text in segments:
        if cur_start is None:
            cur_start = start
        elif start - cur_start >= block_seconds:
            blocks.append((cur_start, " ".join(cur)))
            cur_start, cur = start, []
        cur.append(text)
    if cur:
        blocks.append((cur_start, " ".join(cur)))
    return [(t, re.sub(r"\s+", " ", text).strip()) for t, text in blocks]


def find_ytdlp():
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        sys.exit("yt-dlp is not installed. Install it with: brew install yt-dlp  (or: pip install yt-dlp)")


def pick_caption(files, vid, manual_langs):
    """Prefer manual English captions, then the original auto captions."""
    def lang(path):
        return path.name[len(vid) + 1:].rsplit(".", 1)[0]

    def rank(path):
        lg = lang(path)
        is_manual = lg in manual_langs
        fmt_rank = 0 if path.suffix == ".json3" else 1
        if is_manual:
            return (0, 0 if lg == "en" else 1, fmt_rank)
        auto_rank = {"en-orig": 0, "en": 1}.get(lg, 2)
        return (1, auto_rank, fmt_rank)

    english = [f for f in files if lang(f) == "en" or lang(f).startswith("en-")]
    if not english:
        return None, None, None
    best = min(english, key=rank)
    return best, lang(best), "manual" if lang(best) in manual_langs else "auto"


def fetch(url, vid):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cmd = find_ytdlp() + [
            "--skip-download", "--no-playlist",
            "--write-info-json", "--write-subs", "--write-auto-subs",
            "--sub-langs", "en.*,en", "--sub-format", "json3/vtt/best",
            "-o", str(tmp / "%(id)s.%(ext)s"),
            url,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        info_files = list(tmp.glob("*.info.json"))
        if not info_files:
            tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
            sys.exit(
                "yt-dlp could not read the video.\n"
                f"{tail}\n\n"
                "Try: brew upgrade yt-dlp. If it mentions a JavaScript runtime: brew install deno.\n"
                "If it says 'Sign in to confirm you're not a bot', you are probably on a cloud or VPN IP."
            )
        info = json.loads(info_files[0].read_text())
        vid = info.get("id") or vid
        caption_files = [p for p in tmp.iterdir() if p.suffix in (".json3", ".vtt")]
        path, lang, source = pick_caption(caption_files, vid, set((info.get("subtitles") or {}).keys()))
        if path is None:
            sys.exit(
                "This video has no English captions.\n"
                "Paste the transcript from YouTube's 'Show transcript' panel instead."
            )
        raw = path.read_text(encoding="utf-8")
        segments = parse_json3(raw) if path.suffix == ".json3" else parse_vtt(raw)
        return info, segments, lang, source


def build_meta(info, vid, lang, source):
    date = info.get("upload_date") or ""
    if re.fullmatch(r"\d{8}", date):
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return {
        "id": vid,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "title": info.get("title") or "",
        "channel": info.get("channel") or info.get("uploader") or "",
        "upload_date": date,
        "duration": int(info.get("duration") or 0),
        "description": info.get("description") or "",
        "chapters": [
            {"start": int(c.get("start_time") or 0), "title": c.get("title") or ""}
            for c in (info.get("chapters") or [])
        ],
        "tags": info.get("tags") or [],
        "caption_source": source,
        "caption_lang": lang,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--out-root", default="guides")
    ap.add_argument("--refresh", action="store_true", help="re-download even if files exist")
    args = ap.parse_args()

    vid = video_id(args.url)
    if not vid:
        sys.exit(f"Could not find a YouTube video id in: {args.url}")

    out = Path(args.out_root) / vid
    meta_path, transcript_path = out / "meta.json", out / "transcript.txt"

    if meta_path.exists() and transcript_path.exists() and not args.refresh:
        meta = json.loads(meta_path.read_text())
        print(f"Using existing files in {out}/")
    else:
        info, segments, lang, source = fetch(args.url, vid)
        meta = build_meta(info, vid, lang, source)
        long_form = meta["duration"] >= 3600 or (segments and segments[-1][0] >= 3600)
        lines = [f"[{fmt_time(t, long_form)}] {text}" for t, text in group_blocks(segments)]
        out.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    words = len(transcript_path.read_text(encoding="utf-8").split())
    print(f"Title:     {meta['title']}")
    print(f"Channel:   {meta['channel']}  ({meta['upload_date']})")
    print(f"Duration:  {fmt_time(meta['duration'], True)}")
    print(f"Captions:  {meta['caption_source']} ({meta['caption_lang']}), ~{words} words")
    print(f"Chapters:  {len(meta['chapters'])}")
    print(f"Files:     {meta_path}  {transcript_path}")


if __name__ == "__main__":
    main()
