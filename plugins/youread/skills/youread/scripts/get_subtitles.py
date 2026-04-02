#!/usr/bin/env python3
"""
Extract subtitles from a YouTube video using only the standard library.
No API keys or external packages required.

Usage:
    python get_subtitles.py <youtube_url_or_video_id> [--lang CODE]

Output: timestamped subtitle lines to stdout.
Exit code 1 + message to stderr if subtitles are unavailable.
"""

import json
import re
import sys
import urllib.request
import urllib.error


def extract_video_id(url_or_id):
    """Extract VIDEO_ID from various YouTube URL formats or a bare ID."""
    if re.fullmatch(r"[\w-]{11}", url_or_id):
        return url_or_id

    patterns = [
        r"(?:youtube\.com/watch\?.*?v=)([\w-]{11})",
        r"(?:youtu\.be/)([\w-]{11})",
        r"(?:youtube\.com/shorts/)([\w-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            return m.group(1)
    return None


def fetch_api_key(video_id):
    """Fetch the public INNERTUBE_API_KEY from the YouTube watch page."""
    req = urllib.request.Request(
        f"https://www.youtube.com/watch?v={video_id}",
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US"},
    )
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
    m = re.search(r'"INNERTUBE_API_KEY":\s*"([^"]+)"', html)
    if not m:
        raise RuntimeError("Could not find INNERTUBE_API_KEY on the YouTube page.")
    return m.group(1)


def fetch_caption_tracks(video_id, api_key):
    """Call the InnerTube player endpoint to get available caption tracks."""
    payload = json.dumps({
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.38",
            }
        },
        "videoId": video_id,
    }).encode()

    req = urllib.request.Request(
        f"https://www.youtube.com/youtubei/v1/player?key={api_key}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/20.10.38",
        },
    )
    data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

    captions = data.get("captions")
    if not captions:
        return []
    renderer = captions.get("playerCaptionsTracklistRenderer")
    if not renderer:
        return []
    return renderer.get("captionTracks", [])


def pick_track(tracks, preferred_lang=None):
    """Pick the best subtitle track: prefer manual over ASR, optionally filter by language."""
    if not tracks:
        return None

    candidates = tracks
    if preferred_lang:
        lang_matches = [t for t in tracks if t.get("languageCode", "").startswith(preferred_lang)]
        if lang_matches:
            candidates = lang_matches

    # Prefer manual (no kind=asr) over auto-generated
    manual = [t for t in candidates if t.get("kind") != "asr"]
    return manual[0] if manual else candidates[0]


def fetch_subtitles(track):
    """Download subtitle text from a caption track and return timestamped lines."""
    base_url = track["baseUrl"]
    # Ensure json3 format
    sub_url = base_url.replace("&fmt=srv3", "") + "&fmt=json3"
    req = urllib.request.Request(
        sub_url,
        headers={"User-Agent": "com.google.android.youtube/20.10.38"},
    )
    sub_data = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())

    lines = []
    for ev in sub_data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        ms = ev.get("tStartMs", 0)
        mm = ms // 60000
        ss = (ms % 60000) // 1000
        lines.append(f"[{mm:02d}:{ss:02d}] {text}")
    return lines


def main():
    if len(sys.argv) < 2:
        print("Usage: get_subtitles.py <youtube_url_or_video_id> [--lang CODE]", file=sys.stderr)
        sys.exit(1)

    url_or_id = sys.argv[1]
    preferred_lang = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        if idx + 1 < len(sys.argv):
            preferred_lang = sys.argv[idx + 1]

    video_id = extract_video_id(url_or_id)
    if not video_id:
        print(f"Error: could not extract video ID from '{url_or_id}'", file=sys.stderr)
        sys.exit(1)

    api_key = fetch_api_key(video_id)
    tracks = fetch_caption_tracks(video_id, api_key)

    if not tracks:
        print("No subtitles available for this video.", file=sys.stderr)
        sys.exit(1)

    track = pick_track(tracks, preferred_lang)
    if not track:
        print(f"No subtitles found for language '{preferred_lang}'.", file=sys.stderr)
        sys.exit(1)

    lang = track.get("languageCode", "unknown")
    kind = "auto-generated" if track.get("kind") == "asr" else "manual"
    print(f"# Subtitles: {lang} ({kind})", file=sys.stderr)

    lines = fetch_subtitles(track)
    print("\n".join(lines))


if __name__ == "__main__":
    main()