"""Offline tests for the Missing Pieces scripts. Run: python3 -m unittest discover tests"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "missing-pieces" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = load("fetch_transcript")
render = load("render_guide")


class VideoIdTest(unittest.TestCase):
    def test_url_shapes(self):
        for url in [
            "https://www.youtube.com/watch?v=s8Baf3hr2yY&list=WL&index=42",
            "https://youtu.be/s8Baf3hr2yY?t=30",
            "https://www.youtube.com/live/s8Baf3hr2yY",
            "https://m.youtube.com/watch?feature=share&v=s8Baf3hr2yY",
            "s8Baf3hr2yY",
        ]:
            self.assertEqual(fetch.video_id(url), "s8Baf3hr2yY", url)
        self.assertIsNone(fetch.video_id("https://example.com/nothing"))


class CaptionParseTest(unittest.TestCase):
    def test_json3_skips_newline_events(self):
        raw = json.dumps({"events": [
            {"tStartMs": 0, "segs": [{"utf8": "we went to"}, {"utf8": " jones"}]},
            {"tStartMs": 1500, "aAppend": 1, "segs": [{"utf8": "\n"}]},
            {"tStartMs": 2000, "segs": [{"utf8": "college prep"}]},
            {"tStartMs": 3000},
        ]})
        self.assertEqual(fetch.parse_json3(raw), [(0.0, "we went to jones"), (2.0, "college prep")])

    def test_vtt_drops_rolling_duplicates(self):
        raw = """WEBVTT
Kind: captions

00:00:00.000 --> 00:00:02.000 align:start position:0%
we<00:00:00.500><c> grew</c><00:00:00.900><c> up</c>

00:00:02.000 --> 00:00:02.010 align:start position:0%
we grew up

00:00:02.010 --> 00:00:04.000 align:start position:0%
we grew up
on<00:00:02.500><c> the</c><00:00:03.000><c> south side</c>

01:02:03.500 --> 01:02:05.000
Tom &amp; Jerry
"""
        self.assertEqual(fetch.parse_vtt(raw), [
            (0.0, "we grew up"),
            (2.01, "on the south side"),
            (3723.5, "Tom & Jerry"),
        ])

    def test_group_blocks(self):
        segs = [(0, "a"), (5, "b"), (19.9, "c"), (20, "d"), (45, "e")]
        self.assertEqual(fetch.group_blocks(segs, 20), [(0, "a b c"), (20, "d"), (45, "e")])

    def test_fmt_time(self):
        self.assertEqual(fetch.fmt_time(760, False), "12:40")
        self.assertEqual(fetch.fmt_time(3725, True), "1:02:05")


class PickCaptionTest(unittest.TestCase):
    def paths(self, *names):
        return [Path(f"/tmp/abcdefghijk.{n}") for n in names]

    def test_prefers_manual(self):
        best, lang, source = fetch.pick_caption(self.paths("en-orig.json3", "en.json3"), "abcdefghijk", {"en"})
        self.assertEqual((lang, source), ("en", "manual"))

    def test_auto_prefers_original(self):
        best, lang, source = fetch.pick_caption(self.paths("en.json3", "en-orig.json3"), "abcdefghijk", set())
        self.assertEqual((lang, source), ("en-orig", "auto"))

    def test_prefers_json3_over_vtt(self):
        best, _, _ = fetch.pick_caption(self.paths("en-orig.vtt", "en-orig.json3"), "abcdefghijk", set())
        self.assertEqual(best.suffix, ".json3")

    def test_no_english(self):
        self.assertEqual(fetch.pick_caption(self.paths("fr.json3"), "abcdefghijk", set()), (None, None, None))


def good_guide():
    return {
        "short_title": "Test Guide",
        "people": {"summary": "Two drummers talk.", "speakers": [{"name": "A", "role": "Host"}]},
        "entries": [
            {"t": 90, "name": "B", "category": "music", "confidence": "green", "what": "w", "why": "y"},
            {"t": 10, "name": "A </script><b>", "category": "slang", "confidence": "yellow",
             "heard": "a", "what": "w", "why": "y", "links": [{"label": "L", "url": "https://example.com"}]},
        ],
    }


class RenderTest(unittest.TestCase):
    def test_good_guide_passes(self):
        self.assertEqual(render.check(good_guide()), ([], []))

    def test_bad_entries_reported(self):
        g = good_guide()
        g["entries"][0].update(category="food", confidence="blue", t="1:30")
        g["entries"][1]["links"] = [{"label": "x", "url": "javascript:alert(1)"}]
        errors, _ = render.check(g)
        self.assertEqual(len(errors), 4)

    def test_render_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "meta.json").write_text(json.dumps({"id": "abcdefghijk", "title": "T", "duration": 100,
                                                       "caption_source": "auto", "chapters": []}))
            (tmp / "guide.json").write_text(json.dumps(good_guide()))
            proc = subprocess.run([sys.executable, str(SCRIPTS / "render_guide.py"), str(tmp / "guide.json")],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            page = (tmp / "guide.html").read_text()
            self.assertIn("<title>Test Guide</title>", page)
            self.assertNotIn("__GUIDE_DATA__", page)
            # the injected data must not be able to close its script tag
            data = page.split('id="guide-data" type="application/json">', 1)[1].split("</script>", 1)[0]
            parsed = json.loads(data)
            self.assertEqual([e["t"] for e in parsed["entries"]], [10, 90])
            self.assertEqual(parsed["video"]["id"], "abcdefghijk")


if __name__ == "__main__":
    unittest.main()
