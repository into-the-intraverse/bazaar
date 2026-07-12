---
name: youread
description: >
  Extract YouTube video content — spoken (subtitles) AND on-screen visual information
  (slides, figures, diagrams, code, and the papers/citations/links shown on screen) — and
  save it as a self-contained Markdown source note for a personal wiki. Use this skill whenever
  the user shares a YouTube link (youtube.com/watch?v=, youtu.be/, youtube.com/shorts/) and wants
  a summary, key points, the slides/references captured, a wiki source, or any analysis of the
  video. Also trigger on "TL;DW", "what does this video say about X", "capture the slides/paper
  references", or any question paired with a YouTube URL.
---

# youread — YouTube → wiki source notes

Extract what a YouTube video says **and shows**, then save it as a Markdown source note that a
personal wiki (e.g. the atomic-wiki pipeline) can ingest later.

- **Spoken content** comes from subtitles — 3 plain HTTP requests, no downloads, no API keys, no
  external packages.
- **Visual content** — slide text, figures, diagrams, on-screen code, equations, and especially the
  **papers / citations / links shown on screen** — comes from sampling the video's frames and reading
  them. This needs two external tools (`yt-dlp`, `ffmpeg`); without them the skill still runs in
  subtitle-only mode.

youread's job ends at producing the note. It does **not** build the wiki, create atoms, or fetch any
resource the video references — that is the downstream wiki's job.

## What it produces (default)

One folder per video:

```
<dest>/
    note.md          # frontmatter + summary + Visual information + transcript notes
    transcript.md    # the raw timestamped subtitles, with the kept images woven in at their timestamps
    images/          # the curated keyframes (one per unique slide / figure) referenced by note.md
```

Destination — decide once, up front. Both branches share the `<channel-slug>/<video-slug>` shape, so
a standalone capture can later move into a wiki as a plain copy:

- If the user names a location, use it.
- Else, if the working directory's git root contains `atoms/`, `wiki/`, and `raw/` (an atomic-wiki
  repo), save to `raw/<channel-slug>/<video-slug>/` — the note lands ready for `/atomic-wiki:ingest`.
- Otherwise save to `./_youread_/<channel-slug>/<video-slug>/`.

Slugs are lowercase ASCII with words joined by hyphens — same rule for channel and title; fall back
to the video ID. Re-running for the same video replaces that folder's contents.

If the user only wants a quick answer in chat, or explicitly says "don't save", skip the file and
just respond. If they asked a specific question, answer it directly in chat in addition to saving.

## Prerequisites

| Capability | Needs | If missing |
|---|---|---|
| Subtitles / transcript | Python 3 stdlib only | always works |
| Visual extraction | `yt-dlp` + `ffmpeg` on PATH | falls back to subtitle-only; note records that visuals were skipped |

Install the visual-path tools (both are cross-platform):

- **Windows:** `winget install yt-dlp.yt-dlp` and `winget install Gyan.FFmpeg` (or `uv tool install yt-dlp`)
- **macOS:** `brew install yt-dlp ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (or your distro's package / a static build) and `uv tool install yt-dlp` (or `pipx install yt-dlp`)

YouTube extraction breaks periodically — if downloads start failing, **update yt-dlp first**
(`uv tool upgrade yt-dlp`, `pipx upgrade yt-dlp`, or `yt-dlp -U`). The script needs a recent build.

`extract_frames.py` checks for both tools and prints these hints if either is absent.

> **Note (Windows):** a freshly `winget`-installed ffmpeg may not be on PATH until the shell is
> restarted. If `ffmpeg` isn't found right after install, start a new shell.

---

## Step 1 — Fetch subtitles

```bash
python3 {SKILL_DIR}/scripts/get_subtitles.py "YOUTUBE_URL" [--lang CODE] > transcript.md
```
- `{SKILL_DIR}` is the directory containing this SKILL.md — resolve it from the path you read this file from. On Windows use `python` if `python3` is unavailable.
- Pass the full YouTube URL as-is — the script extracts the video ID internally.
- `--lang CODE` (e.g. `--lang en`) selects a subtitle language. **Pass `--lang en` when you want English**, or the language you need — when omitted, the first available track wins, which may not be the language you expect for multi-sub videos.
- **stdout:** timestamped subtitle lines, `[MM:SS] text`. Redirect to a file — this becomes
  `<dest>/transcript.md`. The destination folder isn't known until the metadata arrives, so write
  to a temporary path first and move it into `<dest>` once created. Read the file afterwards for
  the transcript content.
- **stderr:** metadata header (`# Title:`, `# Channel:`, `# Duration:`, `# Subtitles: en (manual)`) or an error message. Use these for the destination slugs and the note's frontmatter.
- **Exit 0:** success. **Exit 1:** failure — relay the stderr message.

