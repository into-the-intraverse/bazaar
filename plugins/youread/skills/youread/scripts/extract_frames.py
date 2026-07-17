#!/usr/bin/env python3
"""
Extract slide / figure keyframes from a YouTube video (or a local video file).

Two passes, built on the observation that informational visuals (slides,
figures, code, charts) are *held* on screen while non-informational content
(talking heads, b-roll) churns continuously:

  Pass 1 — cheap scan, no image files. ffmpeg decodes the video into tiny
  grayscale frames (one per --sample seconds, GRID x GRID pixels) piped to
  this process. Consecutive samples that stay near-identical form a "run";
  every run held >= MIN_STABLE_SAMPLES yields one candidate: its LAST
  sample, so a build-up slide is captured fully revealed. Cells that churn
  continuously (webcam overlays, tickers, embedded animations) are masked
  out of the comparison, and a candidate that re-shows an earlier visual
  (speaker cutting back to the same slide) is merged into it, accumulating
  its on-screen duration. A sparse periodic floor covers videos that never
  stabilize.

  Pass 2 — one accurate ffmpeg seek per kept candidate writes the
  full-resolution frame.

Pure orchestration of external CLI tools + stdlib. Requires ffmpeg on PATH
(always) and yt-dlp on PATH (for URLs; a local file path skips it).

Usage:
    python3 extract_frames.py <youtube_url_or_id_or_local_file> --out DIR
        [--max-height 720] [--sample 2] [--max-frames 120] [--fmt jpg|png]

stdout: a JSON manifest:
    {"video": {id, title, channel, upload_date, duration, url},
     "frames": [{"file": "...", "t": 12.5, "ts": "00:12", "dur": 40.0}, ...]}
    dur = seconds this visual stayed on screen (summed over re-shows) — a
    curation signal: long-held frames are usually load-bearing.
stderr: progress and warnings. Exit 0 on success, 1 on failure.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

# Scan constants, calibrated on synthetic slide videos with a harsh
# continuously-animating 14%-area overlay (worst-case webcam PiP): overlay
# churn alone changed <= ~2% of masked cells between samples, while a
# one-bullet slide edit changed >= ~6% and a slide flip >= ~25%.
GRID = 32                # scan resolution: 32x32 = 1024 cells per sample
CELL_DELTA = 12          # gray-level delta for a cell to count as changed
CHANGE_FRAC = 0.04       # changed fraction of non-volatile cells => new visual
WINDOW = 6               # intervals of churn history kept per cell
VOLATILE_MIN = 3         # changed in >= this many of WINDOW => volatile cell
MIN_STABLE_SAMPLES = 2   # shorter runs are transitions, dropped
FLOOR_S = 60             # emit a sample at least this often if nothing stabilizes

INSTALL_HINTS = """\
This step needs yt-dlp and ffmpeg on PATH. Install them:
  Windows : winget install yt-dlp.yt-dlp ; winget install Gyan.FFmpeg
  macOS   : brew install yt-dlp ffmpeg
  Linux   : sudo apt install ffmpeg && uv tool install yt-dlp
            (or use your distro's packages / a static ffmpeg build)
Without them, youread still works in subtitle-only mode."""


def require_tools(need_ytdlp):
    import shutil
    tools = ["ffmpeg"] + (["yt-dlp"] if need_ytdlp else [])
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        print(f"Missing required tool(s): {', '.join(missing)}.", file=sys.stderr)
        print(INSTALL_HINTS, file=sys.stderr)
        sys.exit(1)


def fmt_ts(seconds):
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def fetch_metadata(url):
    """Get video metadata via yt-dlp without downloading the stream."""
    proc = subprocess.run(
        ["yt-dlp", "--no-playlist", "--skip-download", "--dump-single-json", url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print("yt-dlp could not read the video:", file=sys.stderr)
        print(proc.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    info = json.loads(proc.stdout)
    upload = info.get("upload_date")  # YYYYMMDD
    if upload and len(upload) == 8:
        upload = f"{upload[:4]}-{upload[4:6]}-{upload[6:]}"
    dur = info.get("duration")
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("uploader") or info.get("channel"),
        "upload_date": upload,
        "duration": fmt_ts(dur) if dur else None,
        "url": info.get("webpage_url") or url,
    }


def local_metadata(path):
    """Metadata for a local video file (ffprobe for duration, best effort)."""
    dur = None
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            dur = float(proc.stdout.strip())
    except OSError:
        pass
    stem = os.path.splitext(os.path.basename(path))[0]
    return {
        "id": stem,
        "title": stem,
        "channel": None,
        "upload_date": None,
        "duration": fmt_ts(dur) if dur else None,
        "url": os.path.abspath(path),
    }


def download_video(url, tmpdir, max_height):
    """Download a video-only, height-capped stream; return its path.

    yt-dlp downloads the whole stream natively (with the headers YouTube
    requires) rather than handing a byte-range URL to ffmpeg — the latter
    triggers 403s.
    """
    fmt = f"bv*[height<={max_height}]/b[height<={max_height}]/bv*/b"
    out_tmpl = os.path.join(tmpdir, "source.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "-f", fmt, "-o", out_tmpl, url]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("yt-dlp failed to download the video stream:", file=sys.stderr)
        print(proc.stderr.strip(), file=sys.stderr)
        sys.exit(1)
    files = sorted(glob.glob(os.path.join(tmpdir, "source.*")))
    if not files:
        print("yt-dlp reported success but produced no file.", file=sys.stderr)
        sys.exit(1)
    return files[0]


def scan_video(video_path, sample_s):
    """Pass 1 decode: return the video as a list of GRID*GRID gray frames."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video_path,
         "-vf", f"fps=1/{sample_s},scale={GRID}:{GRID}:flags=area,format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True,
    )
    if proc.returncode != 0:
        print("ffmpeg failed while scanning the video:", file=sys.stderr)
        print(proc.stderr.decode(errors="replace").strip()[-2000:], file=sys.stderr)
        sys.exit(1)
    raw, n = proc.stdout, GRID * GRID
    return [raw[i:i + n] for i in range(0, len(raw) - n + 1, n)]


