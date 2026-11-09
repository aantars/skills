#!/usr/bin/env python3
"""Fetch Confluence (Server / Data Center) images and attachments that sit behind a 2FA plugin.

The page text is best read through a Confluence MCP server. Those servers authenticate with a
Personal Access Token, which the REST API accepts, but /download/... URLs (images and attachments)
also go through the 2FA check and need the browser cookie Confluence_2FASessionVerified. This
script adds that cookie, stores it between sessions with its expiry date, and says when it must be
renewed. It can also export the page text as Markdown when no MCP server is available.

Commands (each prints one JSON object on stdout; human-readable notes go to stderr):
  status     URL                       API credentials and stored 2FA cookie state (never prints secrets)
  list       URL                       the page's attachments: name, kind (image/file), media type, size
  fetch      URL [options]             download images and/or attachments (and optionally the text)
  set-cookie URL [--expires DATE]      store a new 2FA cookie; interactive, run it in your own terminal

Exit codes: 0 ok, 1 error, 2 no API credentials, 3 2FA cookie missing, expired, rejected or unreadable.

API credentials (first found):
  1. CONFLUENCE_TOKEN env var: Personal Access Token, sent as Bearer
  2. --token-file, default ~/.confluence_token: file holding the token
  3. CONFLUENCE_USER + CONFLUENCE_PASSWORD env vars: Basic auth

2FA cookie store: ~/.confluence-read/cookies.json (change the folder with CONFLUENCE_READ_HOME).
One entry per wiki host: the cookie value, its expiry date, when it was saved and when it last
worked. On Windows the value is encrypted with DPAPI, so only your Windows account can read it;
elsewhere the file gets 0600 permissions. CONFLUENCE_COOKIE (env var) overrides the store for one run.

URLs accepted:
  https://wiki.example.com/spaces/KEY/pages/123456/Title
  https://wiki.example.com/pages/viewpage.action?pageId=123456
  https://wiki.example.com/display/KEY/Page+Title
  https://wiki.example.com/x/AbCdE   (tiny link)

Standard library only, Python 3.10+.
"""
import argparse
import base64
import datetime as dt
import getpass
import json
import os
import re
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

COOKIE_NAME = "Confluence_2FASessionVerified"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
DRAFT_TYPES = {"application/x-drawio-draft"}
EXPIRING_SOON = dt.timedelta(days=1)
EXIT_OK, EXIT_ERROR, EXIT_NO_AUTH, EXIT_COOKIE = 0, 1, 2, 3
SCRIPT = Path(__file__).resolve()

COOKIE_HELP = f"""
Images and attachments on this wiki are behind 2FA, so they need the browser cookie
{COOKIE_NAME}. To get it:

  1. Open the wiki in Chrome or Edge and sign in (enter the 2FA code if asked).
  2. Press F12 to open the developer tools.
  3. Open the "Application" tab (look under ">>" if you cannot see it).
  4. Left panel: Storage > Cookies > the wiki's address.
  5. Type {COOKIE_NAME} in the filter box and select the row.
  6. Note the "Expires / Max-Age" column: that is the expiry date you will be asked for.
  7. Double-click the "Value" cell, select all (Ctrl+A) and copy it (Ctrl+C).
     Copy only the value (for example "v18x...2A=="), not the name.

  Firefox: "Storage" tab > Cookies > the wiki's address.
"""


def out(obj, code=EXIT_OK):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def note(msg):
    print(msg, file=sys.stderr)


def now():
    return dt.datetime.now().astimezone()


# --------------------------------------------------------------------------- secret protection

