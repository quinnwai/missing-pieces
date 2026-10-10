# Missing Pieces

A Claude Code skill that turns a YouTube interview into a listening guide: who the speakers are, every niche reference they make, and why each one came up. It publishes the guide as a claude.ai artifact you can keep open next to the video or read on your phone afterwards.

See [SPEC.md](SPEC.md) for the product decisions.

## Setup (laptop, once)

1. Install Claude Code and sign in with a Pro or Max plan (artifacts need one).
2. Install yt-dlp: `brew install yt-dlp`
   - If it later warns about a JavaScript runtime: `brew install deno`
3. Clone this repo.
4. Optional, to use the skill from any folder: `ln -s "$PWD/.claude/skills/missing-pieces" ~/.claude/skills/missing-pieces`

Run it on your home connection. YouTube blocks transcript requests from cloud servers and many VPNs.

## Use

From the repo folder (or anywhere, if you added the symlink), start Claude Code and type:

```
/missing-pieces https://www.youtube.com/watch?v=piJbnoF318E
```

Files land in `guides/<video_id>/`:
- `meta.json` and `transcript.txt`: what the fetch script pulled
- `guide.json`: what Claude wrote
- `guide.html`: the rendered page
- `artifact_url.txt`: the published link

## Scripts

Both live in `.claude/skills/missing-pieces/scripts/` and only need Python 3.

| Script | Does |
|---|---|
| `fetch_transcript.py <url>` | Pulls captions and video details with yt-dlp into `guides/<id>/` |
| `render_guide.py guides/<id>/guide.json` | Checks the guide and renders it with `assets/template.html`. Add `--standalone` to open it straight in a browser. |

Tests: `python3 -m unittest discover tests`

## Running the success test

1. Write down your 5 to 10 items per episode first.
2. Fetch both transcripts and push them, so the guides can also be tuned from a cloud session:
   ```bash
   python3 .claude/skills/missing-pieces/scripts/fetch_transcript.py "https://www.youtube.com/watch?v=s8Baf3hr2yY"
   python3 .claude/skills/missing-pieces/scripts/fetch_transcript.py "https://www.youtube.com/watch?v=piJbnoF318E"
   git add guides && git commit -m "Add test transcripts" && git push
   ```
3. Start a fresh Claude Code session and run `/missing-pieces <url>` for each one. Time it.
4. Compare each guide against your list.
