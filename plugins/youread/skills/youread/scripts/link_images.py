#!/usr/bin/env python3
"""
Weave curated keyframes into the transcript at their timestamps.

Reads <dest>/transcript.md (timestamped subtitle lines, "[MM:SS] text") and
<dest>/images/ (curated frames renamed to "<ts-digits>-<slug>.<ext>", e.g.
"0412-attention-diagram.jpg" for 04:12), and inserts a markdown embed after
the last subtitle line spoken at or before each image's timestamp:

    [04:10] and the attention mechanism looks like this
    ![attention diagram](images/0412-attention-diagram.jpg)
    [04:14] as you can see the keys and queries...

This anchors every image in its spoken context, so downstream readers
(e.g. a wiki ingest) find the visual and the words together. Idempotent —
images already referenced in the transcript are skipped.

Usage:
    python3 link_images.py <dest-folder>

stderr: how many embeds were inserted / skipped. Exit 0 on success,
1 when <dest>/transcript.md is missing.
"""

import os
import re
import sys

SUB_LINE = re.compile(r"^\[(\d+):(\d{2})\]")
IMAGE_NAME = re.compile(r"^(\d{4,})-(.+)\.(jpg|jpeg|png)$", re.IGNORECASE)


def main():
    if len(sys.argv) != 2:
        print("Usage: link_images.py <dest-folder>", file=sys.stderr)
        sys.exit(1)
    dest = sys.argv[1]
    transcript_path = os.path.join(dest, "transcript.md")
    images_dir = os.path.join(dest, "images")
    if not os.path.isfile(transcript_path):
        print(f"No transcript found at {transcript_path}", file=sys.stderr)
        sys.exit(1)

    with open(transcript_path, encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()

    images = []  # (t_seconds, filename, slug)
    if os.path.isdir(images_dir):
        for name in sorted(os.listdir(images_dir)):
            m = IMAGE_NAME.match(name)
            if m:
                digits = m.group(1)
                t = int(digits[:-2]) * 60 + int(digits[-2:])
                images.append((t, name, m.group(2).replace("-", " ")))
    if not images:
        print("No timestamp-named images to link.", file=sys.stderr)
        return

    subs = []  # (line_index, t_seconds)
    for i, line in enumerate(lines):
        m = SUB_LINE.match(line)
        if m:
            subs.append((i, int(m.group(1)) * 60 + int(m.group(2))))

    inserts = {}  # line index -> [embed lines]; -1 = top of file
    skipped = 0
    for t, name, slug in sorted(images):
        if name in text:
            skipped += 1
            continue
        pos = -1
        for i, st in subs:
            if st <= t:
                pos = i
            else:
                break
        inserts.setdefault(pos, []).append(f"![{slug}](images/{name})")

    out = list(inserts.get(-1, []))
    for i, line in enumerate(lines):
        out.append(line)
        out.extend(inserts.get(i, []))

    with open(transcript_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    n = sum(len(v) for v in inserts.values())
    print(f"Linked {n} image(s) into {transcript_path}"
          + (f" ({skipped} already present)" if skipped else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
