#!/usr/bin/env python3
"""Utilities for downloading AI Startup School subtitles and formatting them into blog posts.

This script shells out to `yt-dlp` to grab English auto captions for each video listed in
`public/posts/posts.json`. It converts the resulting `.vtt` file into a Markdown document that
matches the blog's conventions: a summary block at the top, speaker sections rendered as `###`
headings, and timestamps shown using `<small>` tags.

Examples
--------
# Fetch and rewrite every post listed in posts.json
python scripts/fetch_ai_startup_school.py

# Only fetch one slug and keep the current summary text
python scripts/fetch_ai_startup_school.py --slug andrej-karpathy-software-is-changing-again

# Preview the generated Markdown without touching the file
python scripts/fetch_ai_startup_school.py --slug andrej-karpathy-software-is-changing-again --dry-run
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
POSTS_JSON = ROOT / "public" / "posts" / "posts.json"
POSTS_DIR = ROOT / "public" / "posts"
CACHE_DIR = ROOT / ".cache" / "ai_startup_school"

TIMESTAMP_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})(?:\.(\d{3}))?$")
SPEAKER_PATTERN = re.compile(r"^([A-Z][\w .'-]{0,60}?)(?:\s*[\-–—])?\s*:\s*(.*)")
NOISE_PATTERN = re.compile(r"^\[.*?\]$")


@dataclass
class Cue:
    start: float  # seconds
    text: str


@dataclass
class Segment:
    start: float
    speaker: Optional[str]
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download AI Startup School subtitles and format Markdown posts")
    parser.add_argument("--slug", action="append", help="Only process the given slug(s). Can be repeated.")
    parser.add_argument("--skip-download", action="store_true", help="Assume subtitles already exist in the cache and only reformat the Markdown")
    parser.add_argument("--force", action="store_true", help="Overwrite existing post content without prompting")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated Markdown instead of writing the post file")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help="Directory to store downloaded caption files")
    parser.add_argument("--yt-dlp", default="yt-dlp", help="Path to the yt-dlp executable")
    return parser.parse_args()


def load_posts() -> dict[str, dict]:
    if not POSTS_JSON.exists():
        sys.exit(f"posts.json not found at {POSTS_JSON}")
    with POSTS_JSON.open("r", encoding="utf-8") as fh:
        posts = json.load(fh)
    return {entry["slug"]: entry for entry in posts}


def seconds_from_timestamp(raw: str) -> float:
    match = TIMESTAMP_PATTERN.match(raw)
    if not match:
        raise ValueError(f"Unsupported VTT timestamp: {raw}")
    hours, minutes, seconds, millis = match.groups(default="0")
    total = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000
    return total


def format_timestamp(seconds: float) -> str:
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, sec = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def download_subtitles(yt_dlp: str, url: str, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    cmd = [
        yt_dlp,
        "--write-auto-subs",
        "--skip-download",
        "--sub-lang",
        "en",
        "--sub-format",
        "vtt",
        "--no-overwrites",
        "--output",
        "%(id)s",
        url,
    ]
    try:
        result = subprocess.run(cmd, cwd=destination, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit(f"yt-dlp not found (looked for '{yt_dlp}'). Install it or pass --yt-dlp with the correct path.")
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stdout)
        sys.stderr.write(exc.stderr)
        raise SystemExit(f"yt-dlp failed for {url} (exit code {exc.returncode}).")

    for path in destination.glob("*.en.vtt"):
        return path
    raise SystemExit(f"No English auto subtitle (.en.vtt) found in {destination} after running yt-dlp.")


def parse_vtt(path: Path) -> List[Cue]:
    cues: List[Cue] = []
    start: Optional[float] = None
    lines: List[str] = []
    last_text: Optional[str] = None

    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                if start is not None and lines:
                    text = clean_text(" ".join(lines))
                    if text:
                        normalized = text.casefold()
                        if normalized != last_text:
                            cues.append(Cue(start, text))
                            last_text = normalized
                start = None
                lines = []
                continue
            if line.startswith("WEBVTT") or line.startswith("NOTE"):
                continue
            if "-->" in line:
                start_part = line.split("-->", 1)[0].strip()
                start = seconds_from_timestamp(start_part)
                lines = []
                continue
            lines.append(line)

    if start is not None and lines:
        text = clean_text(" ".join(lines))
        if text:
            normalized = text.casefold()
            if normalized != last_text:
                cues.append(Cue(start, text))
    return cues


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)  # strip any lingering tags
    text = text.replace("♪", "").replace("♪", "")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    if NOISE_PATTERN.match(text):
        return ""
    return text


def cues_to_segments(cues: Iterable[Cue]) -> List[Segment]:
    segments: List[Segment] = []
    for cue in cues:
        text = cue.text
        if not text:
            continue
        speaker, remaining = split_speaker(text)
        if not remaining:
            remaining = text if speaker else text
        if not remaining:
            continue
        remaining = normalize_sentence(remaining)
        if not remaining:
            continue
        if segments and segments[-1].speaker == speaker:
            previous = segments[-1]
            merged = merge_segment_text(previous.text, remaining)
            if merged == previous.text:
                continue
            segments[-1] = Segment(previous.start, speaker, merged)
        else:
            segments.append(Segment(cue.start, speaker, remaining))
    return segments


def split_speaker(text: str) -> tuple[Optional[str], str]:
    candidate = SPEAKER_PATTERN.match(text)
    if candidate:
        speaker = candidate.group(1).strip()
        speech = candidate.group(2).strip()
        if speaker.upper() in {"[MUSIC]", "[LAUGHTER]"}:
            return None, speech
        speaker = tidy_speaker_name(speaker)
        return speaker, speech
    return None, text


def tidy_speaker_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name


def normalize_sentence(text: str) -> str:
    text = text.strip()
    if text.startswith("- "):
        text = text[2:]
    text = text.strip()
    text = collapse_repetitions(text)
    return text


def collapse_repetitions(text: str) -> str:
    """Heuristically collapse consecutive duplicate sentences.

    Auto-generated subtitles often repeat the same sentence multiple times as
    the speaker continues. We split on sentence boundaries and drop adjacent
    duplicates (case-insensitive) to keep the transcript readable.
    """

    if not text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= 1:
        return text
    deduped: List[str] = []
    previous: Optional[str] = None
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        normalized = stripped.lower()
        if normalized == previous:
            continue
        deduped.append(stripped)
        previous = normalized
    return " ".join(deduped) if deduped else text


def merge_segment_text(existing: str, addition: str) -> str:
    if not addition:
        return existing
    if not existing:
        return addition

    existing_norm = existing.strip().casefold()
    addition_norm = addition.strip().casefold()

    if addition_norm == existing_norm:
        return existing
    if existing_norm in addition_norm:
        return addition
    if addition_norm in existing_norm:
        return existing

    overlap = longest_overlap(existing, addition)
    if overlap:
        remainder = addition[len(overlap):].lstrip()
        if not remainder:
            return existing
        return f"{existing} {remainder}".strip()

    return f"{existing} {addition}".strip()


def longest_overlap(existing: str, addition: str) -> str:
    existing_lower = existing.lower()
    addition_lower = addition.lower()
    max_len = min(len(existing_lower), len(addition_lower))
    for length in range(max_len, 0, -1):
        if existing_lower.endswith(addition_lower[:length]):
            return addition[:length]
    return ""


def read_existing_summary(path: Path) -> str:
    if not path.exists():
        return "這支影片的重點摘要待補充。"
    content = path.read_text(encoding="utf-8")
    match = re.search(r"<!-- summary -->(.*?)<!-- endsummary -->", content, flags=re.DOTALL)
    if match:
        summary = match.group(1).strip()
        if summary:
            return summary
    return "這支影片的重點摘要待補充。"


def build_markdown(entry: dict, segments: List[Segment], existing_summary: str, fallback_speaker: Optional[str]) -> str:
    parts: List[str] = []
    parts.append("<!-- summary -->")
    parts.append(existing_summary.strip())
    parts.append("<!-- endsummary -->")
    parts.append("")
    video_url = entry.get("cover") or entry.get("url")
    if video_url:
        parts.append(f"<small>原始影片：[{video_url}]({video_url})</small>")
        parts.append("")
    for segment in segments:
        timestamp = format_timestamp(segment.start)
        speaker = segment.speaker or fallback_speaker
        if speaker:
            parts.append(f"### {speaker} <small>[{timestamp}]</small>")
            parts.append(segment.text)
        else:
            parts.append(f"<small>[{timestamp}]</small> {segment.text}")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def write_post(slug: str, content: str, force: bool, dry_run: bool) -> None:
    post_path = POSTS_DIR / f"{slug}.md"
    if dry_run:
        sys.stdout.write(f"\n--- {slug} ---\n")
        sys.stdout.write(content)
        sys.stdout.write("\n")
        return
    if post_path.exists() and not force:
        backup = post_path.with_suffix(".md.bak")
        if not backup.exists():
            shutil.copy2(post_path, backup)
            print(f"Created backup at {backup}")
    post_path.write_text(content, encoding="utf-8")
    print(f"Wrote {post_path}")


def ensure_cache_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def infer_primary_speaker(entry: dict) -> Optional[str]:
    tags = entry.get("tags")
    if isinstance(tags, list):
        for candidate in reversed(tags):
            if not isinstance(candidate, str):
                continue
            stripped = candidate.strip()
            if not stripped:
                continue
            if stripped in {"AI Startup School", "Y Combinator"}:
                continue
            return stripped
    title = entry.get("title")
    if isinstance(title, str) and title:
        parts = [part.strip() for part in re.split(r"[:：]", title) if part.strip()]
        if parts:
            return parts[-1]
    return None


def main() -> None:
    args = parse_args()
    ensure_cache_dir(args.cache_dir)
    posts = load_posts()

    target_slugs: Iterable[str]
    if args.slug:
        missing = [slug for slug in args.slug if slug not in posts]
        if missing:
            sys.exit(f"Unknown slug(s): {', '.join(missing)}")
        target_slugs = args.slug
    else:
        target_slugs = sorted(posts.keys())

    for slug in target_slugs:
        entry = posts[slug]
        url = entry.get("cover") or entry.get("url")
        if not url:
            print(f"Skipping {slug}: no video URL found", file=sys.stderr)
            continue
        cache_bucket = args.cache_dir / slug
        if args.skip_download:
            candidates = sorted(cache_bucket.glob("*.en.vtt"))
            if not candidates:
                print(f"No cached subtitles for {slug}; run without --skip-download first.", file=sys.stderr)
                continue
            vtt_path = candidates[-1]
        else:
            vtt_path = download_subtitles(args.yt_dlp, url, cache_bucket)
        cues = parse_vtt(vtt_path)
        segments = cues_to_segments(cues)
        if not segments:
            print(f"No transcript segments produced for {slug}; skipping.", file=sys.stderr)
            continue
        summary = read_existing_summary(POSTS_DIR / f"{slug}.md")
        primary_speaker = infer_primary_speaker(entry)
        markdown = build_markdown(entry, segments, summary, primary_speaker)
        write_post(slug, markdown, force=args.force, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
