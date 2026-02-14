"""MkDocs hook: serve raw .md files, generate llms.txt and llms-full.txt.

Registered in mkdocs.yml under ``hooks:``.

on_post_build:
  - Copies every .md source file from docs/ into site/ (preserving paths)
    so each page is also available as raw markdown (e.g. /overview/concepts.md).
  - Generates site/llms.txt from the nav structure (llmstxt.org format).
  - Generates site/llms-full.txt by concatenating all nav pages.
"""

from pathlib import Path

import yaml


class _PermissiveLoader(yaml.SafeLoader):
    """SafeLoader that ignores !!python/name and similar custom tags."""


_PermissiveLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/",
    lambda loader, suffix, node: None,
)


def _walk_nav_titled(nav: list) -> list[tuple[str, str]]:
    """Return (title, path) pairs for leaf pages in the nav tree."""
    entries: list[tuple[str, str]] = []
    for item in nav:
        if isinstance(item, str):
            entries.append((item, item))
        elif isinstance(item, dict):
            for title, value in item.items():
                if isinstance(value, str):
                    entries.append((title, value))
                elif isinstance(value, list):
                    entries.extend(_walk_nav_titled(value))
    return entries


def _extract_llms_txt(nav: list, base_url: str, depth: int = 0) -> list[str]:
    """Recursively walk the nav tree and emit llms.txt lines."""
    lines: list[str] = []
    for item in nav:
        if isinstance(item, str):
            url = f"{base_url}/{item}"
            name = item.rsplit("/", 1)[-1].replace(".md", "").replace("-", " ").title()
            lines.append(f"- [{name}]({url})")
        elif isinstance(item, dict):
            for title, value in item.items():
                if isinstance(value, str):
                    lines.append(f"- [{title}]({base_url}/{value})")
                elif isinstance(value, list):
                    heading = "#" * min(depth + 2, 6)
                    lines.append("")
                    lines.append(f"{heading} {title}")
                    lines.append("")
                    lines.extend(_extract_llms_txt(value, base_url, depth + 1))
    return lines


def _resolve_relative_links(content: str, md_rel: Path, site_url: str) -> str:
    """Rewrite relative markdown links to absolute URLs.

    Skips links inside fenced code blocks and inline code spans.
    """
    import re
    from posixpath import normpath

    base_dir = str(md_rel.parent)

    def _replace_link(m: re.Match) -> str:
        text, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        anchor = ""
        if "#" in url:
            url, anchor = url.rsplit("#", 1)
            anchor = "#" + anchor
        if url:
            resolved = normpath(f"{base_dir}/{url}") if base_dir != "." else normpath(url)
            return f"[{text}]({site_url}/{resolved}{anchor})"
        return f"[{text}](#{anchor[1:]})"

    # Split on fenced code blocks only, then rewrite links in non-code segments
    parts = re.split(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)", content)
    for i, part in enumerate(parts):
        if i % 2 == 0:  # non-code segment
            parts[i] = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", _replace_link, part)
    return "".join(parts)


def on_post_build(config, **kwargs) -> None:
    docs_dir = Path(config["docs_dir"])
    site_dir = Path(config["site_dir"])
    site_url = config["site_url"].rstrip("/")

    mkdocs_yml = Path(config["config_file_path"])
    with open(mkdocs_yml) as f:
        raw_config = yaml.load(f, Loader=_PermissiveLoader)

    site_name = raw_config.get("site_name", "Documentation")
    site_description = raw_config.get("site_description", "").strip()
    nav = raw_config.get("nav", [])

    # 1. Copy all .md files from docs/ to site/, injecting llms.txt pointers
    llms_comment = (
        f"<!-- Documentation index: {site_url}/llms.txt -->\n"
        f"<!-- Full documentation: {site_url}/llms-full.txt -->\n\n"
    )
    for md_file in docs_dir.rglob("*.md"):
        rel = md_file.relative_to(docs_dir)
        dest = site_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = md_file.read_text(encoding="utf-8")
        content = _resolve_relative_links(content, rel, site_url)
        dest.write_text(llms_comment + content, encoding="utf-8")

    # 2. Generate llms.txt from nav structure
    parts = [f"# {site_name}", "", f"> {site_description}"]
    parts.extend(_extract_llms_txt(nav, site_url))
    parts.append("")
    (site_dir / "llms.txt").write_text("\n".join(parts), encoding="utf-8")

    # 3. Generate llms-full.txt by concatenating all nav pages
    entries = _walk_nav_titled(nav)
    full_parts: list[str] = []
    for title, md_path in entries:
        source = docs_dir / md_path
        if not source.exists():
            continue
        content = source.read_text(encoding="utf-8").strip()
        full_parts.append(f"# {title}\n\n{content}")

    (site_dir / "llms-full.txt").write_text(
        "\n\n---\n\n".join(full_parts) + "\n", encoding="utf-8"
    )
