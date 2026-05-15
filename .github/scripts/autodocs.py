#!/usr/bin/env python3
"""
Auto-generate Mintlify MDX API documentation from Python source code.

Walks src/bot/, parses each .py file with ast, and generates MDX files
organized by module path under docs/content/reference/src/bot/.

Usage:
    python .github/scripts/autodocs.py                           # Generate all docs
    python .github/scripts/autodocs.py --dry-run                 # Preview only
    python .github/scripts/autodocs.py --module core             # Single module
    python .github/scripts/autodocs.py --check                   # Exit 1 if docs stale
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path.cwd()
SOURCE_DIR = REPO_ROOT / "src" / "bot"
OUTPUT_DIR = REPO_ROOT / "docs" / "content" / "reference" / "src" / "bot"

EXCLUDE_DIRS = {
    "migrations",
    "__pycache__",
    ".egg-info",
}

EXCLUDE_FILES = {
    "__init__.py",
}


def strip_docstring(docstring: str | None) -> str:
    """Clean a docstring for MDX output."""
    if not docstring:
        return ""
    # Strip and dedent
    lines = docstring.strip().split("\n")
    if len(lines) <= 1:
        return lines[0].strip()
    # Find common indentation
    indent = min(
        (len(line) - len(line.lstrip()) for line in lines[1:] if line.strip()),
        default=0,
    )
    cleaned = [lines[0]] + [line[indent:] for line in lines[1:]]
    return "\n".join(cleaned).strip()


def format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Format a function/method signature as a readable string."""
    args = node.args
    parts: list[str] = []

    # self/cls
    if args.args and args.args[0].arg in ("self", "cls", "mcs"):
        parts.append(args.args[0].arg)

    # Positional args
    for arg in args.args[1:] if parts else args.args:
        name = arg.arg
        if arg.annotation:
            name += f": {ast.unparse(arg.annotation)}"
        parts.append(name)

    # *args
    if args.vararg:
        parts.append(f"*{args.vararg.arg}")
        if args.vararg.annotation:
            parts[-1] += f": {ast.unparse(args.vararg.annotation)}"

    # Keyword-only args
    for idx, arg in enumerate(args.kwonlyargs):
        name = arg.arg
        if arg.annotation:
            name += f": {ast.unparse(arg.annotation)}"
        if idx < len(args.kw_defaults) and args.kw_defaults[idx] is not None:
            name += f" = {ast.unparse(args.kw_defaults[idx])}"
        parts.append(name)

    # **kwargs
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")
        if args.kwarg.annotation:
            parts[-1] += f": {ast.unparse(args.kwarg.annotation)}"

    sig = ", ".join(parts)

    # Return type
    returns = ""
    if node.returns:
        returns = f" -> {ast.unparse(node.returns)}"

    prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
    return f"{prefix}def {node.name}({sig}){returns}"


