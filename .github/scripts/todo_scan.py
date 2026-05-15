#!/usr/bin/env python3
"""
Scan Python source files for TODO/FIXME/HACK/XXX comments, extract them,
remove them from source, and append them to TODO.md.

Usage:
    python .github/scripts/todo_scan.py              # Normal run — modifies files
    python .github/scripts/todo_scan.py --dry-run     # Preview only
    python .github/scripts/todo_scan.py --json        # Output JSON for workflow consumption

Output (--json):
    A JSON array of discovered TODOs, each with:
      - file: relative path
      - line: line number
      - tag: TODO|FIXME|HACK|XXX
      - text: description text
      - link: TODO.md#L<line> reference
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path.cwd()
SRC_DIRS = ["src/bot"]
EXCLUDE_PATTERNS = (
    "migrations",
    ".venv",
    "__pycache__",
    ".egg-info",
    "site-packages",
)

# Matches # TODO:, # FIXME:, # HACK:, # XXX:  at any indentation level
# Group 1: tag (TODO, FIXME, HACK, XXX)
# Group 2: text after the tag
TODO_PATTERN = re.compile(
    r"^\s*#\s*(TODO|FIXME|HACK|XXX)\b\s*(.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Also matches inline comments:  some_code()  # TODO: text
INLINE_TODO_PATTERN = re.compile(
    r"\s*#\s*(TODO|FIXME|HACK|XXX)\b\s*(.*?)\s*$",
    re.IGNORECASE,
)


def find_todos() -> list[dict]:
    """Scan source files and return all TODO/FIXME/HACK/XXX comments."""
    todos: list[dict] = []

    for src_dir in SRC_DIRS:
        base = REPO_ROOT / src_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            rel = path.relative_to(REPO_ROOT)
            if any(excl in path.parts for excl in EXCLUDE_PATTERNS):
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            lines = content.split("\n")

            for lineno, line in enumerate(lines, start=1):
                m = TODO_PATTERN.match(line)
                if m:
                    tag = m.group(1).upper()
                    text = m.group(2).strip() if m.group(2) else "(no description)"
                    todos.append({
                        "file": str(rel),
                        "line": lineno,
                        "tag": tag,
                        "text": text,
                    })

    return todos


def remove_todos_from_source(todos: list[dict], dry_run: bool = False) -> list[dict]:
    """Remove discovered TODO/FIXME/HACK/XXX comments from source files.

    Returns list of (file, removed_count) tuples.
    """
    modified: dict[str, list[int]] = {}  # file -> list of removed line numbers
    removed = []

    # Group TODOs by file (reverse order so line numbers stay valid)
    by_file: dict[str, list[dict]] = {}
    for todo in todos:
        by_file.setdefault(todo["file"], []).append(todo)

    for filepath_str, file_todos in by_file.items():
        filepath = REPO_ROOT / filepath_str
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        lines = content.split("\n")
        # Process in reverse line order to preserve line numbers
        for todo in sorted(file_todos, key=lambda t: t["line"], reverse=True):
            idx = todo["line"] - 1  # 0-indexed
            if idx >= len(lines):
                continue

            m = TODO_PATTERN.match(lines[idx])
            if m:
                # Standalone comment line — remove the line
                removed.append((filepath_str, todo["line"]))
                lines.pop(idx)
                modified.setdefault(filepath_str, []).append(todo["line"])

        new_content = "\n".join(lines)
        # Clean up excessive blank lines (more than 2 consecutive)
        new_content = re.sub(r"\n{3,}", "\n\n", new_content)

        if new_content != content and not dry_run:
            filepath.write_text(new_content, encoding="utf-8")

    return [
        {"file": f, "lines": sorted(lines)}
        for f, lines in modified.items()
    ]


def append_to_todo_md(todos: list[dict]) -> str:
    """Append extracted TODOs to TODO.md and return the section content.

    Returns the section text that was appended.
    """
    todo_path = REPO_ROOT / "TODO.md"
    existing = todo_path.read_text(encoding="utf-8") if todo_path.exists() else "# TODO.md\n\n"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"\n## Auto-extracted ({now})\n"]

    for todo in sorted(todos, key=lambda t: (t["file"], t["line"])):
        link = f"{todo['file']}:{todo['line']}"
        lines.append(f"- [ ] **{todo['tag']}**: {todo['text']} ({link})")

    line_start = existing.count("\n") + 2  # Approximate line number in TODO.md
    todo_md_ref = f"TODO.md#L{line_start}"

    section = "\n".join(lines) + "\n"
    todo_path.write_text(existing + section, encoding="utf-8")

    # Return the section with line number info
    return section + f"\n<!-- section-start:L{line_start} -->\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan and extract TODO comments from source code.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without modifying files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output TODOs as JSON array to stdout (for workflow consumption)",
    )
    args = parser.parse_args()

    todos = find_todos()

    if args.json:
        # Output JSON for workflow to iterate and create issues
        json.dump(todos, sys.stdout, indent=2)
        return

    if not todos:
        print("✓ No TODO/FIXME/HACK/XXX comments found in source code.")
        return

    print(f"Found {len(todos)} TODO/FIXME/HACK/XXX comments:\n")
    for todo in sorted(todos, key=lambda t: (t["file"], t["line"])):
        print(f"  {todo['file']}:{todo['line']}  [{todo['tag']}] {todo['text']}")

    if not args.dry_run:
        removed = remove_todos_from_source(todos)
        section = append_to_todo_md(todos)
        print(f"  Files modified: {len(removed)}")
    else:
        print(f"\n[DRY-RUN] Would remove {len(todos)} comments from source and add to TODO.md.")


if __name__ == "__main__":
    main()
