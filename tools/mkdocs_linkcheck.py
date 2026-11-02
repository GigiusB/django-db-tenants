"""mkdocs hook: check every internal link and anchor of the built site.

The docs link pages with relative site paths (``../api/settings/#reference``), which
mkdocs does not validate. After the build this hook resolves each relative ``href`` /
``src`` in the generated HTML and logs a warning for missing pages, files or anchors,
so ``mkdocs build --strict`` fails on a broken link.
"""

import logging
import posixpath
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

log = logging.getLogger("mkdocs.hooks.linkcheck")


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value is None:
                continue
            if name in ("id", "name"):
                self.ids.add(value)
            elif name in ("href", "src") and tag in ("a", "img"):
                self.links.append(value)


def _target_file(site: Path, page_dir: str, path: str, base: str) -> Path:
    if path.startswith(base):  # absolute link under site_url's path (Material's 404 page uses them)
        path = "/" + path[len(base) :]
    resolved = posixpath.normpath(posixpath.join(page_dir, unquote(path)))
    target = site / resolved.lstrip("/")
    return target / "index.html" if path.endswith("/") or target.is_dir() else target


def on_post_build(config, **kwargs) -> None:
    site = Path(config["site_dir"])
    # "/django-db-tenants/" for site_url https://<user>.github.io/django-db-tenants/; "/" without site_url.
    base = urlsplit(config.get("site_url") or "/").path.rstrip("/") + "/"
    pages: dict[Path, _Page] = {}
    for html in site.rglob("*.html"):
        parser = _Page()
        parser.feed(html.read_text(encoding="utf-8"))
        pages[html.resolve()] = parser

    for html, page in pages.items():
        page_dir = "/" + html.parent.relative_to(site.resolve()).as_posix()
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc or link.startswith(("mailto:", "javascript:")):
                continue
            target = _target_file(site, page_dir, parts.path, base) if parts.path else html
            source = html.relative_to(site.resolve())
            if not target.exists():
                log.warning("Broken link in %s: %s", source, link)
            elif parts.fragment and target.suffix == ".html":
                ids = pages.get(target.resolve())
                if ids is not None and unquote(parts.fragment) not in ids.ids:
                    log.warning("Broken anchor in %s: %s", source, link)
