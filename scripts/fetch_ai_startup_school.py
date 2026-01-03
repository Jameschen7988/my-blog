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
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
POSTS_JSON = ROOT / "public" / "posts" / "posts.json"
POSTS_DIR = ROOT / "public" / "posts"
CACHE_DIR = ROOT / ".cache" / "ai_startup_school"

TRANSLATION_EDITOR_PROMPT = """你是一位具有 20 年以上經驗的專業翻譯與內容編輯，
長期從事【知識型文章、深度分析、專訪與評論】的中英翻譯與在地化改寫。

你的任務不是逐字翻譯，而是將原文轉換為：
「適合台灣繁體中文讀者閱讀、可直接刊登於知識型網站的成熟內容」。

請嚴格遵守以下規範：

【一、內容定位與讀者】
- 內容類型：知識型 / 深度內容（非新聞快訊、非口語字幕）
- 目標讀者：具閱讀能力的一般讀者，重視理解與邏輯，而非娛樂性
- 發布情境：文章頁面（長文、段落清楚，可反覆閱讀）

【二、翻譯核心原則】
- 以「意義、邏輯與可讀性」優先於原文句型
- 允許重組語序、拆分或合併句子
- 必須消除英文句法直接映射到中文的翻譯痕跡
- 中文閱讀時應感覺自然、成熟，而非「翻譯作品」

【三、語言與風格要求（台灣繁中）】
- 使用台灣常見且中性的繁體中文
- 避免中國用語（例如：赋能、抓手、落地、闭环、赋值）
- 避免過度口語、網路語或情緒化表述
- 語氣理性、穩定、清楚，不煽情、不說教

【四、允許的專業編輯行為】
- 將口語英文轉為自然的書面中文
- 補出中文理解所需但原文省略的主詞或邏輯連接
- 壓縮重複或空泛的表述，使段落更精煉
- 在不改變原意的前提下，使段落邏輯更清楚

【五、嚴格禁止事項】
- 不可新增原文未提及的觀點、評論或背景
- 不可自行下結論、延伸或評價作者立場
- 不可使用行銷文案或宣傳式語言
- 不可留下逐字對應、直譯痕跡或翻譯腔

【六、輸出格式】
- 僅輸出最終優化後的繁體中文內容
- 不附加任何說明、註解、分析或對照
"""

TIMESTAMP_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})(?:\.(\d{3}))?$")
SPEAKER_PATTERN = re.compile(r"^([A-Z][\w .'-]{0,60}?)(?:\s*[\-–—])?\s*:\s*(.*)")
NOISE_PATTERN = re.compile(r"^\[.*?\]$")


def has_chinese_chars(text: str) -> bool:
    """Check if the text contains Traditional/Simplified Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


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
    parser.add_argument("--crawl-playlist", help="YouTube Playlist URL to crawl for new videos and update posts.json")
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
    
    # 1. Try downloading Chinese subtitles first
    cmd = [
        yt_dlp,
        "--write-auto-subs",
        "--skip-download",
        "--sub-lang",
        "zh-Hant,zh-TW,zh",
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
        # Don't exit yet, we will try English
        pass

    for path in destination.glob("*.zh*.vtt"):
        return path
    
    # 2. Fallback: Try downloading English subtitles
    print(f"Chinese subtitles not found for {url}, trying English fallback...", file=sys.stderr)
    cmd[4] = "en"  # Change --sub-lang to en
    try:
        subprocess.run(cmd, cwd=destination, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        raise RuntimeError(f"yt-dlp failed for {url} (exit code {exc.returncode}).")

    for path in destination.glob("*.en.vtt"):
        return path
        
    raise RuntimeError(f"No subtitles found for {url}. Ensure the video has captions.")


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
        if segments and segments[-1].speaker == speaker and len(segments[-1].text) < 2500:
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
        if summary and has_chinese_chars(summary):
            return summary
    return "這支影片的重點摘要待補充。"


def generate_ai_summary(text_content: str) -> str:
    """Generate a summary using OpenAI if available."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "這支影片的重點摘要待補充。（請設定 OPENAI_API_KEY 以自動生成）"
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Take the first ~4000 chars to generate a summary to save tokens/time
        prompt = f"請根據以下逐字稿內容，生成一段約 3-5 點的繁體中文重點摘要，並在開頭包含一段簡短的總結。格式請參考：\n\n總結...\n\n重點：\n1. ...\n\n逐字稿：\n{text_content[:4000]}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if "insufficient_quota" in str(e):
            sys.exit(f"❌ Critical Error: OpenAI API quota exceeded. Script aborted to prevent overwriting with English content.\nPlease check billing at https://platform.openai.com/settings/organization/billing/overview")
        print(f"Failed to generate summary: {e}", file=sys.stderr)
        return "這支影片的重點摘要待補充。（生成失敗）"