def _dpapi(data, protect):
    """Encrypt or decrypt bytes with Windows DPAPI, bound to the current Windows user."""
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_wchar_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = Blob()
    desc = "confluence-read" if protect else None
    if not fn(ctypes.byref(blob_in), desc, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def protect(value):
    if os.name == "nt":
        return "dpapi", base64.b64encode(_dpapi(value.encode("utf-8"), True)).decode("ascii")
    return "plain", value


def unprotect(entry):
    if entry.get("protection") == "dpapi":
        return _dpapi(base64.b64decode(entry["value"]), False).decode("utf-8")
    return entry["value"]


# --------------------------------------------------------------------------- cookie store

def store_file():
    return Path(os.environ.get("CONFLUENCE_READ_HOME") or Path.home() / ".confluence-read") / "cookies.json"


def load_store():
    try:
        return json.loads(store_file().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_store(data):
    f = store_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    os.replace(tmp, f)


def update_entry(host, **fields):
    data = load_store()
    if host in data:
        data[host].update(fields)
        save_store(data)


def normalize_cookie(value, name=COOKIE_NAME):
    value = (value or "").strip()
    # the value is base64 and may end in "=="; it is only "name=value" if something follows the first "="
    if value and not re.match(r"[A-Za-z_][\w.-]*=(?!=|$)", value):
        value = f"{name}={value}"
    return value or None


def parse_expiry(text):
    """Return an ISO datetime string, None for a session cookie, or raise ValueError."""
    t = (text or "").strip()
    if not t or t.lower() in ("session", "sesion", "sesi\u00f3n", "unknown"):
        return None
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t):
        day = dt.datetime(int(m[1]), int(m[2]), int(m[3]), 23, 59, 59)
        return day.astimezone().isoformat(timespec="seconds")
    if m := re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t):  # DD/MM/YYYY or DD.MM.YYYY
        day = dt.datetime(int(m[3]), int(m[2]), int(m[1]), 23, 59, 59)
        return day.astimezone().isoformat(timespec="seconds")
    try:
        when = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"unrecognised date '{t}': use YYYY-MM-DD, DD/MM/YYYY or the DevTools value") from None
    if when.tzinfo is None:
        when = when.astimezone()
    return when.astimezone().isoformat(timespec="seconds")


def cookie_state(host):
    """State of the 2FA cookie for a host, without the value."""
    if os.environ.get("CONFLUENCE_COOKIE"):
        return {"state": "ok", "source": "env CONFLUENCE_COOKIE", "expires": None}
    entry = load_store().get(host)
    if not entry:
        return {"state": "missing", "source": None, "expires": None}
    info = {"source": str(store_file()), "expires": entry.get("expires"), "saved_at": entry.get("saved_at"),
            "last_ok": entry.get("last_ok"), "rejected_at": entry.get("rejected_at")}
    try:
        unprotect(entry)
    except Exception:  # noqa: BLE001 - other user, other machine, damaged file
        return {**info, "state": "unreadable"}
    exp = dt.datetime.fromisoformat(entry["expires"]) if entry.get("expires") else None
    if exp:
        info["days_left"] = round((exp - now()).total_seconds() / 86400, 1)
    if entry.get("rejected_at"):
        state = "rejected"
    elif exp and now() >= exp:
        state = "expired"
    elif exp and exp - now() < EXPIRING_SOON:
        state = "expiring"
    else:
        state = "ok"
    return {**info, "state": state}


def cookie_header(host):
    env = os.environ.get("CONFLUENCE_COOKIE")
    if env:
        return normalize_cookie(env)
    entry = load_store().get(host)
    if not entry:
        return None
    return normalize_cookie(unprotect(entry), entry.get("cookie_name", COOKIE_NAME))


def renew_info(url, state):
    reasons = {
        "missing": "no 2FA cookie is stored for this wiki",
        "expired": "the stored 2FA cookie has passed its expiry date",
        "rejected": "the wiki rejected the stored 2FA cookie (expired early or signed out)",
        "unreadable": "the stored 2FA cookie cannot be decrypted (other user or machine)",
    }
    return {
        "error": "cookie",
        "state": state.get("state"),
        "reason": reasons.get(state.get("state"), "the 2FA cookie cannot be used"),
        "expires": state.get("expires"),
        "renew_command": f'python "{SCRIPT}" set-cookie "{url}"',
        "renew_note": "Run renew_command in your own terminal: it explains where to find the cookie, asks for "
                      "its value (hidden) and its expiry date, checks it and saves both for next time.",
    }


# --------------------------------------------------------------------------- HTTP

class TwoFactorBlocked(RuntimeError):
    pass


