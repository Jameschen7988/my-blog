#!/usr/bin/env python3
"""
Scans existing blog posts, identifies English content, and translates it to Traditional Chinese.

This script is designed to be run after posts have been generated. It iterates through the
Markdown files in `public/posts`, checks if the content is primarily in English, and uses
an AI translation service (OpenAI's GPT models) to translate the text.

Key Features:
- Parses Markdown to isolate translatable text (summaries, paragraphs) from code and syntax.
- Detects if content needs translation using character-based analysis.
- Batches API calls for efficient translation of multiple text segments.
- Preserves Markdown structure, including speaker headings and timestamps.
- Includes a `--dry-run` mode to preview changes before writing to disk.

This script requires the `openai` Python package and an `OPENAI_API_KEY` environment variable.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Union

# Third-party dependencies, assumed to be installed.
# pip install openai
try:
    from openai import OpenAI
except ImportError:
    print("Error: The 'openai' package is not installed. Please install it with 'pip install openai'", file=sys.stderr)
    sys.exit(1)

# Constants
ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "public" / "posts"

# Regular Expressions
SUMMARY_PATTERN = re.compile(r"<!-- summary -->(.*?)<!-- endsummary -->", re.DOTALL)
SPEAKER_HEADING_PATTERN = re.compile(r"^(###\s+.+?)\s*(<small>\[\d{2}:\d{2}(?:\:\d{2})?\]</small>.*)")
# A simple block is any text not part of a heading or special block
BLOCK_DELIMITER = re.compile(r"^(### |<small>|<!--)")


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Translate existing English blog posts to Traditional Chinese.")
    parser.add_argument("--api-key", help="Your OpenAI API key. If not provided, it will use the OPENAI_API_KEY environment variable.")
    parser.add_argument("--slug", action="append", help="Only process the given slug(s). Can be repeated.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing post content without creating a backup.")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated Markdown instead of writing to the post file.")
    parser.add_argument("--min-chinese-ratio", type=float, default=0.5, help="Minimum ratio of Chinese characters to be considered 'translated'.")
    return parser.parse_args()


def has_chinese_chars(text: str) -> bool:
    """Checks if the text contains any Traditional/Simplified Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", text))

def get_chinese_char_ratio(text: str) -> float:
    """Calculates the ratio of Chinese characters in the text."""
    if not text:
        return 0.0
    total_chars = len(text)
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_chars / total_chars

def translate_batch(texts: List[str], api_key: str) -> List[str]:
    """
    Translates a list of strings to Traditional Chinese using the OpenAI API.
    Retries on failure.
    """
    if not api_key:
        print("Warning: API key not provided. Skipping translation.", file=sys.stderr)
        return texts

    client = OpenAI(api_key=api_key)
    translated = []
    batch_size = 20  # Balance context window and speed

    print(f"Translating {len(texts)} segments in batches of {batch_size}...", file=sys.stderr)
    for i in range(0, len(texts), batch_size):
        batch_num = i // batch_size + 1
        total_batches = (len(texts) - 1) // batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}...", file=sys.stderr)
        
        batch = texts[i:i + batch_size]
        prompt_text = "\n".join(f"SEGMENT_{idx}: {text}" for idx, text in enumerate(batch))
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Translate the following text segments to Traditional Chinese (Taiwan). Maintain the original format 'SEGMENT_index: translated_text' for each line. Preserve any special formatting or technical terms where appropriate."},
                        {"role": "user", "content": prompt_text}
                    ]
                )
                content = response.choices[0].message.content.strip()
                
                batch_map = {}
                for line in content.splitlines():
                    match = re.match(r"SEGMENT_(\d+):\s*(.*)", line, re.DOTALL)
                    if match:
                        batch_map[int(match.group(1))] = match.group(2).strip()

                # Reconstruct batch, falling back to original if translation is missing/failed
                for idx in range(len(batch)):
                    translated.append(batch_map.get(idx, batch[idx]))
                
                break  # Success
            except Exception as e:
                if "insufficient_quota" in str(e):
                    sys.exit(f"❌ Critical Error: OpenAI API quota exceeded. Script aborted.")
                
                if attempt < max_retries - 1:
                    print(f"    Batch {batch_num} failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in 2s...", file=sys.stderr)
                    time.sleep(2)
                else:
                    print(f"    Batch {batch_num} failed after {max_retries} attempts: {e}. Appending original text.", file=sys.stderr)
                    translated.extend(batch)
    
    return translated

