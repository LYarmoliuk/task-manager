"""Wikilinks [[name]] (Obsidian) -> звичайні посилання MkDocs. Невизначена ціль = WARNING (strict впаде)."""
import logging
import os
import posixpath
import re

log = logging.getLogger("mkdocs.hooks.wikilinks")
_idx = {}
_RE = re.compile(r"(```.*?```|`[^`\n]*`)|\[\[([^\]\n]+)\]\]", re.S)


def on_files(files, config):
    _idx.clear()
    for f in files.documentation_pages():
        src = f.src_uri
        stem = os.path.splitext(posixpath.basename(src))[0].lower()
        _idx.setdefault(stem, []).append(src)
        _idx.setdefault(os.path.splitext(src)[0].lower(), []).append(src)
    return files


def on_page_markdown(markdown, page, config, files):
    def repl(m):
        if m.group(1):
            return m.group(1)
        raw = m.group(2)
        target, _, label = raw.partition("|")
        target, _, anchor = target.partition("#")
        key = target.strip().lower()
        hits = sorted(set(_idx.get(key, [])))
        if len(hits) != 1:
            log.warning("wikilink [[%s]] у %s: %s", raw, page.file.src_uri,
                        "неоднозначна ціль" if hits else "ціль не знайдено")
            return m.group(0)
        rel = posixpath.relpath(hits[0], posixpath.dirname(page.file.src_uri) or ".")
        text = label.strip() or target.strip()
        return "[%s](%s%s)" % (text, rel, "#" + anchor if anchor else "")

    return _RE.sub(repl, markdown)