def is_interactive():
    """True only with a real console. On Windows isatty() is also True for NUL, so check GetConsoleMode."""
    if not sys.stdin.isatty():
        return False
    if os.name != "nt":
        return True
    import ctypes
    import msvcrt
    mode = ctypes.c_uint32()
    handle = msvcrt.get_osfhandle(sys.stdin.fileno())
    return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))


def build_auth(token_file):
    token = os.environ.get("CONFLUENCE_TOKEN")
    if token:
        return f"Bearer {token.strip()}", "env CONFLUENCE_TOKEN"
    path = Path(token_file).expanduser()
    if path.is_file():
        return f"Bearer {path.read_text(encoding='utf-8').strip()}", str(path)
    user, password = os.environ.get("CONFLUENCE_USER"), os.environ.get("CONFLUENCE_PASSWORD")
    if user and password:
        return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode(), "env CONFLUENCE_USER/PASSWORD"
    return None, None


def build_ssl(args):
    if args.insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context(cafile=args.ca_bundle or os.environ.get("CONFLUENCE_CA_BUNDLE"))


def split_base(url):
    """(base URL including any context path, path) of a Confluence URL."""
    u = urllib.parse.urlsplit(url)
    m = re.search(r"/(spaces|pages|display|x|download|rest)/", u.path)
    ctx = u.path[: m.start()] if m else u.path.rstrip("/")
    return f"{u.scheme}://{u.netloc}{ctx}", u.path


class Client:
    def __init__(self, base, auth_header, ssl_ctx, cookie=None):
        self.base = base.rstrip("/")
        self.host = urllib.parse.urlsplit(self.base).netloc
        self.auth_header, self.ssl_ctx, self.cookie = auth_header, ssl_ctx, cookie

    def _open(self, url, accept="application/json"):
        if url.startswith("/"):
            url = self.base + url
        req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "confluence-read/1.0"})
        if self.auth_header:
            req.add_header("Authorization", self.auth_header)
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            return urllib.request.urlopen(req, context=self.ssl_ctx, timeout=60)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {e.code} on {url.split('?')[0]}: {body}") from None

    def json(self, path, **params):
        if params:
            path += ("&" if "?" in path else "?") + urllib.parse.urlencode(params)
        with self._open(path) as r:
            return json.load(r)

    def paged(self, path, limit=100, **params):
        start = 0
        while True:
            data = self.json(path, start=start, limit=limit, **params)
            results = data.get("results", [])
            yield from results
            if len(results) < limit or "next" not in data.get("_links", {}):
                return
            start += len(results)

    def download(self, url, dest=None, expected_type=None, probe=False):
        """Save url to dest. Raises TwoFactorBlocked when the wiki answers with its 2FA or login page."""
        with self._open(url, accept="*/*") as r:
            ctype = r.headers.get("Content-Type", "")
            final = r.geturl()
            # /download/* is not the REST API: a 2FA or login wall comes back as an HTML page with 200
            if "/twofactor/" in final or "login" in final.lower() or (
                    ctype.startswith("text/html") and not (expected_type or "").startswith("text/html")):
                raise TwoFactorBlocked(final.split("?")[0])
            if probe:
                r.read(1024)
                return
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)

    def final_url(self, url):
        with self._open(url, accept="text/html") as r:
            return r.geturl()


def resolve_page_id(client, url):
    if re.fullmatch(r"\d+", url):
        return url
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    if "pageId" in q:
        return q["pageId"][0]
    _, path = split_base(url)
    if m := re.search(r"/pages/(\d+)", path):
        return m.group(1)
    if m := re.search(r"/display/([^/]+)/([^/?#]+)", path):
        space, title = m.group(1), urllib.parse.unquote_plus(m.group(2))
        res = client.json("/rest/api/content", spaceKey=space, title=title)["results"]
        if not res:
            raise RuntimeError(f"page '{title}' not found in space {space}")
        return res[0]["id"]
    if "/x/" in path:  # tiny link: follow the redirect
        final = client.final_url(url)
        if final != url:
            return resolve_page_id(client, final)
    raise RuntimeError(f"cannot work out the page id from {url}")


# --------------------------------------------------------------------------- attachments

def kind_of(name, media_type):
    if (media_type or "").startswith("image/") or Path(name).suffix.lower() in IMAGE_EXT:
        return "image"
    return "file"