def translate_batch(texts: List[str]) -> List[str]:
    """Translate a list of strings to Traditional Chinese using OpenAI efficiently."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return texts
    
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    translated = []
    # Batch size to balance context window and speed
    batch_size = 20
    
    print(f"Translating {len(texts)} segments...", file=sys.stderr)
    for i in range(0, len(texts), batch_size):
        print(f"  Batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}...", file=sys.stderr)
        batch = texts[i:i+batch_size]
        
        # Optimization: If only one segment, translate directly to avoid formatting issues
        if len(batch) == 1:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a professional translator. Translate the following text to Traditional Chinese (Taiwan). Return ONLY the translated text, no other commentary."},
                            {"role": "user", "content": batch[0]}
                        ]
                    )
                    translated.append(response.choices[0].message.content.strip())
                    break # Success
                except Exception as e:
                    if "insufficient_quota" in str(e):
                        sys.exit(f"❌ Critical Error: OpenAI API quota exceeded during batch translation. Script aborted.")
                    if attempt < max_retries - 1:
                        print(f"Translation failed (attempt {attempt+1}/{max_retries}): {e}. Retrying...", file=sys.stderr)
                        time.sleep(2)
                    else:
                        print(f"Translation failed after {max_retries} attempts: {e}", file=sys.stderr)
                        translated.append(batch[0])
            continue

        # Use a delimiter to separate segments in the prompt
        prompt_text = "\n".join(f"SEGMENT_{idx}: {text}" for idx, text in enumerate(batch))
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Translate the following text to Traditional Chinese (Taiwan). Maintain the format 'SEGMENT_index: translated_text'."},
                        {"role": "user", "content": prompt_text}
                    ]
                )
                content = response.choices[0].message.content.strip()
                
                # Parse the response back into a list
                batch_map = {}
                for line in content.splitlines():
                    match = re.match(r"SEGMENT_(\d+):\s*(.*)", line)
                    if match:
                        batch_map[int(match.group(1))] = match.group(2)
                
                # Reconstruct batch, falling back to original if translation missing
                for idx in range(len(batch)):
                    translated.append(batch_map.get(idx, batch[idx]))
                break # Success
            except Exception as e:
                if "insufficient_quota" in str(e):
                    sys.exit(f"❌ Critical Error: OpenAI API quota exceeded during batch translation. Script aborted.")
                
                if attempt < max_retries - 1:
                    print(f"Batch translation failed (attempt {attempt+1}/{max_retries}): {e}. Retrying...", file=sys.stderr)
                    time.sleep(2)
                else:
                    print(f"Batch translation failed after {max_retries} attempts: {e}", file=sys.stderr)
                    translated.extend(batch)
            
    return translated


def build_markdown(entry: dict, segments: List[Segment], existing_summary: str, fallback_speaker: Optional[str]) -> str:
    if "待補充" in existing_summary:
        # Combine segments to form text for summarization
        full_text = " ".join([s.text for s in segments])
        if full_text and os.environ.get("OPENAI_API_KEY"):
            print(f"Generating AI summary for {entry.get('slug')}...")
            existing_summary = generate_ai_summary(full_text)

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


def slugify(text: str) -> str:
    """Convert a string to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text).strip('-_')
    return text


