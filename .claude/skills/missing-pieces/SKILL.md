---
name: missing-pieces
description: Build a listening guide for a YouTube interview or podcast that explains the niche references (songs, people, places, history, slang, inside jokes) and why the speakers brought each one up, then publish it as a phone-friendly artifact with timestamps and confidence flags. Use when the user gives a YouTube link and asks for a guide, cheat sheet, context, references, or "missing pieces" for an interview, podcast or conversation video.
argument-hint: <youtube-url>
---

# Missing Pieces

The user is listening to an interview right now and enjoys the topic but is not an insider. Give them a guide that explains every reference they would stop to Google, and why these speakers brought it up. It must be ready **within 10 minutes** so it is useful early in the episode.

The value is the context. "What it is" alone is a search result. "Why it came up here" is the guide.

Scripts and the page template live next to this file. `<skill-dir>` below means the base directory shown when this skill loaded.

## 1. Get the transcript (under 1 minute)

```bash
python3 "<skill-dir>/scripts/fetch_transcript.py" "<youtube-url>"
```

This writes `guides/<video_id>/meta.json` and `guides/<video_id>/transcript.txt` under the current directory and prints a summary. If both files already exist it reuses them.

If it fails, show the user the error and the fix it suggests (install or upgrade `yt-dlp`, install `deno`, or the video has no captions). With no captions, ask the user to paste the text from YouTube's "Show transcript" panel, save it as `transcript.txt` in the same `[mm:ss] text` format, and continue.

## 2. Read everything

Read `meta.json` and all of `transcript.txt`. The description often names the guests, songs and what is being promoted. The upload date tells you what "now" means in the conversation. Each transcript line covers about 20 seconds and starts with its timestamp.

## 3. People and relationships

Write this before the references, because every "why it came up" depends on it.

- **Speakers:** the hosts and guests. For each one: who they are in one line, what they stand for (values, politics, artistic identity, communities they represent), and what they were promoting when this was recorded.
- **Relationships:** how the speakers know each other, shared history, past collaborations, tension.
- **Summary:** one or two sentences on what this conversation is and why it is happening now.

Run one to three web searches, in parallel, to confirm what they were promoting around the upload date and any relationship facts you are unsure of.

## 4. Find the references

**The bar:** include anything an engaged listener who is not an insider would stop to Google, given who is speaking and what they just said.

Include:
- **Music (highest priority):** songs, albums, mixtapes, features, producers, labels, groups, earlier bands, venues, scenes, studio stories, samples, quoted lyrics.
- **People:** lesser-known figures, collaborators, family, historical figures.
- **Places:** neighborhoods, schools, venues, and cities when they carry a specific meaning for the speaker.
- **History:** events, movements, organizations.
- **Culture:** TV, film, anime, games, sports moments, eras.
- **Slang:** regional terms and phrases a general listener would miss.
- **Inside jokes:** callbacks, nicknames, shared stories, anything the speakers assume you already know ("you know what happened with...").

Skip:
- Things almost everyone knows. When the speakers use a specific angle on a famous thing, explain the angle and name the entry after it (no entry for a famous rapper; yes for the specific story about them).
- Sponsor reads, small talk, generic opinions.

Rules:
- One entry per reference, at its first mention. Put later mentions in `also_at`.
- `t` is the timestamp of the transcript line where it is first mentioned, in seconds.
- Usually 15 to 40 entries per hour. Do not pad.
- Auto captions garble names. Rebuild the real name from sound and context ("jon coal train" is John Coltrane) and keep the raw caption words in `heard`.

## 5. Check names and facts (the biggest part of the time budget)

- Web search every name you rebuilt from garbled captions and every fact you are not sure of. Send searches in parallel batches of 5 to 10 per message. Stay under about 25 searches.
- Do not search things you know well when the captions got them right.
- Set `confidence`:
  - `green`: the name is certain (clear captions or confirmed by search) and the facts in `what` and `why` are well established.
  - `yellow`: a best guess. The captions were unclear and you inferred the name, or the connection in `why` is your inference rather than something said or documented.
  - `red`: you could not confirm what was said or what it refers to. Still include it with `heard`, so the user can listen back.
- Links: only use URLs you saw in search results or are certain exist, such as a Wikipedia article you know. For a song, a YouTube search link is fine: `https://www.youtube.com/results?search_query=<artist>+<song>`. Never invent URLs. One or two links per entry; for music, include a listen link.

## 6. Write each entry

- `what`: one or two sentences. What it is and what it is known for.
- `why`: one to three sentences. Why these speakers brought it up at this moment. Tie it to the people section: their history, beliefs, projects and relationships. If the speaker is making a point that depends on the reference, say what the point is.

Example of the depth wanted: a jazz drummer mentions Blue Note. `what` says it is the jazz label founded in 1939 that recorded much of hard bop. `why` says the drummer's hero recorded there, and that the drummer brings it up while arguing that artists today have less control than those players did.

Write plainly. No hype, no em dashes.

## 7. Render and publish

Write `guides/<video_id>/guide.json`:

```json
{
  "short_title": "Drummers on Blue Note",
  "generated_at": "2026-10-10",
  "people": {
    "summary": "...",
    "speakers": [
      {"name": "...", "role": "Guest", "who": "...", "stands_for": "...", "promoting": "..."}
    ],
    "relationships": ["..."]
  },
  "entries": [
    {
      "t": 760,
      "name": "Blue Note Records",
      "category": "music",
      "confidence": "green",
      "heard": "blue note",
      "what": "...",
      "why": "...",
      "links": [{"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Blue_Note_Records"}],
      "also_at": [2105]
    }
  ]
}
```

- `short_title`: two to four words naming the conversation. It becomes the page name.
- `category`: one of `music`, `people`, `places`, `history`, `culture`, `slang`, `inside-joke`, `other`.
- Video details and chapters are merged in from `meta.json` automatically.
- Optional `notice`: a line shown at the top, for example when publishing a partial guide.

Then render:

```bash
python3 "<skill-dir>/scripts/render_guide.py" guides/<video_id>/guide.json
```

Fix any problems it lists and run it again. Then publish `guides/<video_id>/guide.html` with the Artifact tool. The page is already designed; publish it as is. Use icon `headphones` and a one-sentence description. If `guides/<video_id>/artifact_url.txt` exists, pass that URL to update the same artifact; otherwise save the new URL there.

If the Artifact tool is not available, render with `--standalone` and open the file (`open guides/<video_id>/guide.html` on macOS).

Reply with the link and one line: how many references, and how many are yellow or red.

## Time budget

| Step | Target |
|---|---|
| Transcript | under 1 min |
| Read and people section | 1 to 2 min |
| Find references | 2 to 3 min |
| Check names and facts | 3 to 4 min |
| Render and publish | 1 min |

If you are running long, stop searching, mark unchecked entries `yellow`, and publish. For episodes over 90 minutes, publish a first version covering the first 30 minutes as soon as it is ready (set `notice` to say it covers up to that point), then finish and update the same artifact.