def list_attachments(client, page_id):
    items = []
    for a in client.paged(f"/rest/api/content/{page_id}/child/attachment"):
        ext = a.get("extensions", {})
        media_type = ext.get("mediaType")
        name = a["title"]
        items.append({
            "name": name,
            "kind": kind_of(name, media_type),
            "media_type": media_type,
            "size": ext.get("fileSize"),
            "draft": media_type in DRAFT_TYPES or (name.startswith("~") and name.endswith(".tmp")),
            "download": a["_links"]["download"],
        })
    return items


def safe_name(s, maxlen=120):
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip(" .")
    return s[:maxlen] or "_"


LONG_PREFIX = "\\\\?\\"


def long_path(p):
    r"""On Windows, prefix \\?\ to get past the 260-character MAX_PATH limit."""
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith(LONG_PREFIX):
        p = LONG_PREFIX + p
    return Path(p)


def show(p):
    return str(p).removeprefix(LONG_PREFIX)


# --------------------------------------------------------------------------- HTML -> Markdown (fetch --text)

VOID = {"br", "img", "hr", "input", "meta", "link", "col", "source", "area", "wbr"}
SKIP = {"script", "style", "noscript"}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("root", {})

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.children.append(data)


class MarkdownRenderer:
    def __init__(self, img_resolver, link_resolver):
        self.img_resolver, self.link_resolver = img_resolver, link_resolver

    def convert(self, html):
        tb = TreeBuilder()
        tb.feed(html)
        md = self.children(tb.root)
        md = re.sub(r"[ \t]+\n", "\n", md)
        return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"

    def children(self, node, **ctx):
        return "".join(self.render(c, **ctx) for c in node.children)

    @staticmethod
    def text_of(node):
        if isinstance(node, str):
            return node
        if node.tag == "br":
            return "\n"
        return "".join(MarkdownRenderer.text_of(c) for c in node.children)

    def render(self, n, pre=False, cell=False):
        if isinstance(n, str):
            return n if pre else re.sub(r"\s+", " ", n)
        t, cls = n.tag, n.attrs.get("class", "") or ""
        inner = lambda: self.children(n, pre=pre, cell=cell)  # noqa: E731
        if t in SKIP:
            return ""
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            return f"\n\n{'#' * int(t[1])} {inner().strip()}\n\n"
        if t in ("p", "div", "section", "article", "header", "footer"):
            body = inner()
            return body if cell else f"\n\n{body.strip()}\n\n" if body.strip() else ""
        if t == "br":
            return "<br>" if cell else "  \n"
        if t == "hr":
            return "\n\n---\n\n"
        if t in ("strong", "b"):
            s = inner()
            return f"**{s.strip()}**" if s.strip() else s
        if t in ("em", "i"):
            s = inner()
            return f"*{s.strip()}*" if s.strip() else s
        if t in ("del", "s"):
            return f"~~{inner().strip()}~~"
        if t == "code" and not pre:
            return f"`{self.text_of(n)}`"
        if t == "pre":
            code = self.text_of(n).strip("\n")
            lang = n.attrs.get("data-syntaxhighlighter-params", "")
            lang = m.group(1) if (m := re.search(r"brush:\s*([\w+-]+)", lang)) else ""
            return f"\n\n```{lang}\n{code}\n```\n\n"
        if t == "a":
            text, href = inner().strip(), n.attrs.get("href")
            return f"[{text}]({self.link_resolver(href)})" if href and text else text
        if t == "img":
            if "emoticon" in cls:
                return n.attrs.get("data-emoji-fallback") or n.attrs.get("alt", "")
            src = n.attrs.get("data-image-src") or n.attrs.get("src", "")
            alt = n.attrs.get("alt") or n.attrs.get("data-linked-resource-default-alias") or ""
            return f"![{alt}]({self.img_resolver(src)})" if src else ""
        if t in ("ul", "ol"):
            return self.render_list(n, ordered=(t == "ol"))
        if t == "table":
            return self.render_table(n)
        if t == "blockquote":
            body = inner().strip()
            return "\n\n" + "\n".join("> " + line for line in body.splitlines()) + "\n\n"
        return inner()

    def render_list(self, n, ordered):
        lines, i = [], 1
        for li in n.children:
            if isinstance(li, str) or li.tag != "li":
                continue
            marker = f"{i}. " if ordered else "- "
            body = re.sub(r"\n{2,}", "\n", self.children(li).strip())
            parts = body.splitlines() or [""]
            lines.append(marker + parts[0])
            lines += [" " * len(marker) + p for p in parts[1:]]
            i += 1
        return "\n\n" + "\n".join(lines) + "\n\n"

    def render_table(self, n):
        rows = []

        def walk(node):
            for c in node.children:
                if isinstance(c, str):
                    continue
                if c.tag == "tr":
                    cells = [x for x in c.children if not isinstance(x, str) and x.tag in ("td", "th")]
                    rows.append([self.cell(x) for x in cells])
                elif c.tag != "table":  # do not enter nested tables
                    walk(c)

        walk(n)
        if not rows:
            return ""
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
        lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n\n" + "\n".join(lines) + "\n\n"

    def cell(self, node):
        s = self.children(node, cell=True)
        return re.sub(r"\s*\n\s*", "<br>", s.strip()).replace("|", "\\|")