def parse_markdown_to_segments(content: str) -> List[Dict[str, Any]]:
    """
    Parses a Markdown file's content into a structured list of segments.
    Each segment is a dictionary that can be translated and re-rendered.
    """
    segments = []
    summary_match = SUMMARY_PATTERN.search(content)
    
    if summary_match:
        summary_text = summary_match.group(1).strip()
        segments.append({"type": "summary", "content": summary_text})
        # Process the rest of the content
        main_content = content[summary_match.end():].strip()
    else:
        main_content = content.strip()

    # The rest of the content is processed line by line or in blocks
    lines = main_content.split('\n')
    current_block = []

    for line in lines:
        if BLOCK_DELIMITER.match(line):
            # If we hit a delimiter, process the accumulated block first
            if current_block:
                segments.append({"type": "text", "content": "\n".join(current_block)})
                current_block = []
            
            # Now handle the delimiter line
            heading_match = SPEAKER_HEADING_PATTERN.match(line)
            if heading_match:
                segments.append({
                    "type": "heading", 
                    "content": heading_match.group(1)
                })
                segments.append({
                    "type": "timestamp",
                    "content": heading_match.group(2)
                })
            else:
                 segments.append({"type": "raw", "content": line})

        else:
            # Not a delimiter, just add to the current text block
            current_block.append(line)

    # Add any remaining block
    if current_block:
        segments.append({"type": "text", "content": "\n".join(current_block).strip()})
        
    return segments


def render_segments_to_markdown(segments: List[Dict[str, Any]]) -> str:
    """Renders a list of structured segments back into a Markdown string."""
    output = []
    has_summary = False
    
    for i, seg in enumerate(segments):
        seg_type = seg.get("type")
        content = seg.get("content", "")

        if seg_type == "summary":
            output.append("<!-- summary -->")
            output.append(content)
            output.append("<!-- endsummary -->")
            output.append("")
            has_summary = True
        elif seg_type == "heading":
            # Check if next segment is a timestamp to join them
            if i + 1 < len(segments) and segments[i+1].get("type") == "timestamp":
                # The timestamp will be handled with the next segment
                output.append(content)
            else:
                output.append(content)
        elif seg_type == "timestamp":
            # This should be appended to the previous heading
             if output and not output[-1].endswith("\n"):
                 output[-1] = f"{output[-1]} {content}"
             else:
                 output.append(content)
        elif seg_type == "text":
            # Add a newline after the content block
            output.append(content + "\n")
        elif seg_type == "raw":
            output.append(content)

    # Post-process to clean up spacing
    full_text = "\n".join(output)
    # Condense multiple blank lines into one
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    return full_text.strip() + "\n"

def main():
    """Main execution function."""
    args = parse_args()
    
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("Error: API key not provided. Please use the --api-key argument or set the OPENAI_API_KEY environment variable.")

    target_slugs = args.slug if args.slug else [p.stem for p in POSTS_DIR.glob("*.md") if not p.name.endswith(".bak.md")]
    
    print(f"Scanning {len(target_slugs)} posts...")

    for slug in sorted(target_slugs):
        post_path = POSTS_DIR / f"{slug}.md"
        if not post_path.exists():
            print(f"Skipping {slug}: File not found.", file=sys.stderr)
            continue
            
        print(f"\n--- Processing: {slug} ---")
        original_content = post_path.read_text(encoding="utf-8")
        
        # Simple check: if the whole file is already mostly Chinese, skip it
        if get_chinese_char_ratio(original_content) > args.min_chinese_ratio:
            print("  Looks like it's already translated. Skipping.")
            continue

        # Parse the document into structured segments
        segments = parse_markdown_to_segments(original_content)
        
        translatable_texts = []
        translatable_indices = []

        for i, seg in enumerate(segments):
            # We only translate summary and text blocks that are not primarily Chinese
            if seg.get("type") in ["summary", "text"] and seg.get("content"):
                content = seg["content"]
                if get_chinese_char_ratio(content) < args.min_chinese_ratio:
                    translatable_texts.append(content)
                    translatable_indices.append(i)

        if not translatable_texts:
            print("  No English content found needing translation. Skipping.")
            continue
            
        print(f"  Found {len(translatable_texts)} segments to translate.")
        
        # Perform the translation
        translated_texts = translate_batch(translatable_texts, api_key)
        
        # Update the segments with the translated content
        for i, translated_text in zip(translatable_indices, translated_texts):
            segments[i]["content"] = translated_text
            
        # Re-render the Markdown
        new_content = render_segments_to_markdown(segments)
        
        if args.dry_run:
            print("--- DRY RUN: NEW CONTENT ---")
            print(new_content)
            print("--- END DRY RUN ---")
        else:
            if not args.force:
                backup_path = post_path.with_suffix(".md.bak")
                if not backup_path.exists():
                    shutil.copy2(post_path, backup_path)
                    print(f"  Created backup: {backup_path.name}")
            
            post_path.write_text(new_content, encoding="utf-8")
            print(f"  Successfully translated and updated {post_path.name}")

if __name__ == "__main__":
    main()