**Fallback — if Bash is unavailable**, fetch subtitles with WebFetch via the [Manual HTTP workflow](#manual-http-workflow). (There is no manual fallback for visual extraction.)

## Step 2 — Extract visual frames

Run only when capturing visual content (the default unless the user opted out) and `yt-dlp` + `ffmpeg`
are available:

```bash
python3 {SKILL_DIR}/scripts/extract_frames.py "YOUTUBE_URL" --out "<dest>/images" \
    [--max-height 720] [--sample 2] [--max-frames 120]
```
- Point `--out` at the note's `images/` directory; the script creates it.
- It downloads a ≤`max-height` (default 720p — legible enough for small citation text) **video-only**
  copy, then captures visuals that are *held* on screen: a tiny grayscale sample every `--sample`
  seconds, near-identical stretches grouped into runs, and the **last** frame of each stable run
  extracted at full resolution (a build-up slide arrives fully revealed). Continuously-churning
  regions (webcam overlays, tickers, embedded animations) are masked out of the comparison, and
  re-shows of an earlier visual are merged into it. Constant full-frame motion (talking heads,
  b-roll) never stabilizes and is skipped automatically.
- **stdout:** a JSON manifest: `{"video": {id,title,channel,upload_date,duration,url}, "frames": [{"file","t","ts","dur"}, ...]}`. Use `video` for frontmatter and `frames[].ts` to anchor each image to its timestamp. `dur` is how many seconds the visual stayed on screen (summed over re-shows).
- **stderr:** progress + warnings. If you see `# Warning: ... exceeded --max-frames`, some visuals were dropped — re-run with a higher `--max-frames` if the video is slide-dense and you need them all.
- **If it exits 1** (tools missing, video unavailable, etc.): relay the message, continue subtitle-only, and note in the file that visuals were skipped.
- The script also accepts a **local video file path** in place of the URL (skips yt-dlp entirely).

**Cost note:** the whole video is downloaded and decoded once for the scan — for an hours-long video
that takes minutes; say so before running. The frame count that reaches you stays proportional to
*unique visuals*, not video length.

## Step 3 — Read and curate the frames

Read the candidate frames (in timestamp order from the manifest) and curate:

- **Keep** frames that carry information: slides, bullet lists, titles, **papers / citations / references shown on screen**, figures, diagrams, charts, tables, on-screen code, equations, URLs.
- **Discard** noise: talking-head shots, intros/outros, b-roll, transitions, and any near-duplicates that slipped through. The manifest's `dur` is a strong prior: long-held visuals are usually load-bearing, minimum-duration ones are often transitions.
- **Rename each kept frame** to `<ts-digits>-<short-slug>.<ext>` (e.g. `0412-attention-diagram.jpg` for a diagram at 04:12) and **delete the discarded frame files**, so `images/` ends up self-documenting and holds only the keepers.
- **Weave the keepers into the transcript** so each image sits next to the words spoken at that
  moment (downstream readers get the visual and its context together):

  ```bash
  python3 {SKILL_DIR}/scripts/link_images.py "<dest>"
  ```

  It reads the timestamp from each keeper's filename and inserts a `![...](images/...)` embed after
  the matching subtitle line in `transcript.md`. Idempotent — safe to re-run. Run it **after**
  renaming and deleting.
- For every kept frame, extract its substance, anchored to its `[MM:SS]` timestamp and cross-referenced with what the subtitles say at that moment:
  - **Slides** — title + the actual text/bullets.
  - **References & citations** — normalize each to authors, year, title, and venue/identifier (arXiv ID, DOI, journal) when visible. This is the highest-value output for a wiki source.
  - **Figures / diagrams / charts / tables** — a precise description of what they show and the takeaway.
  - **Code / commands**, **equations**, **URLs / resources** shown on screen.

## Step 4 — Compose and save the source note

Write `<dest>/note.md` (destination rules above). Omit any section that has no content.

```markdown
---
title: "<video title>"
source: "<canonical https://www.youtube.com/watch?v=… URL>"
video_id: "<id>"
channel: "<channel>"
uploaded: "<YYYY-MM-DD or omit>"
duration: "<MM:SS>"
fetched: "<today's date, YYYY-MM-DD>"
subtitles: "<lang (manual|auto-generated)>"
tags: [<a few topical tags>]
---

# <video title>

## Summary
<2–4 sentences: what the video is and its core thesis.>

## Key points
- <substantive, deduplicated takeaways — skip intros, sponsor reads, filler>

## Visual information

### Slides
- **[MM:SS] <slide title>** — <slide text / bullets>
  ![<short alt>](images/<frame file>)

### References & citations
- **<Authors> (<year>)**, "<title>" — <arXiv:…/DOI/venue if shown> — shown at [MM:SS]

### Figures & diagrams
- **[MM:SS] <what it is>** — <description + takeaway>
  ![<short alt>](images/<frame file>)

### Code / commands
- [MM:SS] `<code or command shown>`

### Links & resources shown
- [MM:SS] <URL or resource exactly as shown — recorded, not visited>

## Transcript notes
<Distilled notes from the subtitles, organized by topic (not chronology): steps, methods, numbers,
comparisons, conclusions. This is the spoken substance, complementing the visual sections above.>
```

If visuals were skipped (no tools / extraction failed), omit the **Visual information** section and add
a line under the summary: `> Visual extraction skipped (yt-dlp/ffmpeg unavailable).`

## Step 5 — Answer the user (if they asked something)

If the user asked a specific question, answer it directly in chat. Match the user's language. Tell them
where the note was saved. Keep the chat reply focused — the full detail lives in the note.

If the note was saved into an atomic-wiki repo, end with the ready-to-run next step:
`/atomic-wiki:ingest raw/<channel-slug>/<video-slug>/`. Do **not** run the ingest yourself — atom
extraction and branch approval are the user's call.

---

## Scope boundary

- youread **may** download the video's **own** stream (via `yt-dlp`) to extract and read its frames — that is the core visual-capture function.
- youread **must not** fetch, open, visit, or download any **external** resource the video *references*: papers, arXiv/DOI links, GitHub repos, packages, websites, or any URL shown on a slide. **Record** these as citations/links in the note; never resolve them. That is the downstream wiki's job.
- Do not research, fact-check, or verify the video's claims. Capture what the video says and shows, faithfully.

---

## Manual HTTP workflow

Use this only when Bash is unavailable and you must fetch **subtitles** with WebFetch or another HTTP tool. (Visual extraction has no manual fallback — it requires the scripts + tools.)

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

In the HTML response, find the value matching this regex: `"INNERTUBE_API_KEY":\s*"([^"]+)"`. This is a public key embedded in every YouTube page. If no match is found, the page structure may have changed — stop and inform the user.

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

When multiple tracks exist for the same language, prefer manual (no `kind` field) over auto-generated (`kind: "asr"`). The response's `videoDetails` also holds `title`, `author`, and `lengthSeconds` for the frontmatter. If the `captions` field is missing entirely, the video has no subtitles — tell the user.

### Request 3 — Download subtitles

Take the `baseUrl` from the chosen caption track and modify it:
1. Remove any `&fmt=srv3` substring from the URL
2. Append `&fmt=json3` to the end

**GET** the modified URL with header `User-Agent: com.google.android.youtube/20.10.38`.

Parse the JSON `events` array. For each event:
1. If the event has no `segs` array, skip it
2. Concatenate the `utf8` field from every item in `segs`
3. Strip whitespace; if empty or just a newline, skip it
4. `tStartMs` is the timecode in milliseconds

## Troubleshooting

- **`yt-dlp`/`ffmpeg` missing** — visual extraction is skipped; install per [Prerequisites](#prerequisites). Subtitles still work.
- **yt-dlp download fails / HTTP 403 / "format not available"** — the build is likely stale; update yt-dlp (`uv tool upgrade yt-dlp` / `pipx upgrade yt-dlp` / `yt-dlp -U`) and retry.
- **`# Warning: ... exceeded --max-frames`** — a slide-dense video hit the cap; re-run `extract_frames.py` with a higher `--max-frames` to capture every visual.
- **Very few frames extracted** — the video holds almost nothing still (pure talking head / continuous animation). That is by design — unstable content carries no slide-like information; a sparse periodic sample still covers it. If you expected slides, verify the video actually shows them.
- **Several frames of the same slide** — someone or something moving in front of it (e.g. a speaker at a projector) can split one visual into several runs; keep the cleanest frame during curation.
- **Frames are blurry / citations unreadable** — raise `--max-height` (e.g. `--max-height 1080`).
- **No `captions` in Request 2 response** — the video has no subtitles. Inform the user.
- **Script exits with code 1** — read stderr and relay the message.