# --------------------------------------------------------------------------- commands

def make_client(args, with_cookie):
    base = args.base or split_base(args.url)[0]
    if not base.startswith("http"):
        out({"error": f"need a full URL or --base for '{args.url}'"}, EXIT_ERROR)
    auth, source = build_auth(args.token_file)
    host = urllib.parse.urlsplit(base).netloc
    cookie = cookie_header(host) if with_cookie else None
    return Client(base, auth, build_ssl(args), cookie), source


def require_auth(client, url):
    if not client.auth_header:
        out({"error": "auth", "reason": "no Confluence API credentials",
             "fix": "Create a Personal Access Token in Confluence (Profile > Personal Access Tokens) and save it "
                    "in ~/.confluence_token, or set CONFLUENCE_TOKEN.", "url": url}, EXIT_NO_AUTH)


def cmd_status(args):
    base = args.base or split_base(args.url)[0]
    host = urllib.parse.urlsplit(base).netloc
    _, source = build_auth(args.token_file)
    state = cookie_state(host)
    result = {"host": host, "auth": source or "none", "cookie": state}
    if state["state"] not in ("ok", "expiring"):
        result["renew"] = renew_info(args.url, state)
    elif state["state"] == "expiring":
        result["warning"] = f"the 2FA cookie expires on {state['expires']}; renew it soon with set-cookie"
    code = EXIT_NO_AUTH if not source else EXIT_OK if state["state"] in ("ok", "expiring") else EXIT_COOKIE
    out(result, code)


def cmd_list(args):
    client, _ = make_client(args, with_cookie=False)
    require_auth(client, args.url)
    page_id = resolve_page_id(client, args.url)
    page = client.json(f"/rest/api/content/{page_id}")
    items = [{k: v for k, v in a.items() if k != "download"} for a in list_attachments(client, page_id)]
    live = [a for a in items if not a["draft"]]
    out({"page_id": page_id, "title": page["title"],
         "counts": {"images": sum(a["kind"] == "image" for a in live), "files": sum(a["kind"] == "file" for a in live),
                    "drafts_ignored": len(items) - len(live)},
         "attachments": live})


