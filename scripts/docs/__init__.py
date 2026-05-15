"""
Documentation utilities.

The migrate_to_mintlify script is the primary entry point and should
be run directly:
    uv run python -m scripts.docs.migrate_to_mintlify
"""

from pathlib import Path

__all__ = ["MIGRATION_SCRIPT_PATH"]

MIGRATION_SCRIPT_PATH = Path(__file__).parent / "migrate_to_mintlify.py"


def main() -> None:
    """Legacy entry point — migration script uses argparse directly."""
    import sys
    sys.stderr.write(
        "Use 'uv run python -m scripts.docs.migrate_to_mintlify' instead.\n"
    )
    sys.exit(1)