def diff_cells(a, b):
    return {i for i in range(GRID * GRID) if abs(a[i] - b[i]) > CELL_DELTA}


def select_candidates(frames, sample_s):
    """Group samples into stable runs; return kept visuals with t and dur."""
    ncells = GRID * GRID
    kept = []            # {"frame", "t", "dur", "volatile"}
    changed_hist = []    # per interval: set of cells changed vs previous sample
    volatile = set()
    last_emit_t = 0.0

    def merge_or_keep(rep, t, dur):
        nonlocal last_emit_t
        last_emit_t = t
        for k in kept:
            mask = volatile | k["volatile"]
            usable = ncells - len(mask)
            if usable == 0:
                continue
            d = sum(1 for c in diff_cells(rep, k["frame"]) if c not in mask)
            if d / usable <= CHANGE_FRAC:
                k["dur"] += dur   # same visual shown again — merge
                return
        kept.append({"frame": rep, "t": t, "dur": dur, "volatile": set(volatile)})

    run_start = 0
    anchor = frames[0]
    prev = frames[0]

    def close_run(end_idx):
        nsamples = end_idx - run_start + 1
        if nsamples >= MIN_STABLE_SAMPLES:
            merge_or_keep(frames[end_idx], end_idx * sample_s, nsamples * sample_s)

    for i in range(1, len(frames)):
        cur = frames[i]
        # churn mask: cells that changed in >= VOLATILE_MIN of the last
        # WINDOW consecutive intervals (a one-shot slide flip never qualifies)
        counts = {}
        for s in changed_hist[-WINDOW:]:
            for c in s:
                counts[c] = counts.get(c, 0) + 1
        volatile = {c for c, n in counts.items() if n >= VOLATILE_MIN}

        usable = ncells - len(volatile)
        moved = sum(1 for c in diff_cells(cur, anchor) if c not in volatile)
        if usable and moved / usable > CHANGE_FRAC:
            close_run(i - 1)
            run_start, anchor = i, cur

        if i * sample_s - last_emit_t >= FLOOR_S:
            merge_or_keep(cur, i * sample_s, sample_s)

        changed_hist.append(diff_cells(cur, prev))
        prev = cur

    close_run(len(frames) - 1)

    if not kept and frames:
        mid = len(frames) // 2
        kept.append({"frame": frames[mid], "t": mid * sample_s,
                     "dur": sample_s, "volatile": set()})
    return sorted(kept, key=lambda k: k["t"])


