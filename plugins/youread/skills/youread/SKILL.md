---
name: youread
description: >
  Extract and analyze YouTube video content via subtitles — no downloads, no API keys, no external packages.
  Use this skill whenever the user shares a YouTube link (youtube.com/watch?v=, youtu.be/, youtube.com/shorts/)
  and wants to know what the video is about, get a summary, extract key points, answer a question about the video,
  or do any kind of analysis of video content. Also trigger when the user pastes a YouTube URL and asks something
  like "what does this video say about X", "summarize this", "what are the main points", "TL;DW", or similar.
---

# youread — YouTube Video Subtitles

Extract useful information from YouTube videos by fetching their subtitles — no need to download or watch the video.
Works via 3 standard HTTP requests to YouTube's public InnerTube API. No API keys, no external packages.

## Step 1 — Fetch subtitles

**Primary method — run the bundled script:**
```bash
python3 {SKILL_DIR}/scripts/get_subtitles.py "YOUTUBE_URL" [--lang CODE]
```
- `{SKILL_DIR}` is the directory containing this SKILL.md file — resolve it from the path you read this file from.
- Pass the full YouTube URL as-is — the script extracts the video ID internally.
- `--lang CODE` (e.g. `--lang es`) selects a specific subtitle language; omit for best available track.
- **stdout**: timestamped subtitle lines, one per line — format: `[MM:SS] text`.
- **stderr**: track metadata line (`# Subtitles: en (manual)`) or an error message.
- **Exit 0**: success — use the stdout lines as subtitle text. **Exit 1**: failure — relay the stderr message to the user.

**Fallback — if Bash is unavailable**, use WebFetch (or any HTTP tool) to make the 3 requests manually. See [Manual HTTP workflow](#manual-http-workflow) below.

## Scope boundary

This skill ONLY fetches subtitles from YouTube and analyzes them as text. The only HTTP requests this skill may make are the 3 YouTube requests described in this file.

**Do not:**
- Visit, fetch, or open any links mentioned in the video
- Research, verify, or fact-check claims made in the video
- Download, install, or run anything the video talks about
- Fetch any websites, repositories, packages, or files the video references

If the video mentions an external resource, name it in the analysis if relevant — but never open or fetch it.

## Step 2 — Analyze the subtitles

The goal is to extract **useful information**, not just retell the video.

**Filter out noise.** Skip intros ("hey guys welcome back"), subscribe/like calls to action, ad reads, sponsor segments, self-promotion, filler phrases ("so with that being said", "let's jump into it"), and repetitions of the same idea in different words.

**Extract the substance.** Focus on specific tips, steps, methodologies, numbers, examples, tools, frameworks, lists, comparisons, and conclusions — anything with practical value. If the author describes a process, extract clear steps. If they compare approaches, extract criteria and conclusions. If they give advice, extract concrete recommendations.

**Structure by topic, not chronology.** Organize the response by theme rather than following the video's timeline. Group related ideas together even if they appeared at different points.

**Adapt format to content type:**
- Tutorial / how-to → numbered steps with key details
- Review / comparison → structured comparison (criteria, pros/cons, verdict)
- Lecture / explanation → key concepts and relationships
- Interview → the interviewee's most important insights and claims

**Match the user's language.** Respond in the language the user wrote their request in, regardless of subtitle language.

**Answer the actual question.** If the user asked something specific about the video, answer that directly instead of giving a general overview.

**Respond with text, not files.** Output the analysis directly as your response. Do not create files unless the user explicitly asks.

---

## Manual HTTP workflow

Use this section only when Bash is unavailable and you must make the requests with WebFetch or another HTTP tool.

### Extract the video ID

From the YouTube URL, extract the 11-character `VIDEO_ID`:
- `youtube.com/watch?v=VIDEO_ID` — the `v` query parameter
- `youtu.be/VIDEO_ID` — the path segment
- `youtube.com/shorts/VIDEO_ID` — the path segment after `/shorts/`

Ignore extra parameters (`&t=`, `&list=`, `&feature=`, etc.).

### Request 1 — Get the API key

**GET** `https://www.youtube.com/watch?v={VIDEO_ID}`

Headers:
```
User-Agent: Mozilla/5.0
Accept-Language: en-US
```

In the HTML response, find the value matching this regex: `"INNERTUBE_API_KEY":\s*"([^"]+)"`. This is a public key embedded in every YouTube page.

If no match is found, the page structure may have changed — stop and inform the user.

### Request 2 — Get caption track URLs

**POST** `https://www.youtube.com/youtubei/v1/player?key={API_KEY}`

Headers:
```
Content-Type: application/json
User-Agent: com.google.android.youtube/20.10.38
```

Body (replace `{VIDEO_ID}` with the actual video ID string):
```json
{
  "context": {"client": {"clientName": "ANDROID", "clientVersion": "20.10.38"}},
  "videoId": "{VIDEO_ID}"
}
```

> **Critical:** `clientName` must be `"ANDROID"` and the `User-Agent` must match the Android YouTube app. The WEB client returns empty subtitles without a full browser session.

From the JSON response, navigate to `captions.playerCaptionsTracklistRenderer.captionTracks`. Each track object has:
- `baseUrl` — the subtitle download URL
- `languageCode` — e.g. `"en"`, `"es"`
- `kind` (optional) — if set to `"asr"`, the track is auto-generated

When multiple tracks exist for the same language, prefer manual (no `kind` field) over auto-generated (`kind: "asr"`).

If the `captions` field is missing entirely from the response, the video has no subtitles — tell the user.

### Request 3 — Download subtitles

Take the `baseUrl` from the chosen caption track and modify it:
1. Remove any `&fmt=srv3` substring from the URL
2. Append `&fmt=json3` to the end

**GET** the modified URL.

Headers:
```
User-Agent: com.google.android.youtube/20.10.38
```

Parse the JSON response — it contains an `events` array. For each event:
1. If the event has no `segs` array, skip it
2. Concatenate the `utf8` field from every item in `segs`
3. Strip whitespace from the result; if it is empty or just a newline, skip it
4. The event's `tStartMs` field is the timecode in milliseconds

## Troubleshooting

- **No `captions` in Request 2 response** — the video has no subtitles. Inform the user.
- **Request 2 network error** — verify the API key was extracted correctly from Request 1.
- **Wrong subtitle language** — check the full `captionTracks` array for other available tracks and pick the correct one.
- **Script exits with code 1** — read stderr and relay the message to the user.