def cmd_fetch(args):
    client, _ = make_client(args, with_cookie=args.what != "none")
    require_auth(client, args.url)
    host = client.host
    state = cookie_state(host) if args.what != "none" else None
    if state and state["state"] not in ("ok", "expiring"):
        note(f"2FA cookie {state['state']}: run set-cookie to renew it (see renew_command).")
        out(renew_info(args.url, state), EXIT_COOKIE)

    page_id = resolve_page_id(client, args.url)
    expand = "body.export_view,version,space" if args.text else "version,space"
    page = client.json(f"/rest/api/content/{page_id}", expand=expand)
    folder = long_path(Path(args.out) / page_id)
    att_dir = folder / "attachments"

    wanted = {"images": {"image"}, "files": {"file"}, "all": {"image", "file"}, "none": set()}[args.what]
    only = set(args.only or [])
    downloaded, skipped, local_by_name = [], [], {}
    blocked = None
    items = list_attachments(client, page_id) if wanted else []
    for a in items:
        if a["draft"] or a["kind"] not in wanted or (only and a["name"] not in only):
            continue
        if a["size"] and a["size"] > args.max_mb * 1024 * 1024:
            skipped.append({"name": a["name"], "reason": f"larger than {args.max_mb} MB ({a['size']} bytes)"})
            continue
        if blocked:
            skipped.append({"name": a["name"], "reason": "2FA cookie rejected"})
            continue
        att_dir.mkdir(parents=True, exist_ok=True)
        dest = att_dir / safe_name(a["name"])
        try:
            client.download(a["download"], dest, a["media_type"])
        except TwoFactorBlocked as e:
            blocked = str(e)
            skipped.append({"name": a["name"], "reason": "2FA cookie rejected"})
            continue
        except Exception as e:  # noqa: BLE001 - keep going with the rest
            skipped.append({"name": a["name"], "reason": f"error: {e}"})
            continue
        local_by_name[a["name"]] = dest
        downloaded.append({"name": a["name"], "kind": a["kind"], "media_type": a["media_type"],
                           "size": a["size"], "path": show(dest)})

    if only - {a["name"] for a in items}:
        skipped += [{"name": n, "reason": "no attachment with this name"} for n in sorted(only - {a["name"] for a in items})]

    text_path = None
    if args.text:
        folder.mkdir(parents=True, exist_ok=True)

        def img_resolver(src):
            name = urllib.parse.unquote(urllib.parse.urlsplit(src).path.rsplit("/", 1)[-1])
            if name in local_by_name:
                return "attachments/" + urllib.parse.quote(local_by_name[name].name)
            return urllib.parse.urljoin(client.base + "/", src)

        def link_resolver(href):
            return href if href.startswith(("#", "mailto:")) else urllib.parse.urljoin(client.base + "/", href)

        ver = page.get("version", {})
        header = (f"# {page['title']}\n\n- URL: {client.base + page['_links']['webui']}\n"
                  f"- Space: {page.get('space', {}).get('key')}\n"
                  f"- Version: {ver.get('number')} ({ver.get('when')}), by {ver.get('by', {}).get('displayName')}\n\n---\n\n")
        md = MarkdownRenderer(img_resolver, link_resolver).convert(page["body"]["export_view"]["value"])
        text_path = folder / "page.md"
        text_path.write_text(header + md, encoding="utf-8")

    result = {"page_id": page_id, "title": page["title"], "folder": show(folder), "text": show(text_path) if text_path else None,
              "downloaded": downloaded, "skipped": skipped}
    if blocked:
        if not os.environ.get("CONFLUENCE_COOKIE"):
            update_entry(host, rejected_at=now().isoformat(timespec="seconds"))
        note("The wiki rejected the 2FA cookie: run set-cookie to store a new one (see renew_command).")
        result.update(renew_info(args.url, {**cookie_state(host), "state": "rejected"}))
        out(result, EXIT_COOKIE)
    if downloaded and not os.environ.get("CONFLUENCE_COOKIE"):
        update_entry(host, last_ok=now().isoformat(timespec="seconds"))
    if state:
        result["cookie"] = cookie_state(host)
        if result["cookie"]["state"] == "expiring":
            result["warning"] = f"the 2FA cookie expires on {result['cookie']['expires']}; renew it soon with set-cookie"
    out(result)