def translate_to_chinese(text: str) -> str:
    """Translate text to Traditional Chinese using OpenAI."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return text
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the following text to Traditional Chinese (Taiwan). Keep the tone professional."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if "insufficient_quota" in str(e):
            sys.exit(f"❌ Critical Error: OpenAI API quota exceeded. Script aborted.")
        print(f"Translation failed: {e}", file=sys.stderr)
        return text


def crawl_playlist(yt_dlp: str, playlist_url: str) -> None:
    """Fetch video metadata from a YouTube playlist and update posts.json."""
    print(f"Crawling playlist: {playlist_url}...")
    
    # Fetch playlist metadata using yt-dlp
    cmd = [
        yt_dlp,
        "--dump-single-json",
        "--flat-playlist",
        playlist_url,
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        playlist_data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        sys.exit(f"Failed to crawl playlist: {e}")

    if not POSTS_JSON.exists():
        current_posts = []
    else:
        with POSTS_JSON.open("r", encoding="utf-8") as fh:
            current_posts = json.load(fh)

    existing_urls = {p.get("cover") for p in current_posts if p.get("cover")}
    existing_slugs = {p.get("slug") for p in current_posts if p.get("slug")}
    
    new_entries = []
    for entry in playlist_data.get("entries", []):
        video_id = entry.get("id")
        title = entry.get("title")
        if not video_id or not title:
            continue
            
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Check if existing entry needs translation (if title has no Chinese)
        if url in existing_urls:
            for post in current_posts:
                if post.get("cover") == url and not has_chinese_chars(post.get("title", "")):
                    print(f"Updating English title for: {title}")
                    zh_title = "YC AI Startup School: " + translate_to_chinese(title)
                    post["title"] = zh_title
                    post["excerpt"] = zh_title
            continue

        slug = slugify(title)
        if slug in existing_slugs:
            # Handle duplicate slugs by appending id
            slug = f"{slug}-{video_id}"
        
        print(f"Found new video: {title}")
        
        # Translate title
        zh_title = "YC AI Startup School: " + translate_to_chinese(title)
        
        new_post = {
            "slug": slug,
            "title": zh_title,
            "date": datetime.today().strftime('%Y-%m-%d'),
            "tags": ["AI Startup School", "Y Combinator"],
            "excerpt": zh_title,  # Default excerpt
            "cover": url,      # Using YouTube URL as cover source
            "url": url
        }
        new_entries.append(new_post)
        existing_urls.add(url)
        existing_slugs.add(slug)

    if new_entries:
        # Append new entries to the beginning or end? Usually new posts at top.
        # But category.js sorts by date, so order in JSON matters less, but let's prepend.
        updated_posts = new_entries + current_posts
        with POSTS_JSON.open("w", encoding="utf-8") as fh:
            json.dump(updated_posts, fh, indent=2, ensure_ascii=False)
        print(f"Added {len(new_entries)} new posts to posts.json.")
    else:
        # Even if no new entries, we might have updated titles of existing posts
        with POSTS_JSON.open("w", encoding="utf-8") as fh:
            json.dump(current_posts, fh, indent=2, ensure_ascii=False)
        print("Checked and updated existing posts in posts.json.")


def main() -> None:
    args = parse_args()
    ensure_cache_dir(args.cache_dir)

    if args.crawl_playlist:
        crawl_playlist(args.yt_dlp, args.crawl_playlist)
        # Reload posts after crawling to process them immediately if needed
        print("Reloading posts list...")

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
        try:
            entry = posts[slug]
            url = entry.get("cover") or entry.get("url")
            if not url:
                print(f"Skipping {slug}: no video URL found", file=sys.stderr)
                continue
            cache_bucket = args.cache_dir / slug
            if args.skip_download:
                candidates = sorted(cache_bucket.glob("*.zh-Hant.vtt"))
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
                
            # Check if transcript is English and needs translation
            full_text_sample = " ".join([s.text for s in segments[:20]])
            if full_text_sample and not has_chinese_chars(full_text_sample):
                print(f"Detected English transcript for {slug}. Translating to Chinese...", file=sys.stderr)
                texts = [s.text for s in segments]
                translated_texts = translate_batch(texts)
                for i, s in enumerate(segments):
                    s.text = translated_texts[i]

            summary = read_existing_summary(POSTS_DIR / f"{slug}.md")
            primary_speaker = infer_primary_speaker(entry)
            markdown = build_markdown(entry, segments, summary, primary_speaker)
            write_post(slug, markdown, force=args.force, dry_run=args.dry_run)
        except Exception as e:
            print(f"Error processing {slug}: {e}", file=sys.stderr)
            continue


if __name__ == "__main__":
    main()
