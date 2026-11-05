#!/usr/bin/env python3
"""Assemble section fragments into ONE self-contained HTML page and verify it.

Usage:
  python build_html.py --meta META.json --sections DIR --out OUT.html [--template T.html]
  python build_html.py --sections DIR --list-images

Fragments are the *.html files in DIR, assembled in filename order (00_intro.html,
01_..., 99_closing.html). Each chapter is a <section class="chapter" id="..."> whose
first <h2> becomes a table-of-contents entry; every <h3 id="..."> inside it becomes a
nested entry.

The build:
  - inlines every <img src="path"> as a base64 data URI (paths absolute or relative to DIR),
  - turns <a class="ts" data-t="SECONDS">m:ss</a> into links to that moment of the source
    video (YouTube, Vimeo) or plain chips when there is no online source,
  - builds the header, TL;DR, TOC and footer from META.json,
  - verifies: unique ids, every href="#id" resolves, no image left un-inlined, no
    external script/style, size under --max-mb.

Prints a JSON report. Exit 1 (and no output file) when verification fails.
--list-images prints the resolved image paths the fragments use, one per line (for the
anonymisation step), and exits.

META.json fields: title, subtitle, lang, type (tutorial|highlights|topics), source_url,
source_label, duration, date, tldr (list of strings), labels (object overriding the
English UI labels below). Standard library only.
"""
import argparse
import base64
import html
import json
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

LABELS = {
    "toc": "Contents",
    "tldr": "Key takeaways",
    "duration": "Duration",
    "source": "Source",
    "generated": "Generated",
    "read_time": "min read",
    "theme": "Toggle light/dark theme",
    "skip": "Skip to content",
    "top": "Back to top",
    "close": "Close",
    "image": "Enlarged image",
    "copy": "Copy",
    "copied": "Copied",
    "watch_at": "Watch this moment in the video",
    "footer": "Generated from the video with video-to-html.",
    "type_tutorial": "Tutorial",
    "type_highlights": "Highlights",
    "type_topics": "Full summary",
}

