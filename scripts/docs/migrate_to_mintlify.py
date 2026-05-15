"""
Migrate Zensical-flavored Markdown docs to Mintlify-flavored MDX.

Converts all .md files under docs/content/ to .mdx with:
  - Renamed extension (.md → .mdx)
  - Cleaned frontmatter (drops tags, hide; strips lucide/ prefix from icon)
  - Admonitions (!!! note → <Note>, ??? collapsible → <Accordion>, etc.)
  - Tabs (=== "Name" → <Tabs><Tab label="Name">)
  - Snippet includes (--8<-- "FILE" → removed or inlined)
  - Internal links (.md → .mdx)

Usage:
    uv run scripts/docs/migrate_to_mintlify.py              # Run migration
    uv run scripts/docs/migrate_to_mintlify.py --dry-run     # Preview only
    uv run scripts/docs/migrate_to_mintlify.py --backup      # Keep originals
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# ── Admonition mapping ──────────────────────────────────────────────
# Zensical type -> Mintlify component name
ADMONITION_MAP: dict[str, str] = {
    "note": "Note",
    "tip": "Tip",
    "warning": "Warning",
    "danger": "Danger",
    "info": "Info",
    "important": "Warning",
    "success": "Note",
    "failure": "Danger",
    "bug": "Danger",
    "question": "Tip",
    "quote": "Note",
    "example": "Note",
    "abstract": "Note",
    "hint": "Tip",
    "check": "Note",
    "error": "Danger",
    "attention": "Warning",
    "caution": "Warning",
}

# Admonition types that should map to collapsible/expandable
COLLAPSIBLE_MAP: dict[str, str] = {
    "question": "Tip",
    "example": "Note",
    "quote": "Note",
    "abstract": "Note",
}

# ── Metrics ─────────────────────────────────────────────────────────
stats = {
    "files_processed": 0,
    "files_skipped": 0,
    "admonitions_converted": 0,
    "tabs_converted": 0,
    "links_updated": 0,
    "snippet_includes_removed": 0,
    "errors": 0,
}


# ── Regex patterns ──────────────────────────────────────────────────

# Admonition start: !!! type "Title"  or  !!! type  or  ???/???+ type "Title"
ADMONITION_START = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>!{3}|\?{3}|\?{3}\+) "
    r"(?P<admon_type>\w+)"
    r'(?: "(?P<title>[^"]*)")?$'
)

# Tab start: === "Tab Name"
TAB_START = re.compile(r'^[ \t]*=== "(?P<name>[^"]*)"\s*$')

# Internal link: [text](path.md)  but not https:// or /abs/
INTERNAL_LINK = re.compile(r"(?P<before>\[[^\]]*\]\()(?P<path>[^)]+\.md)(?P<after>\))")

# Snippet include
SNIPPET_INCLUDE = re.compile(r"^--8<--\s*\"([^\"]+)\"\s*$")

# Frontmatter markers
FM_START = re.compile(r"^---\s*$")

# Frontmatter fields to drop entirely
DROP_FM_FIELDS = {"tags", "hide"}

# Frontmatter fields needing icon prefix stripping
ICON_FIELD = re.compile(r"^icon:\s*lucide/(.+)$")


def convert_frontmatter(lines: list[str], filepath: str) -> list[str]:
    """Convert frontmatter: drop 'tags'/'hide', strip 'lucide/' from icon."""
    result: list[str] = []
    in_frontmatter = False
    in_fm_block = False

    for line in lines:
        if FM_START.match(line) and not in_fm_block:
            in_fm_block = True
            result.append(line)
            continue
        if in_fm_block:
            if FM_START.match(line):
                in_fm_block = False
                result.append(line)
                continue
            # Check if this is a field we should drop
            stripped = line.strip()
            if any(stripped.startswith(f"{fld}:") or stripped.startswith(f"  {fld}:")
                   or any(f"  - {fld}" in stripped for fld in DROP_FM_FIELDS)
                   for fld in DROP_FM_FIELDS):
                # Drop the line
                # But might be multi-line YAML, skip until next top-level key
                if not stripped.startswith(" ") and stripped.endswith(":"):
                    # This is a key we're dropping - skip until next key or end
                    # Actually just skip this line - YAML lists are on same level
                    continue
                continue
            # Handle multi-line tags (list items under "tags:")
            # Actually let's handle it simply
            if stripped in DROP_FM_FIELDS or any(
                stripped.startswith(f) for f in DROP_FM_FIELDS
            ):
                continue
            # Strip lucide/ from icon
            icon_match = ICON_FIELD.match(stripped)
            if icon_match:
                result.append(f"icon: {icon_match.group(1)}\n")
                continue
        result.append(line)

    return result


def convert_admonitions(lines: list[str], filepath: str) -> list[str]:
    """Convert Zensical admonition blocks to Mintlify JSX components."""
    result: list[str] = []
    i = 0
    indent_stack: list[int] = []  # track indent levels for nested admonitions

    while i < len(lines):
        line = lines[i]
        match = ADMONITION_START.match(line)

        if match:
            marker = match.group("marker")
            admon_type = match.group("admon_type").lower()
            title = match.group("title")
            base_indent = len(match.group("indent"))

            # Determine if collapsible
            is_collapsible = marker.startswith("?")
            is_expanded = marker == "???+"

            # Map to Mintlify component
            component = ADMONITION_MAP.get(admon_type, "Note")
            if is_collapsible:
                component = "Accordion"

            # Collect body lines (indented more than base_indent)
            body_lines: list[str] = []
            j = i + 1
            indent_width = None
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip() == "":
                    # Empty line inside admonition - preserve it
                    if body_lines:
                        body_lines.append(next_line)
                    else:
                        # Can't have blank right after opening tag, skip it
                        j += 1
                        continue
                # Calculate indent
                stripped = next_line.rstrip("\n")
                leading_spaces = len(stripped) - len(stripped.lstrip())
                # Content must be indented >= base_indent + 4
                required_indent = base_indent + 4
                if leading_spaces >= required_indent:
                    # Strip the admonition indent (exactly required_indent or relative)
                    if indent_width is None:
                        indent_width = leading_spaces
                    body_lines.append(next_line[indent_width:] if leading_spaces >= indent_width else next_line[required_indent:])
                    j += 1
                else:
                    break

            # Render Mintlify component
            attr = f' title="{title}"' if title else ""
            expanded_attr = ' defaultOpen' if is_expanded else ""

            if is_collapsible:
                result.append(f"{' ' * base_indent}<Accordion{attr}{expanded_attr}>\n")
            else:
                result.append(f"{' ' * base_indent}<{component}{attr}>\n")

            for bl in body_lines:
                result.append(f"{' ' * (base_indent + 2)}{bl}")

            if is_collapsible:
                result.append(f"{' ' * base_indent}</Accordion>\n")
            else:
                result.append(f"{' ' * base_indent}</{component}>\n")

            stats["admonitions_converted"] += 1
            i = j
        else:
            result.append(line)
            i += 1

    return result


def convert_tabs(lines: list[str], filepath: str) -> list[str]:
    """Convert Zensical tab groups to Mintlify Tabs/Tab components."""
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        match = TAB_START.match(line)

        if match:
            # This is a tab start - collect all consecutive tabs
            tab_group: list[tuple[str, list[str], str]] = []  # (name, content, first_line)
            base_indent = len(line) - len(line.lstrip())

            while i < len(lines):
                tab_match = TAB_START.match(lines[i])
                if not tab_match:
                    break
                tab_name = tab_match.group("name")
                # The content of this tab follows, indented by base_indent + 4
                tab_content: list[str] = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if next_line.strip() == "" and not tab_content:
                        # Skip blank right after tab header
                        i += 1
                        continue
                    if next_line.strip() == "":
                        # Empty line inside content
                        tab_content.append(next_line)
                        i += 1
                        continue
                    leading = len(next_line) - len(next_line.lstrip())
                    if leading >= base_indent + 4:
                        # Strip the extra indent (keep relative indent)
                        indent_strip = base_indent + 4
                        content_part = next_line[indent_strip:] if leading >= indent_strip else next_line.lstrip()
                        tab_content.append(content_part)
                        i += 1
                    else:
                        # Check if this is a new tab or end of group
                        if TAB_START.match(next_line):
                            break
                        else:
                            # End of tab group
                            break
                # Remove trailing blanks
                while tab_content and tab_content[-1].strip() == "":
                    tab_content.pop()
                tab_group.append((tab_name, tab_content))

            if tab_group:
                stats["tabs_converted"] += 1
                result.append(f"{' ' * base_indent}<Tabs>\n")
                for tab_name, tab_content in tab_group:
                    result.append(f"{' ' * (base_indent + 2)}<Tab label=\"{tab_name}\">\n")
                    for tc in tab_content:
                        result.append(f"{' ' * (base_indent + 4)}{tc}")
                    result.append(f"{' ' * (base_indent + 2)}</Tab>\n")
                result.append(f"{' ' * base_indent}</Tabs>\n")
                continue

        result.append(line)
        i += 1

    return result


def convert_links(content: str) -> str:
    """Convert .md internal links to .mdx."""
    def replace_link(m: re.Match) -> str:
        stats["links_updated"] += 1
        return f"{m.group('before')}{m.group('path')[:-3]}.mdx{m.group('after')}"

    return INTERNAL_LINK.sub(replace_link, content)


def remove_snippet_includes(lines: list[str], filepath: str) -> list[str]:
    """Remove or replace --8<-- snippet includes."""
    result: list[str] = []
    for line in lines:
        match = SNIPPET_INCLUDE.match(line)
        if match:
            included_file = match.group(1)
            # CHANGELOG.md include is handled by the new changelog.mdx
            if "CHANGELOG" in included_file:
                result.append(
                    "<!-- Changelog content migrated to changelog.mdx -->\n"
                )
                stats["snippet_includes_removed"] += 1
            else:
                # Leave other includes with a warning
                print(
                    f"  ⚠  Snippet include '{included_file}' in {filepath} "
                    f"— needs manual review"
                )
                result.append(line)
        else:
            result.append(line)
    return result


def process_file(filepath: Path, dry_run: bool = False, backup: bool = False) -> None:
    """Process a single .md file, converting it to .mdx."""
    if filepath.suffix != ".md":
        return

    # Skip files in known-non-content dirs
    skip_dirs = {".mintlify-backup", "__pycache__", ".git"}
    if any(part in skip_dirs for part in filepath.parts):
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            original_text = f.read()

        lines = original_text.splitlines(keepends=True)

        # Apply conversions in order
        lines = convert_frontmatter(lines, str(filepath))
        lines = remove_snippet_includes(lines, str(filepath))
        text = "".join(lines)
        text = convert_links(text)
        # Re-split for block-level conversions
        lines = text.splitlines(keepends=True)
        lines = convert_admonitions(lines, str(filepath))
        lines = convert_tabs(lines, str(filepath))

        new_text = "".join(lines)

        if original_text == new_text:
            # No changes beyond rename — skip
            pass

        if dry_run:
            rel = filepath.relative_to(Path.cwd())
            print(f"  ~  {rel} → {rel.with_suffix('.mdx')}")
            if original_text != new_text:
                print("     (content modified)")
            return

        # Write the .mdx file
        mdx_path = filepath.with_suffix(".mdx")
        with open(mdx_path, "w", encoding="utf-8") as f:
            f.write(new_text)

        # Backup original if requested
        if backup:
            backup_dir = filepath.parent / ".mintlify-backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, backup_dir / filepath.name)
            print(f"  ↑  Backed up {filepath.name} → {backup_dir}")

        # Remove original .md
        filepath.unlink()

        rel = mdx_path.relative_to(Path.cwd())
        print(f"  ✓  {rel}")
        stats["files_processed"] += 1

    except Exception as e:
        print(f"  ✗  {filepath}: {e}", file=sys.stderr)
        stats["errors"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Zensical Markdown docs to Mintlify MDX.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="docs/content",
        help="Root directory of docs (default: docs/content)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview changes without writing",
    )
    parser.add_argument(
        "--backup",
        "-b",
        action="store_true",
        help="Backup originals before conversion",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Log every file processed",
    )
    args = parser.parse_args()

    root = Path(args.directory)
    if not root.is_dir():
        print(f"Error: '{root}' is not a directory", file=sys.stderr)
        sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "MIGRATE"
    print(f"\n  Mintlify Migration — {mode}")
    print(f"  Directory: {root.resolve()}\n")

    # Collect all .md files (resolve to absolute paths)
    md_files = sorted(root.resolve().rglob("*.md"))

    if not md_files:
        print("  No .md files found.\n")
        return

    print(f"  Found {len(md_files)} .md files\n")

    for fpath in md_files:
        process_file(fpath, dry_run=args.dry_run, backup=args.backup)

    # Summary
    print(f"\n  ── Summary ──")
    print(f"  Files processed:  {stats['files_processed']}")
    print(f"  Files skipped:    {stats['files_skipped']}")
    print(f"  Admonitions:      {stats['admonitions_converted']}")
    print(f"  Tabs converted:   {stats['tabs_converted']}")
    print(f"  Links updated:    {stats['links_updated']}")
    print(f"  Includes removed: {stats['snippet_includes_removed']}")
    print(f"  Errors:           {stats['errors']}")

    if args.dry_run:
        print("\n  Run without --dry-run to apply changes.\n")
    else:
        print(f"\n  ✅ Migration complete.\n")


if __name__ == "__main__":
    main()