def cap_candidates(cands, max_frames):
    """Evenly thin the candidate list to max_frames (before any extraction)."""
    if len(cands) <= max_frames:
        return cands
    step = len(cands) / max_frames
    kept = [cands[int(i * step)] for i in range(max_frames)]
    print(
        f"# Warning: {len(cands)} unique visuals exceeded --max-frames={max_frames}; "
        f"kept {len(kept)} evenly spaced. Some slides may be missing — "
        f"re-run with a higher --max-frames to capture all.",
        file=sys.stderr,
    )
    return kept


def extract_full_frames(video_path, cands, out_dir, fmt):
    """Pass 2: seek-extract each candidate at full resolution."""
    results = []
    for idx, k in enumerate(cands, 1):
        out = os.path.join(out_dir, f"frame_{idx:05d}.{fmt}")
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-ss", f"{k['t']:.3f}", "-i", video_path,
             "-frames:v", "1", "-q:v", "2", "-y", out],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not os.path.exists(out):
            print(f"# Warning: failed to extract frame at t={k['t']:.1f}s; skipped.",
                  file=sys.stderr)
            continue
        results.append((out, k))
    return results


def main():
    ap = argparse.ArgumentParser(
        description="Extract slide/figure keyframes from a YouTube video or local file."
    )
    ap.add_argument("url", help="YouTube URL / video ID, or a local video file path")
    ap.add_argument("--out", required=True, help="output directory for frames")
    ap.add_argument("--max-height", type=int, default=720,
                    help="cap video resolution (default 720)")
    ap.add_argument("--sample", type=float, default=2,
                    help="scan one frame every N seconds (default 2)")
    ap.add_argument("--max-frames", type=int, default=120,
                    help="max frames to keep (default 120)")
    ap.add_argument("--fmt", default="jpg", choices=("jpg", "png"),
                    help="frame image format")
    args = ap.parse_args()

    is_local = os.path.isfile(args.url)
    require_tools(need_ytdlp=not is_local)
    os.makedirs(args.out, exist_ok=True)

    if is_local:
        meta = local_metadata(args.url)
    else:
        meta = fetch_metadata(args.url)
    print(f"# Video: {meta['title']} — {meta['channel'] or 'local file'}", file=sys.stderr)

    with tempfile.TemporaryDirectory(prefix="youread-dl-") as tmpdir:
        video_path = args.url if is_local else download_video(args.url, tmpdir, args.max_height)
        frames = scan_video(video_path, args.sample)
        if not frames:
            print("No frames could be decoded from the video.", file=sys.stderr)
            sys.exit(1)
        cands = select_candidates(frames, args.sample)
        print(f"# Scan: {len(frames)} samples -> {len(cands)} unique visuals",
              file=sys.stderr)
        cands = cap_candidates(cands, args.max_frames)
        pairs = extract_full_frames(video_path, cands, args.out, args.fmt)

    manifest = {
        "video": meta,
        "frames": [
            {"file": os.path.abspath(p), "t": round(k["t"], 2),
             "ts": fmt_ts(k["t"]), "dur": round(k["dur"], 1)}
            for p, k in pairs
        ],
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"# Extracted {len(pairs)} candidate frames to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
