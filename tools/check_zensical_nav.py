"""Pre-commit hook: the ``nav`` of ``zensical.toml`` lists every page under ``docs/``.

Zensical builds a page missing from an explicit ``nav`` without a warning, but leaves it out
of the menu. This fails when a page has no ``nav`` entry, or an entry names a missing page.
"""

import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def nav_pages(items: list[Any]) -> Iterator[str]:
    """The page paths of a ``nav`` list: ``"page.md"``, ``{"Title" = "page.md"}``, ``{"Section" = [...]}``."""
    for item in items:
        values = item.values() if isinstance(item, dict) else [item]
        for value in values:
            if isinstance(value, list):
                yield from nav_pages(value)
            elif isinstance(value, str) and "://" not in value:  # external links are allowed
                yield value


def main() -> int:
    project = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))["project"]
    if "nav" not in project:
        return 0  # Zensical generates the navigation from the files
    docs = ROOT / project.get("docs_dir", "docs")
    pages = {path.relative_to(docs).as_posix() for path in docs.rglob("*.md")}
    listed = list(nav_pages(project["nav"]))

    errors = [f"{page}: no entry in nav" for page in sorted(pages - set(listed))]
    errors += [f"{entry}: in nav, but {docs.name}/{entry} does not exist" for entry in listed if entry not in pages]
    for error in errors:
        sys.stderr.write(f"zensical.toml: {error}\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
