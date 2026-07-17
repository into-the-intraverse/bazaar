---
name: youread
description: >
  Use when the user shares a YouTube link (youtube.com/watch?v=, youtu.be/,
  youtube.com/shorts/) and wants a summary, key points, the transcript, notes,
  a wiki source note, the on-screen slides/figures/code captured, or the
  papers/citations/links shown in the video — or asks any question paired with
  a YouTube URL ("TL;DW", "what does this video say about X", "capture the
  slides/paper references").
---

# youread — YouTube → wiki source notes

Extract what a YouTube video says **and shows** into a source-note folder (`note.md` +
`transcript.md` + curated `images/`), then use that note to answer the user.

The capture itself is heavy — full transcripts, dozens of candidate frames — and every video is an
independent job with no need for conversation context. So **never fetch subtitles or extract frames
in this conversation**: spawn a capture worker per video and only load its finished outputs. For
multiple URLs, spawn the workers in parallel.

## Step 1 — Decide the destination root (once, up front)

- If the user names a location, use it.
- Else, if the working directory's git root contains `atoms/`, `wiki/`, and `raw/` (an atomic-wiki
  repo), use `raw/` — the note lands ready for `/atomic-wiki:ingest`.
- Otherwise use `./notes/`.

The worker creates `<root>/<channel-slug>/<video-slug>/` under it, so a standalone capture can
later move into a wiki as a plain copy.

## Step 2 — Spawn the capture worker

Spawn a subagent — general-purpose; a small model (sonnet) is
enough, pass it if your Agent tool takes a model — with this prompt, filled in:

```
Read <skill dir>/references/capture.md and execute it exactly.
SKILL_DIR: <skill dir>
Video URL: <url>
Destination root: <absolute root path decided at step 1>
Subtitle language: <code the user needs, otherwise default to `en` or `ru` - whichever is available>
Capture visuals: <yes | no — no only if the user opted out>
Extra constraints: <e.g. --max-height 1080, or "none">
```

`<skill dir>` is the absolute path of the directory containing this SKILL.md — resolve it from the
path you read this file from. The worker fetches subtitles, extracts and curates frames, writes
`note.md` / `transcript.md` / `images/`, and returns a report: destination path, video metadata,
the note's summary, and warnings.

If subagents are unavailable in this environment, read `references/capture.md` and execute it
yourself.

## Step 3 — Process the results

- Read `<dest>/note.md`; load specific images only when the user's question needs them.
- If the user asked something, answer it directly in chat, in their language. Keep the reply
  focused — the full detail lives in the note.
- Tell them where the note was saved and relay any worker warnings (visuals skipped, frame cap
  exceeded, etc.).
- The papers and links the note records are **never fetched or verified** by youread — resolving
  them is the downstream job.
- If the note landed in an atomic-wiki repo, end with the ready-to-run next step:
  `/atomic-wiki:ingest raw/<channel-slug>/<video-slug>/`. Do **not** run the ingest yourself —
  atom extraction and branch approval are the user's call.
