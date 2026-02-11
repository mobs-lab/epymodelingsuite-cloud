"""MkDocs hook that renders link cards from HTML comment syntax.

Syntax:
    <!-- link-card: https://example.com -->
    <!-- link-card: https://example.com | title=Custom Title -->
    <!-- link-card: https://example.com | description=Custom subtitle -->
    <!-- link-card: https://example.com | description=false -->
    <!-- link-card: https://example.com | favicon=false -->

Two-phase approach: on_page_markdown stores card data and emits a
placeholder that survives markdown processing; on_page_content replaces
placeholders with final HTML (avoiding abbr/other extension interference).
"""

import html
import re
import urllib.request
import urllib.error
from urllib.parse import urlparse

_meta_cache: dict[str, tuple[str | None, str | None]] = {}  # url → (title, desc)

# Cards pending render, keyed by placeholder id
_pending: dict[str, tuple[str, dict[str, str]]] = {}
_counter = 0

_COMMENT = re.compile(
    r"<!--\s*link-card:\s*(https?://[^\s|>]+)\s*"
    r"(?:\|\s*(.*?))?\s*-->",
    re.DOTALL,
)

_PLACEHOLDER = re.compile(r"<!-- LC#(\d+) -->")


_OPT_PATTERN = re.compile(r'(\w+)\s*=\s*(?:"([^"]*?)"|(\S+))')


def _parse_options(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
            for m in _OPT_PATTERN.finditer(raw)}


def _fetch_meta(url: str) -> tuple[str | None, str | None]:
    """Fetch title and description from a URL. Returns (title, description)."""
    if url in _meta_cache:
        return _meta_cache[url]
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MkDocs-LinkCard)"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read(32_768).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        _meta_cache[url] = (None, None)
        return (None, None)

    # Title: og:title → <title>
    m = re.search(
        r'<meta\s+(?:property|name)=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        data,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r'<meta\s+content=["\']([^"\']+)["\']\s+(?:property|name)=["\']og:title["\']',
            data,
            re.IGNORECASE,
        )
    if not m:
        m = re.search(r"<title[^>]*>([^<]+)</title>", data, re.IGNORECASE)
    title = html.unescape(m.group(1).strip()) if m else None
    if title:
        title = re.sub(r"^GitHub - ", "", title)

    # Description: og:description → <meta name="description">
    d = re.search(
        r'<meta\s+(?:property|name)=["\']og:description["\']\s+content=["\']([^"\']+)["\']',
        data,
        re.IGNORECASE,
    )
    if not d:
        d = re.search(
            r'<meta\s+content=["\']([^"\']+)["\']\s+(?:property|name)=["\']og:description["\']',
            data,
            re.IGNORECASE,
        )
    if not d:
        d = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
            data,
            re.IGNORECASE,
        )
    if not d:
        d = re.search(
            r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']description["\']',
            data,
            re.IGNORECASE,
        )
    desc = html.unescape(d.group(1).strip()) if d else None

    _meta_cache[url] = (title, desc)
    return (title, desc)


def _github_repo_path(parsed) -> str | None:
    """Return 'user/repo' if url is a GitHub repo root, else None."""
    if parsed.hostname != "github.com":
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) == 2:
        return f"{parts[0]}/{parts[1]}"
    return None


def _clean_github_desc(desc: str, repo: str) -> str:
    """Strip GitHub boilerplate from description."""
    desc = re.sub(
        r"\s*Contribute to \S+ development by creating an account on GitHub\.\s*$",
        "",
        desc,
    )
    desc = re.sub(r"\s*-\s+" + re.escape(repo) + r"\s*$", "", desc)
    return desc.strip()


def _build_card(url: str, opts: dict[str, str]) -> str:
    parsed = urlparse(url)
    domain = parsed.hostname or parsed.netloc

    fetched_title, fetched_desc = _fetch_meta(url)
    gh_repo = _github_repo_path(parsed)

    if "title" in opts:
        title = opts["title"]
    elif gh_repo:
        title = gh_repo
    else:
        title = fetched_title or domain

    desc_opt = opts.get("description", "")
    if desc_opt == "false":
        description = ""
    elif desc_opt:
        description = desc_opt
    elif gh_repo and fetched_desc:
        description = _clean_github_desc(fetched_desc, gh_repo)
    else:
        description = fetched_desc or ""
    favicon_opt = opts.get("favicon", "")

    if favicon_opt == "false":
        favicon_html = ""
    elif favicon_opt:
        favicon_html = (
            f'<img class="link-card-favicon" src="{html.escape(favicon_opt)}" '
            f'alt="" width="14" height="14">'
        )
    else:
        favicon_url = (
            f"https://www.google.com/s2/favicons?domain={html.escape(domain)}&sz=32"
        )
        favicon_html = (
            f'<img class="link-card-favicon" src="{favicon_url}" '
            f'alt="" width="14" height="14">'
        )

    desc_html = ""
    if description:
        desc_html = (
            f'<span class="link-card-description">{html.escape(description)}</span>'
        )

    return (
        f'<a class="link-card" href="{html.escape(url)}" '
        f'target="_blank" rel="noopener noreferrer">'
        f'<span class="link-card-title">{html.escape(title)}</span>'
        f"{desc_html}"
        f'<span class="link-card-origin">'
        f"{favicon_html}"
        f'<span class="link-card-domain">{html.escape(domain)}</span>'
        f"</span>"
        f"</a>"
    )


# Phase 1: replace comment with a placeholder that markdown won't touch
def on_page_markdown(markdown: str, **kwargs) -> str:
    global _counter

    def _replace(m: re.Match) -> str:
        global _counter
        _counter += 1
        cid = str(_counter)
        url = m.group(1).strip()
        opts = _parse_options(m.group(2))
        _pending[cid] = (url, opts)
        # Emit an HTML comment placeholder — survives markdown processing
        return f"<!-- LC#{cid} -->"

    return _COMMENT.sub(_replace, markdown)


# Phase 2: replace placeholders with final card HTML (after abbr etc.)
def on_page_content(html_content: str, **kwargs) -> str:
    def _replace(m: re.Match) -> str:
        cid = m.group(1)
        if cid not in _pending:
            return m.group(0)
        url, opts = _pending.pop(cid)
        return _build_card(url, opts)

    return _PLACEHOLDER.sub(_replace, html_content)