def cmd_set_cookie(args):
    base = args.base or split_base(args.url)[0]
    host = urllib.parse.urlsplit(base).netloc
    if not host:
        out({"error": f"need the wiki URL, got '{args.url}'"}, EXIT_ERROR)
    if not is_interactive():
        out({"error": "set-cookie is interactive: run it in your own terminal, not through an agent",
             "command": f'python "{SCRIPT}" set-cookie "{args.url}"'}, EXIT_ERROR)
    note(COOKIE_HELP)
    value = normalize_cookie(getpass.getpass(f"Value of {COOKIE_NAME} (hidden; Enter to cancel): "), args.cookie_name)
    if not value:
        note("Cancelled, nothing saved.")
        sys.exit(EXIT_ERROR)

    expires = None
    if args.expires:
        expires = parse_expiry(args.expires)
    else:
        while True:
            raw = input("Expiry date (the 'Expires / Max-Age' value, e.g. 2026-11-10T14:03:22.000Z, "
                        "or YYYY-MM-DD; Enter if it says 'Session'): ")
            try:
                expires = parse_expiry(raw)
                break
            except ValueError as e:
                note(f"  {e}")

    # check it against a real attachment on the page, when there is one
    verified = None
    auth, _ = build_auth(args.token_file)
    if auth and split_base(args.url)[1].strip("/"):
        try:
            client = Client(base, auth, build_ssl(args), value)
            items = [a for a in list_attachments(client, resolve_page_id(client, args.url)) if not a["draft"]]
            if items:
                smallest = min(items, key=lambda a: a["size"] or 0)
                client.download(smallest["download"], probe=True)
                verified = True
        except TwoFactorBlocked:
            verified = False
        except Exception as e:  # noqa: BLE001
            note(f"Could not check the cookie against the wiki: {e}")
    if verified is False:
        note("The wiki rejected this cookie. Check that you copied the whole value of the right cookie.")
        if input("Save it anyway? [y/N]: ").strip().lower() not in ("y", "yes", "s", "si"):
            sys.exit(EXIT_COOKIE)

    protection, stored = protect(value)
    data = load_store()
    stamp = now().isoformat(timespec="seconds")
    data[host] = {"cookie_name": args.cookie_name, "protection": protection, "value": stored, "expires": expires,
                  "saved_at": stamp, "last_ok": stamp if verified else None, "rejected_at": None}
    save_store(data)
    note(f"Saved for {host} in {store_file()}"
         + (f", expires {expires}." if expires else ", no expiry date (session cookie).")
         + (" Checked against the wiki: OK." if verified else " Not checked against the wiki." if verified is None else ""))
    out({"host": host, "saved": True, "expires": expires, "verified": verified, "store": str(store_file())})


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(description="Confluence images and attachments behind 2FA, with a stored cookie.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("url", help="Confluence page URL (or the wiki's base URL for status / set-cookie)")
    common.add_argument("--base", help="Confluence base URL, when it cannot be worked out from the URL")
    common.add_argument("--token-file", default="~/.confluence_token", help="file holding the Personal Access Token")
    common.add_argument("--ca-bundle", help="PEM CA file (corporate proxy); default env CONFLUENCE_CA_BUNDLE")
    common.add_argument("--insecure", action="store_true", help="do not verify the TLS certificate")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", parents=[common], help="API credentials and 2FA cookie state")
    sub.add_parser("list", parents=[common], help="list the page's attachments")
    f = sub.add_parser("fetch", parents=[common], help="download images and/or attachments")
    f.add_argument("--what", choices=["images", "files", "all", "none"], default="all",
                   help="images, other attachments, both (all) or none (with --text: text only)")
    f.add_argument("--only", action="append", metavar="NAME", help="download only this attachment (repeatable)")
    f.add_argument("--text", action="store_true", help="also write the page text as page.md")
    f.add_argument("--max-mb", type=float, default=25, help="skip attachments larger than this (default 25)")
    f.add_argument("-o", "--out", default=os.path.join(tempfile.gettempdir(), "confluence-read"),
                   help="output folder; files go to <out>/<pageId>/ (default: system temp)")
    s = sub.add_parser("set-cookie", parents=[common], help="store a new 2FA cookie (interactive)")
    s.add_argument("--expires", help="expiry date (YYYY-MM-DD, DD/MM/YYYY or ISO datetime); asked if omitted")
    s.add_argument("--cookie-name", default=COOKIE_NAME, help=f"cookie name (default {COOKIE_NAME})")
    args = p.parse_args()
    try:
        {"status": cmd_status, "list": cmd_list, "fetch": cmd_fetch, "set-cookie": cmd_set_cookie}[args.cmd](args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        out({"error": str(e)}, EXIT_ERROR)


if __name__ == "__main__":
    main()