SECTION_RE = re.compile(r"<section\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</section>", re.S | re.I)
H2_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
H3_RE = re.compile(r"<h3\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</h3>", re.S | re.I)
ID_RE = re.compile(r"(?<![\w-])id=\"([^\"]+)\"", re.I)  # not data-id="..."
HREF_RE = re.compile(r"\bhref=\"#([^\"]*)\"", re.I)
IMG_RE = re.compile(r"(<img\b[^>]*?\bsrc=\")([^\"]+)(\"[^>]*>)", re.I)
# Any <a> with class "ts" and data-t, in either attribute order (checked in ts_sub).
TS_RE = re.compile(r"<a\b([^>]*\bdata-t=\"([\d.]+)\"[^>]*)>(.*?)</a>", re.S | re.I)
TS_CLASS_RE = re.compile(r"\bclass=\"(?:[^\"]*\s)?ts(?:\s[^\"]*)?\"", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(text):
    return html.unescape(TAG_RE.sub("", text)).strip()


def fragments(sections_dir):
    files = sorted(p for p in Path(sections_dir).glob("*.html") if p.is_file())
    if not files:
        sys.exit(f"No *.html fragments in {sections_dir}")
    return files, "\n".join(p.read_text(encoding="utf-8") for p in files)


def resolve(src, base):
    # resolve() normalises "..", and on Windows expands 8.3 short names, so
    # --list-images prints one canonical path per file.
    p = Path(src)
    return (p if p.is_absolute() else (base / p)).resolve()


def image_paths(content, base):
    return [resolve(m.group(2), base) for m in IMG_RE.finditer(content) if not m.group(2).startswith("data:")]


def ts_url(source_url, seconds):
    if not source_url:
        return None
    u = urlparse(source_url)
    host = u.netloc.lower()
    s = int(float(seconds))
    if "youtube.com" in host or "youtu.be" in host:
        q = [(k, v) for k, v in parse_qsl(u.query) if k != "t"] + [("t", f"{s}s")]
        return urlunparse(u._replace(query=urlencode(q)))
    if "vimeo.com" in host:
        return urlunparse(u._replace(fragment=f"t={s}s"))
    return None


def build_toc(content):
    items = []
    for sec_id, body in SECTION_RE.findall(content):
        h2 = H2_RE.search(body)
        if not h2:
            continue
        subs = "".join(
            f'<li><a href="#{html.escape(sid)}">{html.escape(strip_tags(t))}</a></li>' for sid, t in H3_RE.findall(body)
        )
        sub = f"<ol>{subs}</ol>" if subs else ""
        items.append(f'<li><a href="#{html.escape(sec_id)}">{html.escape(strip_tags(h2.group(1)))}</a>{sub}</li>')
    return f"<ol>{''.join(items)}</ol>", len(items)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--meta")
    ap.add_argument("--sections", required=True)
    ap.add_argument("--out")
    ap.add_argument("--template", default=str(Path(__file__).resolve().parent.parent / "assets" / "template.html"))
    ap.add_argument("--max-mb", type=float, default=15.0)
    ap.add_argument("--list-images", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    base = Path(args.sections).resolve()
    files, content = fragments(base)

    if args.list_images:
        seen = []
        for p in image_paths(content, base):
            if str(p) not in seen:
                seen.append(str(p))
        print("\n".join(seen))
        return
    if not args.meta or not args.out:
        sys.exit("--meta and --out are required unless --list-images is given")

    meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
    labels = {**LABELS, **(meta.get("labels") or {})}
    esc = html.escape
    errors, warnings = [], []

    # Timestamps -> links to the source, or plain chips.
    source_url = meta.get("source_url")

    def ts_sub(m):
        if not TS_CLASS_RE.search(m.group(1)):
            return m.group(0)
        url = ts_url(source_url, m.group(2))
        label = m.group(3)
        if url:
            return (f'<a class="ts" href="{esc(url)}" target="_blank" rel="noopener" '
                    f'title="{esc(labels["watch_at"])}">{label}</a>')
        return f'<span class="ts">{label}</span>'

    content = TS_RE.sub(ts_sub, content)

    # Inline images.
    inlined, total_bytes = 0, 0

    def img_sub(m):
        nonlocal inlined, total_bytes
        src = m.group(2)
        if src.startswith("data:"):
            return m.group(0)
        p = resolve(src, base)
        if not p.is_file():
            errors.append(f"missing image: {src}")
            return m.group(0)
        data = p.read_bytes()
        total_bytes += len(data)
        mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
        inlined += 1
        tail = m.group(3)
        if "loading=" not in m.group(0):
            # rstrip("/ ") keeps a self-closing <img ... /> valid.
            tail = tail[:-1].rstrip("/ ") + ' loading="lazy" decoding="async">'
        return f"{m.group(1)}data:{mime};base64,{base64.b64encode(data).decode('ascii')}{tail}"

    content = IMG_RE.sub(img_sub, content)
    for m in IMG_RE.finditer(content):
        if not m.group(2).startswith("data:") and f"missing image: {m.group(2)}" not in errors:
            errors.append(f"image not inlined: {m.group(2)[:120]}")
        if not re.search(r"\balt=\"[^\"]+\"", m.group(0)):
            warnings.append("image without alt text")

    toc, chapter_count = build_toc(content)
    if chapter_count == 0:
        errors.append('no <section id="..."> with an <h2> found: the TOC would be empty')

    # Header.
    kind = meta.get("type", "topics")
    chips = []
    if meta.get("duration"):
        chips.append(f"<li>⏱ {esc(labels['duration'])}: {esc(meta['duration'])}</li>")
    words = len(strip_tags(content).split())
    chips.append(f"<li>📖 {max(1, round(words / 220))} {esc(labels['read_time'])}</li>")
    if meta.get("source_label") or source_url:
        label = esc(meta.get("source_label") or source_url)
        link = f'<a href="{esc(source_url)}" target="_blank" rel="noopener">{label}</a>' if source_url else label
        chips.append(f"<li>🎬 {esc(labels['source'])}: {link}</li>")
    if meta.get("date"):
        chips.append(f"<li>🗓 {esc(labels['generated'])}: {esc(meta['date'])}</li>")
    tldr = ""
    if meta.get("tldr"):
        lis = "".join(f"<li>{esc(t)}</li>" for t in meta["tldr"])
        tldr = f'<section class="tldr" id="tldr" aria-labelledby="tldr-h"><h2 id="tldr-h">{esc(labels["tldr"])}</h2><ul>{lis}</ul></section>'
    subtitle = f'<p class="subtitle">{esc(meta["subtitle"])}</p>' if meta.get("subtitle") else ""
    header = (
        f'<header class="hero"><span class="badge">{esc(labels.get("type_" + kind, kind))}</span>'
        f'<h1>{esc(meta.get("title", "Video"))}</h1>{subtitle}<ul class="chips">{"".join(chips)}</ul>{tldr}</header>'
    )

    page = Path(args.template).read_text(encoding="utf-8")
    replacements = {
        "{{lang}}": esc(meta.get("lang", "en")),
        "{{title}}": esc(meta.get("title", "Video")),
        "{{description}}": esc(meta.get("subtitle") or meta.get("title", "")),
        "{{header}}": header,
        "{{toc}}": toc,
        "{{footer}}": esc(labels["footer"]),
    }
    for key, value in labels.items():
        replacements[f"{{{{label_{key}}}}}"] = esc(value)
    for key, value in replacements.items():
        page = page.replace(key, value)
    page = page.replace("{{content}}", content)  # last: content may contain braces
    leftover = sorted(set(re.findall(r"\{\{[a-z_]+\}\}", page.replace(content, ""))))
    if leftover:
        errors.append(f"unfilled template placeholders: {leftover}")

    # Verify anchors and ids on the final page.
    ids = ID_RE.findall(page)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"duplicate ids: {dupes}")
    idset = set(ids)
    broken = sorted({h for h in HREF_RE.findall(page) if h and h not in idset})
    if broken:
        errors.append(f"links to missing ids: {broken}")
    if re.search(r"<script\b[^>]*\bsrc=", page, re.I) or re.search(r"<link\b[^>]*rel=\"stylesheet\"", page, re.I):
        errors.append("external script or stylesheet found: the page must be self-contained")

    size_mb = len(page.encode("utf-8")) / 1_048_576
    if size_mb > args.max_mb:
        errors.append(f"page is {size_mb:.1f} MB, over the {args.max_mb} MB limit: use fewer or smaller images")

    report = {
        "fragments": [p.name for p in files],
        "chapters": chapter_count,
        "images_inlined": inlined,
        "ids": len(idset),
        "size_mb": round(size_mb, 2),
        "errors": errors,
        "warnings": sorted(set(warnings)),
    }
    if not errors:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        report["out"] = str(out.resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
