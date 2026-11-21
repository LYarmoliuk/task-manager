"""Сторінки зі status: deprecated: попередження зверху + переспрямування на superseded_by (meta refresh)."""
import posixpath


def _is_dep(page):
    return str(page.meta.get("status", "")).lower() == "deprecated"


def on_page_markdown(markdown, page, config, files):
    if not _is_dep(page):
        return markdown
    sup = page.meta.get("superseded_by")
    if sup:
        rel = posixpath.relpath(sup, posixpath.dirname(page.file.src_uri) or ".")
        note = '!!! warning "Deprecated"\n    Сторінку застарілo. Актуальний документ: [%s](%s).\n\n' % (sup, rel)
    else:
        note = '!!! warning "Deprecated"\n    Сторінку застарілo; актуальної заміни не вказано.\n\n'
    return note + markdown


def on_post_page(output, page, config):
    sup = page.meta.get("superseded_by")
    if not (_is_dep(page) and sup):
        return output
    # відносна URL-адреса цілі від поточної сторінки (use_directory_urls: dir/index.html)
    src = page.file.src_uri
    rel = posixpath.relpath(sup, posixpath.dirname(src) or ".")
    depth = 0 if src.endswith("index.md") else 1
    rel_url = "../" * depth + posixpath.splitext(rel)[0].replace("index", "").rstrip("/") + "/"
    tag = '<meta http-equiv="refresh" content="5; url=%s">' % rel_url
    return output.replace("<head>", "<head>\n" + tag, 1)