def get_decorators(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    """Get decorator names."""
    decos = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decos.append(dec.id)
        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
            decos.append(dec.func.id)
        elif isinstance(dec, ast.Attribute):
            decos.append(ast.unparse(dec).split(".")[-1])
        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
            decos.append(ast.unparse(dec.func).split(".")[-1])
    return decos


def extract_docstring(node: ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Extract docstring from an AST node."""
    if (body := getattr(node, "body", None)) and body:
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            doc = first.value.value
            if isinstance(doc, str):
                return doc
    return ""


def parse_file(filepath: Path) -> dict[str, Any]:
    """Parse a Python file and extract doc structure."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return {}

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {}

    rel = filepath.relative_to(SOURCE_DIR)
    module_path = str(rel.with_suffix("")).replace(os.sep, ".")

    result: dict[str, Any] = {
        "module_path": module_path,
        "docstring": extract_docstring(tree),
        "classes": [],
        "functions": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            cls_doc = extract_docstring(node)
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_") and item.name != "__init__":
                        continue
                    m_doc = extract_docstring(item)
                    methods.append({
                        "name": item.name,
                        "signature": format_signature(item),
                        "docstring": strip_docstring(m_doc),
                        "decorators": get_decorators(item),
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                    })
            bases = []
            for base in node.bases:
                bases.append(ast.unparse(base))

            result["classes"].append({
                "name": node.name,
                "docstring": strip_docstring(cls_doc),
                "bases": bases,
                "decorators": get_decorators(node),
                "methods": methods,
            })

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Module-level functions only (not inside a class)
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for item in ast.walk(parent):
                        if item is node:
                            break
                    else:
                        continue
                    break

            # Check it's really a module-level function
            is_module_level = True
            for item in ast.walk(tree):
                if isinstance(item, ast.ClassDef):
                    for child in ast.walk(item):
                        if child is node:
                            is_module_level = False
                            break

            if is_module_level and not node.name.startswith("_"):
                fn_doc = extract_docstring(node)
                result["functions"].append({
                    "name": node.name,
                    "signature": format_signature(node),
                    "docstring": strip_docstring(fn_doc),
                    "decorators": get_decorators(node),
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })

    return result


def render_mdx(data: dict[str, Any]) -> str:
    """Render parsed module data to MDX."""
    title = data["module_path"].split(".")[-1].replace("_", " ").title()
    module_root = data["module_path"].rsplit(".", 1)[0] if "." in data["module_path"] else ""
    parent_link = f" [{module_root}](./index.md)" if module_root else ""

    lines = [
        "---",
        f"title: {title}",
        'icon: lucide/code-2',
        "---",
        "",
        f"# {title}",
        "",
    ]

    if data["docstring"]:
        lines.append(data["docstring"].strip())
        lines.append("")

    # ── Classes ──
    if data["classes"]:
        lines.append("## Classes")
        lines.append("")

        for cls in data["classes"]:
            decorators = cls.get("decorators", [])
            if decorators:
                deco_line = " ".join(f"@{d}" for d in decorators)
                lines.append(f"```python")
                lines.append(f"{deco_line}")
                lines.append(f"class {cls['name']}{'(' + ', '.join(cls['bases']) + ')' if cls['bases'] else ''}:")
                lines.append(f"```")
                lines.append("")

            if cls["docstring"]:
                lines.append(cls["docstring"])
                lines.append("")

            if cls["methods"]:
                lines.append(f"### Methods")
                lines.append("")
                for method in cls["methods"]:
                    decos = method.get("decorators", [])
                    if decos:
                        lines.append(f"*Decorated with: `{'`, `'.join(decos)}`*")
                        lines.append("")

                    # Wrap in fenced code block for readability
                    lines.append(f"```python")
                    lines.append(f"{method['signature']}")
                    lines.append(f"```")
                    lines.append("")

                    if method["docstring"]:
                        lines.append(method["docstring"])
                        lines.append("")

    # ── Functions ──
    if data["functions"]:
        lines.append("## Functions")
        lines.append("")

        for fn in data["functions"]:
            decos = fn.get("decorators", [])
            if decos:
                lines.append(f"*Decorated with: `{'`, `'.join(decos)}`*")
                lines.append("")

            lines.append(f"```python")
            lines.append(f"{fn['signature']}")
            lines.append(f"```")
            lines.append("")

            if fn["docstring"]:
                lines.append(fn["docstring"])
                lines.append("")

    if not data["classes"] and not data["functions"]:
        lines.append("*No public classes or functions in this module.*")
        lines.append("")

    return "\n".join(lines)


def generate(module_filter: str | None = None, dry_run: bool = False, check: bool = False) -> bool:
    """Generate MDX docs. Returns True if any files changed."""
    changed = False

    # Find all Python files
    py_files = sorted(SOURCE_DIR.rglob("*.py"))
    py_files = [
        f for f in py_files
        if not any(excl in f.parts for excl in EXCLUDE_DIRS)
        and f.name not in EXCLUDE_FILES
    ]

    for py_file in py_files:
        rel = py_file.relative_to(SOURCE_DIR)

        # Filter by module
        if module_filter and module_filter not in str(rel):
            continue

        data = parse_file(py_file)
        if not data or (not data["classes"] and not data["functions"] and not data["docstring"]):
            continue

        mdx = render_mdx(data)
        out_path = OUTPUT_DIR / rel.with_suffix(".mdx")

        if dry_run:
            print(f"[DRY-RUN] Would write: {out_path.relative_to(REPO_ROOT)}")
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        existing = out_path.read_text(encoding="utf-8") if out_path.exists() else ""

        if existing != mdx:
            out_path.write_text(mdx, encoding="utf-8")
            print(f"  ✍ Updated: {out_path.relative_to(REPO_ROOT)}")
            changed = True
        else:
            print(f"  ✓ Unchanged: {out_path.relative_to(REPO_ROOT)}")

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-generate MDX API documentation from Python source.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be generated without writing files",
    )
    parser.add_argument(
        "--module", "-m",
        type=str,
        default=None,
        help="Generate docs for a specific module only (e.g., 'core', 'database')",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if docs are stale (for CI)",
    )
    args = parser.parse_args()

    print("Auto-generating API documentation from source...\n")

    changed = generate(
        module_filter=args.module,
        dry_run=args.dry_run,
        check=args.check,
    )

    if not args.dry_run:
        print(f"\n{'✓' if not changed else '⚠'} Done. {'Docs were updated.' if changed else 'All docs up to date.'}")

    if args.check and changed:
        print("\n❌ Docs are stale. Run 'python .github/scripts/autodocs.py' to regenerate.")
        sys.exit(1)


if __name__ == "__main__":
    main()
