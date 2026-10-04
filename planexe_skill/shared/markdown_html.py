"""Small, dependency-free Markdown -> HTML renderer (replaces Python-Markdown in the report stage).

Supports: ATX headings, paragraphs, emphasis/strong, inline code, links/autolinks, inline HTML,
ordered/unordered lists with nesting, blockquotes, fenced code blocks, horizontal rules,
pipe tables, hard line breaks (two trailing spaces). Output mirrors Python-Markdown's HTML.
"""
from __future__ import annotations

import html
import re

_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(\s[^<>]*)?/?>|<!--.*?-->")
_ENTITY = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
_HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_HR = re.compile(r"^ {0,3}([-*_])([ \t]*\1){2,}[ \t]*$")
_UL = re.compile(r"^( *)([-*+])[ \t]+(.*)$")
_OL = re.compile(r"^( *)(\d+)[.)][ \t]+(.*)$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*([\w+-]*)[ \t]*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
_HTML_BLOCK = re.compile(r"^ {0,3}<(/?)(div|table|thead|tbody|tr|td|th|p|ul|ol|li|pre|h[1-6]|blockquote|section|details|summary|hr|br|img|iframe|script|style|!--)", re.I)


def _escape_text(s: str) -> str:
    """Escape &, <, > but keep entities and inline HTML tags."""
    out = []
    pos = 0
    for m in _TAG.finditer(s):
        out.append(_escape_plain(s[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_escape_plain(s[pos:]))
    return "".join(out)


def _escape_plain(s: str) -> str:
    parts = []
    pos = 0
    for m in _ENTITY.finditer(s):
        parts.append(s[pos:m.start()].replace("&", "&amp;"))
        parts.append(m.group(0))
        pos = m.end()
    parts.append(s[pos:].replace("&", "&amp;"))
    return "".join(parts).replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Render inline markdown."""
    stash: list[str] = []

    def keep(fragment: str) -> str:
        stash.append(fragment)
        return f"\x00{len(stash) - 1}\x00"

    # Code spans first: their content is literal.
    text = re.sub(r"(`+)(.+?)\1", lambda m: keep(f"<code>{html.escape(m.group(2).strip(), quote=False)}</code>"), text)
    # Autolinks <http://...>
    text = re.sub(r"<((?:https?|ftp)://[^>\s]+)>", lambda m: keep(f'<a href="{m.group(1)}">{m.group(1)}</a>'), text)
    # Links [text](url "title")
    def link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2).strip()
        title = ""
        tm = re.match(r'^(\S+)\s+"(.*)"$', url)
        if tm:
            url, title = tm.group(1), f' title="{html.escape(tm.group(2))}"'
        return keep(f'<a href="{html.escape(url, quote=True)}"{title}>') + label + keep("</a>")
    text = re.sub(r"\[([^\[\]]*)\]\(([^()\s]+(?:\s+\"[^\"]*\")?)\)", link, text)
    # Hard line break: two+ trailing spaces before newline.
    text = re.sub(r" {2,}\n", lambda m: keep("<br />\n"), text)
    text = _escape_text(text)
    # Strong / emphasis (strong first). Underscore variants only at word boundaries.
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text, flags=re.S)
    text = re.sub(r"(?<![\w])__(?=\S)(.+?)(?<=\S)__(?![\w])", r"<strong>\1</strong>", text, flags=re.S)
    text = re.sub(r"(?<![\*\w])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\*\w])", r"<em>\1</em>", text, flags=re.S)
    text = re.sub(r"(?<![\w])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w])", r"<em>\1</em>", text, flags=re.S)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells = re.split(r"(?<!\\)\|", line)
    return [c.strip().replace("\\|", "|") for c in cells]


def _render_table(lines: list[str]) -> str:
    header = _split_row(lines[0])
    aligns = []
    for spec in _split_row(lines[1]):
        left, right = spec.startswith(":"), spec.endswith(":")
        aligns.append("center" if left and right else "right" if right else "left" if left else None)

    def cell(tag: str, content: str, i: int) -> str:
        a = aligns[i] if i < len(aligns) else None
        style = f' style="text-align: {a};"' if a else ""
        return f"<{tag}{style}>{inline(content)}</{tag}>"

    out = ["<table>", "<thead>", "<tr>"]
    out += [cell("th", h, i) for i, h in enumerate(header)]
    out += ["</tr>", "</thead>", "<tbody>"]
    for row in lines[2:]:
        cells = _split_row(row)
        cells = (cells + [""] * len(header))[:len(header)]
        out.append("<tr>")
        out += [cell("td", c, i) for i, c in enumerate(cells)]
        out.append("</tr>")
    out += ["</tbody>", "</table>"]
    return "\n".join(out)


def _list_item_match(line: str):
    return _UL.match(line) or _OL.match(line)


def _render_list(lines: list[str], start: int, base_indent: int) -> tuple[str, int]:
    """Render a list starting at lines[start]; returns (html, next_index)."""
    first = _list_item_match(lines[start])
    ordered = bool(_OL.match(lines[start])) and not _UL.match(lines[start])
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    i = start
    loose = False
    while i < len(lines):
        m = _list_item_match(lines[i])
        if not m or len(m.group(1)) != base_indent or (bool(_OL.match(lines[i]) and not _UL.match(lines[i])) != ordered):
            break
        body_lines = [m.group(3)]
        i += 1
        children: list[str] = []
        blank_seen = False
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                # A blank line inside a list: continue if the next non-blank line belongs to it.
                j = i
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    nm = _list_item_match(lines[j])
                    indent = len(lines[j]) - len(lines[j].lstrip(" "))
                    if (nm and len(nm.group(1)) == base_indent) or indent > base_indent:
                        loose = True
                        blank_seen = True
                        i = j
                        continue
                break
            sub = _list_item_match(line)
            indent = len(line) - len(line.lstrip(" "))
            if sub and indent > base_indent:
                child_html, i = _render_list(lines, i, len(sub.group(1)))
                children.append(child_html)
                continue
            if sub and indent <= base_indent:
                break
            if indent > base_indent or (not blank_seen and not _HEADING.match(line)):
                if children:
                    children.append(f"<p>{inline(line.strip())}</p>")
                else:
                    body_lines.append(line.strip())
                i += 1
                continue
            break
        text = inline("\n".join(body_lines))
        if loose:
            text = f"<p>{text}</p>"
        items.append("<li>" + text + ("\n" + "\n".join(children) + "\n" if children else "") + "</li>")
    start_attr = ""
    if ordered and first and first.group(2) != "1":
        start_attr = f' start="{int(first.group(2))}"'
    return f"<{tag}{start_attr}>\n" + "\n".join(items) + f"\n</{tag}>", i


def render(md: str) -> str:
    lines = md.replace("\r\n", "\n").replace("\t", "    ").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        fm = _FENCE.match(line)
        if fm:
            fence = fm.group(1)
            lang = fm.group(2)
            body = []
            i += 1
            while i < n and not lines[i].strip().startswith(fence):
                body.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>{html.escape(chr(10).join(body), quote=False)}\n</code></pre>")
            continue
        hm = _HEADING.match(line)
        if hm:
            level = len(hm.group(1))
            out.append(f"<h{level}>{inline(hm.group(2))}</h{level}>")
            i += 1
            continue
        if _HR.match(line):
            out.append("<hr />")
            i += 1
            continue
        if "|" in line and i + 1 < n and _TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1]:
            block = [line, lines[i + 1]]
            i += 2
            while i < n and lines[i].strip() and "|" in lines[i]:
                block.append(lines[i])
                i += 1
            out.append(_render_table(block))
            continue
        if stripped.startswith(">"):
            block = []
            while i < n and lines[i].strip() and (lines[i].lstrip().startswith(">") or block):
                if not lines[i].lstrip().startswith(">") and _HEADING.match(lines[i]):
                    break
                block.append(re.sub(r"^\s*> ?", "", lines[i]))
                i += 1
            out.append("<blockquote>\n" + render("\n".join(block)) + "\n</blockquote>")
            continue
        lm = _list_item_match(line)
        if lm:
            rendered, i = _render_list(lines, i, len(lm.group(1)))
            out.append(rendered)
            continue
        if _HTML_BLOCK.match(line):
            block = []
            while i < n and lines[i].strip():
                block.append(lines[i])
                i += 1
            out.append("\n".join(block))
            continue
        para = []
        while i < n and lines[i].strip():
            l = lines[i]
            if para and (_HEADING.match(l) or _FENCE.match(l) or _HR.match(l) or _list_item_match(l)
                         or l.lstrip().startswith(">")
                         or ("|" in l and i + 1 < n and _TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1])):
                break
            para.append(l.strip() if not l.endswith("  ") else l.lstrip())
            i += 1
        out.append(f"<p>{inline(chr(10).join(para))}</p>")
    return "\n".join(out)
