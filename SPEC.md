# Missing Pieces: MVP spec

## Problem
I enjoy interviews and podcasts on topics where I am not an insider. The speakers drop references (songs, people, places, history, slang, inside jokes) that I would have to stop and Google, and the context behind them is what makes the conversation land.

## Goal
Paste a YouTube link and, within 10 minutes, get a guide I can scan while listening and read again afterwards.

## Users and moments
- **During (main mode):** watching on a laptop, or listening on Spotify with the laptop open. The guide sits next to it in timestamp order.
- **After:** listening on a phone or in the car, then opening the same guide on my phone.

## Decisions
| Area | Decision |
|---|---|
| Input | YouTube link only. Spotify has no transcript API, and most interview shows are also on YouTube. |
| Where it runs | Claude Code skill on my laptop. YouTube blocks transcript requests from cloud IPs, so claude.ai and cloud sessions cannot fetch them. |
| Transcript | `yt-dlp` captions. Manual captions first, then auto captions. |
| Output | A claude.ai artifact, so the guide made on the laptop opens on the phone too. |
| What to include | Anything I would stop to Google, given who is speaking. Music gets the most weight. Slang and inside jokes count. |
| Out of scope | Filtering out things I already know. Spotify and Apple input. Videos without captions. A library of past guides. |
| Top section | People and relationships: who the speakers are, what they stand for, what they are promoting, how they are connected. |
| Each entry | Timestamp (opens YouTube at that point), name, category, confidence, what it is, why it came up, one or two links. |
| Why it came up | The core value. It ties the reference to the speakers' history, beliefs and the point they were making. |
| Confidence | Green: checked. Yellow: best guess (garbled captions or inferred link), shows what the captions heard. Red: unconfirmed, listen back. |
| Name checking | Web search every name rebuilt from garbled captions and every uncertain fact. Never invent links. |
| Spoilers | Later references are visible. |
| Speed | Under 10 minutes end to end. Publish early with yellow flags rather than run long. |

## Success test
Run the skill on the two example videos in a fresh Claude Code session:
- Chance the Rapper and Vic Mensa: https://www.youtube.com/watch?v=s8Baf3hr2yY
- Questlove interviews Thundercat: https://www.youtube.com/watch?v=piJbnoF318E

Before seeing any output, I write down 5 to 10 things per episode that I wanted explained. The MVP passes if, for each episode:
1. The guide covers most of my list (at least 7 of 10).
2. The entries it has are correct, and anything shaky is flagged yellow or red.
3. The "why it came up" lines are useful, not generic.
4. It is ready within 10 minutes of pasting the link.

## Later ideas (not in MVP)
- Start from a phone using a transcript API that works from the cloud.
- Spotify links matched to the episode's YouTube upload.
- A profile of what I already know, to skip basics.
- Live mode that follows playback position.
