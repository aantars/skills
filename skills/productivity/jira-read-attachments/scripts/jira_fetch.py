#!/usr/bin/env python3
"""Read a Jira (Server / Data Center) issue and download its attachments with a browser session cookie.

The cookie is stored between runs (encrypted with DPAPI on Windows) together with its optional expiry
date, so it never has to be pasted into a chat. Everything goes through the REST API with that cookie:
issue fields, comments, links and the attachment files.

Commands (each prints one JSON object on stdout; human-readable notes go to stderr):
  status     URL                    cookie state, plus a live check against the server (never prints secrets)
  list       URL                    the issue's attachments: name, kind (image/file), media type, size
  fetch      URL [options]          write the issue as Markdown and/or download attachments
  set-cookie URL [--expires DATE]   store a new session cookie; interactive, run it in your own terminal

Exit codes: 0 ok, 1 error, 3 cookie missing, expired, rejected or unreadable.

Cookie store: ~/.jira-read/cookies.json (change the folder with JIRA_READ_HOME). One entry per Jira host.
JIRA_COOKIE (env var) overrides the store for one run. The cookie is only ever sent to the Jira host
it was stored for, and dropped on redirects to another host.

URLs accepted:
  https://jira.example.com/browse/PROJ-123
  https://jira.example.com/jira/browse/PROJ-123          (context path)
  https://jira.example.com/projects/PROJ/issues/PROJ-123
  https://jira.example.com/secure/RapidBoard.jspa?...&selectedIssue=PROJ-123
  PROJ-123 together with --base https://jira.example.com

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
from pathlib import Path

DEFAULT_COOKIE = "JSESSIONID"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
EXPIRING_SOON = dt.timedelta(days=1)
EXIT_OK, EXIT_ERROR, EXIT_COOKIE = 0, 1, 3
SCRIPT = Path(__file__).resolve()
ISSUE_KEY = re.compile(r"\b[A-Z][A-Z0-9_]+-\d+\b")

COOKIE_HELP = """
This script needs your logged-in Jira session cookie. The easiest complete way:

  1. Open Jira in Chrome or Edge and sign in (including any 2FA step).
  2. Press F12, open the "Network" tab and reload the page (F5).
  3. Click any request to the Jira host (for example the first one, the page itself).
  4. In "Headers" > "Request Headers" find "Cookie" and copy its whole value.

Alternative with a single cookie: "Application" tab > Storage > Cookies > the Jira address >
copy the Value of JSESSIONID (the script then stores it as JSESSIONID=<value>). If your Jira sits
behind a 2FA or SSO plugin, the full Cookie header from the Network tab is the safer choice.

Firefox: Network tab > a request > "Cookies" / "Request Headers" > Cookie.
"""


def out(obj, code=EXIT_OK):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def note(msg):
    print(msg, file=sys.stderr)


def now():
    return dt.datetime.now().astimezone()


# --------------------------------------------------------------------------- secret protection

def _dpapi(data, protect_it):
    """Encrypt or decrypt bytes with Windows DPAPI, bound to the current Windows user."""
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if protect_it else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_wchar_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                   ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = Blob()
    desc = "jira-read" if protect_it else None
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
    return Path(os.environ.get("JIRA_READ_HOME") or Path.home() / ".jira-read") / "cookies.json"


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


def normalize_cookie(value, name=DEFAULT_COOKIE):
    """Accept 'Cookie: a=b; c=d', 'a=b; c=d' or a bare value (stored as <name>=value)."""
    v = (value or "").strip().strip('"')
    v = re.sub(r"^cookie:\s*", "", v, flags=re.I)
    if re.search(r"[\x00-\x1f\x7f]", v):
        raise ValueError("the cookie contains control characters or line breaks")
    # a bare base64 value may end in "=="; it is only name=value if something follows the first "="
    if v and not re.match(r"[A-Za-z_][\w.-]*=(?!=|$)", v):
        v = f"{name}={v}"
    return v or None


def parse_expiry(text):
    """Return an ISO datetime string, None for a session cookie, or raise ValueError."""
    t = (text or "").strip()
    if not t or t.lower() in ("session", "sesion", "sesi\u00f3n", "unknown"):
        return None
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", t):
        return dt.datetime(int(m[1]), int(m[2]), int(m[3]), 23, 59, 59).astimezone().isoformat(timespec="seconds")
    if m := re.fullmatch(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", t):  # DD/MM/YYYY or DD.MM.YYYY
        return dt.datetime(int(m[3]), int(m[2]), int(m[1]), 23, 59, 59).astimezone().isoformat(timespec="seconds")
    try:
        when = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"unrecognised date '{t}': use YYYY-MM-DD, DD/MM/YYYY or the DevTools value") from None
    if when.tzinfo is None:
        when = when.astimezone()
    return when.astimezone().isoformat(timespec="seconds")


def cookie_state(host):
    """State of the stored cookie for a host, without the value."""
    if os.environ.get("JIRA_COOKIE"):
        return {"state": "ok", "source": "env JIRA_COOKIE", "expires": None}
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
    env = os.environ.get("JIRA_COOKIE")
    if env:
        return normalize_cookie(env)
    entry = load_store().get(host)
    if not entry:
        return None
    return normalize_cookie(unprotect(entry), entry.get("cookie_name", DEFAULT_COOKIE))


def renew_info(url, state):
    reasons = {
        "missing": "no session cookie is stored for this Jira",
        "expired": "the stored session cookie has passed its expiry date",
        "rejected": "Jira rejected the stored session cookie (session ended or signed out)",
        "unreadable": "the stored session cookie cannot be decrypted (other user or machine)",
    }
    return {
        "error": "cookie",
        "state": state.get("state"),
        "reason": reasons.get(state.get("state"), "the session cookie cannot be used"),
        "expires": state.get("expires"),
        "renew_command": f'python "{SCRIPT}" set-cookie "{url}"',
        "renew_note": "Run renew_command in your own terminal: it explains where to find the cookie, asks for "
                      "its value (hidden) and an optional expiry date, checks it and saves it for next time.",
    }


# --------------------------------------------------------------------------- HTTP

class CookieBlocked(RuntimeError):
    """Jira answered with a login / 2FA wall instead of the data."""


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward the cookie to another host on a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            for h in ("Cookie", "Authorization"):
                new.headers.pop(h, None)
                new.unredirected_hdrs.pop(h, None)
        return new


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


def build_ssl(args):
    if args.insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context(cafile=args.ca_bundle or os.environ.get("JIRA_CA_BUNDLE"))


def split_base(url):
    """(base URL including any context path, path + query) of a Jira URL."""
    u = urllib.parse.urlsplit(url)
    m = re.search(r"/(browse|projects|secure|rest|issues|plugins|download)(/|$)", u.path)
    ctx = u.path[: m.start()] if m else u.path.rstrip("/")
    return f"{u.scheme}://{u.netloc}{ctx}", u.path + ("?" + u.query if u.query else "")


def issue_key_of(url):
    m = ISSUE_KEY.search(urllib.parse.unquote(url))
    if not m:
        raise RuntimeError(f"cannot find an issue key (like PROJ-123) in '{url}'")
    return m.group(0)


class Client:
    def __init__(self, base, ssl_ctx, cookie):
        self.base = base.rstrip("/")
        self.host = urllib.parse.urlsplit(self.base).netloc
        self.cookie = cookie
        self.opener = urllib.request.build_opener(SafeRedirect, urllib.request.HTTPSHandler(context=ssl_ctx))

    def _open(self, url, accept):
        if url.startswith("/"):
            url = self.base + url
        req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "jira-read/1.0",
                                                   "X-Atlassian-Token": "no-check"})
        if self.cookie and urllib.parse.urlsplit(url).netloc == self.host:
            req.add_header("Cookie", self.cookie)
        try:
            return self.opener.open(req, timeout=60)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            reason = e.headers.get("X-Seraph-LoginReason", "")
            if e.code == 401 or (e.code == 403 and reason and reason != "OK"):
                raise CookieBlocked(f"HTTP {e.code} {reason}".strip()) from None
            if e.code == 403:
                raise RuntimeError(f"HTTP 403 on {url.split('?')[0]}: no permission or CAPTCHA required") from None
            raise RuntimeError(f"HTTP {e.code} on {url.split('?')[0]}: {body}") from None

    def json(self, path, **params):
        if params:
            path += ("&" if "?" in path else "?") + urllib.parse.urlencode(params)
        with self._open(path, "application/json") as r:
            ctype = r.headers.get("Content-Type", "")
            if "json" not in ctype:  # an SSO / 2FA page answers 200 with HTML
                raise CookieBlocked(r.geturl().split("?")[0])
            return json.load(r)

    def download(self, url, dest=None, probe=False):
        with self._open(url, "*/*") as r:
            final = r.geturl()
            if "login" in final.lower() or "twofactor" in final.lower() or r.headers.get(
                    "Content-Type", "").startswith("text/html") and not final.lower().endswith((".htm", ".html")):
                raise CookieBlocked(final.split("?")[0])
            if probe:
                r.read(1024)
                return
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)


# --------------------------------------------------------------------------- attachments and text

def kind_of(name, media_type):
    if (media_type or "").startswith("image/") or Path(name).suffix.lower() in IMAGE_EXT:
        return "image"
    return "file"


def attachments_of(issue):
    items = []
    for a in issue["fields"].get("attachment") or []:
        name = a["filename"]
        items.append({
            "id": str(a.get("id")),
            "name": name,
            "kind": kind_of(name, a.get("mimeType")),
            "media_type": a.get("mimeType"),
            "size": a.get("size"),
            "created": a.get("created"),
            "author": (a.get("author") or {}).get("displayName"),
            "download": a["content"],
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


def tidy_internal(s):
    """Jira plugins return some fields as Java toString() text; reduce them to what a reader needs."""
    if ".Sprint@" in s:
        name = re.search(r"\bname=(.*?),(?=\w+=)", s)
        state = re.search(r"\bstate=(\w+)", s)
        return f"{name.group(1) if name else 'sprint'} ({state.group(1).lower()})" if state or name else ""
    if "summaryBean=" in s:  # development panel: keep the pull request counts only
        counts = {k: re.search(rf"\b{k}Count=(\d+)", s) for k in ("merged", "open", "declined")}
        parts = [f"{m.group(1)} {k}" for k, m in counts.items() if m and m.group(1) != "0"]
        return "pull requests: " + ", ".join(parts) if parts else ""
    return s


def fmt(v, limit=600):
    """Compact, readable text for any Jira field value."""
    if v is None:
        return ""
    if isinstance(v, str):
        s = tidy_internal(v)
    elif isinstance(v, (int, float, bool)):
        s = str(v)
    elif isinstance(v, list):
        s = ", ".join(x for x in (fmt(i, limit) for i in v) if x)
    elif isinstance(v, dict):
        for k in ("displayName", "value", "name", "key", "title"):
            if v.get(k):
                s = str(v[k])
                break
        else:
            s = json.dumps(v, ensure_ascii=False)
    else:
        s = str(v)
    return s if len(s) <= limit else s[:limit] + "..."


def link_images(text, local_by_name):
    """Point wiki-markup images (!name.png|width=300!) at the downloaded files."""
    def sub(m):
        name = m.group(1)
        return f"[image: attachments/{local_by_name[name].name}]" if name in local_by_name else m.group(0)
    return re.sub(r"!([^!\s|\n]+)(?:\|[^!\n]*)?!", sub, text or "")


def issue_markdown(client, issue, saved, names):
    f, key = issue["fields"], issue["key"]
    lines = [f"# {key}: {f.get('summary', '')}", "",
             f"- URL: {client.base}/browse/{key}"]
    for label, field in (("Type", "issuetype"), ("Status", "status"), ("Priority", "priority"),
                         ("Resolution", "resolution"), ("Assignee", "assignee"), ("Reporter", "reporter"),
                         ("Created", "created"), ("Updated", "updated"), ("Labels", "labels"),
                         ("Components", "components"), ("Fix versions", "fixVersions"),
                         ("Affects versions", "versions"), ("Parent", "parent")):
        if val := fmt(f.get(field)):
            lines.append(f"- {label}: {val}")
    lines += ["", "## Description", "", link_images(f.get("description") or "(empty)", saved), ""]

    links = f.get("issuelinks") or []
    if links or f.get("subtasks"):
        lines += ["## Links", ""]
        for ln in links:
            other = ln.get("outwardIssue") or ln.get("inwardIssue") or {}
            kind = ln["type"]["outward" if "outwardIssue" in ln else "inward"]
            lines.append(f"- {kind}: {other.get('key')} - {other.get('fields', {}).get('summary', '')}")
        for st in f.get("subtasks") or []:
            lines.append(f"- subtask: {st.get('key')} - {st.get('fields', {}).get('summary', '')}")
        lines.append("")

    custom = [(names.get(k, k), fmt(v)) for k, v in f.items() if k.startswith("customfield_") and fmt(v)
              and not re.search(r"\brank\b", names.get(k, k), re.I)]  # ranking values are noise
    if custom:
        lines += ["## Custom fields", ""] + [f"- {n}: {v}" for n, v in custom] + [""]

    atts = attachments_of(issue)
    if atts:
        lines += ["## Attachments", ""]
        for a in atts:
            where = f"attachments/{saved[a['name']].name}" if a["name"] in saved else "not downloaded"
            lines.append(f"- {a['name']} ({a['media_type']}, {a['size']} bytes, {a['author']}, {a['created']}): {where}")
        lines.append("")

    comments = (f.get("comment") or {}).get("comments") or []
    if comments:
        lines += [f"## Comments ({len(comments)})", ""]
        for c in comments:
            lines += [f"### {(c.get('author') or {}).get('displayName')} - {c.get('created')}", "",
                      link_images(c.get("body"), saved), ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- commands

def make_client(args, with_cookie=True):
    base = args.base or split_base(args.url)[0]
    if not base.startswith("http"):
        out({"error": f"need a full URL or --base for '{args.url}'"}, EXIT_ERROR)
    host = urllib.parse.urlsplit(base).netloc
    try:
        cookie = cookie_header(host) if with_cookie else None
    except Exception:  # noqa: BLE001 - unreadable store entry, reported through cookie_state
        cookie = None
    return Client(base, build_ssl(args), cookie)


def require_cookie(client, url):
    state = cookie_state(client.host)
    if state["state"] not in ("ok", "expiring"):
        note(f"Session cookie {state['state']}: run set-cookie to renew it (see renew_command).")
        out(renew_info(url, state), EXIT_COOKIE)
    return state


def mark_rejected(host):
    if not os.environ.get("JIRA_COOKIE"):
        update_entry(host, rejected_at=now().isoformat(timespec="seconds"))


def cmd_status(args):
    client = make_client(args)
    state = cookie_state(client.host)
    result = {"host": client.host, "cookie": state}
    if state["state"] not in ("ok", "expiring"):
        result["renew"] = renew_info(args.url, state)
        out(result, EXIT_COOKIE)
    try:
        me = client.json("/rest/api/2/myself")
        result["live"] = {"ok": True, "user": me.get("displayName") or me.get("name")}
        if not os.environ.get("JIRA_COOKIE"):
            update_entry(client.host, last_ok=now().isoformat(timespec="seconds"), rejected_at=None)
        result["cookie"] = cookie_state(client.host)
    except CookieBlocked as e:
        mark_rejected(client.host)
        result["live"] = {"ok": False, "detail": str(e)}
        result["renew"] = renew_info(args.url, {**cookie_state(client.host), "state": "rejected"})
        out(result, EXIT_COOKIE)
    except Exception as e:  # noqa: BLE001 - network down, proxy, TLS
        result["live"] = {"ok": None, "detail": f"could not reach Jira: {e}"}
    if state["state"] == "expiring":
        result["warning"] = f"the session cookie expires on {state['expires']}; renew it soon with set-cookie"
    out(result)


def load_issue(client, args, fields="*all"):
    require_cookie(client, args.url)
    key = issue_key_of(args.url)
    try:
        return client.json(f"/rest/api/2/issue/{key}", fields=fields, expand="names")
    except CookieBlocked:
        mark_rejected(client.host)
        out(renew_info(args.url, {**cookie_state(client.host), "state": "rejected"}), EXIT_COOKIE)


def cmd_list(args):
    client = make_client(args)
    issue = load_issue(client, args, fields="summary,attachment")
    items = [{k: v for k, v in a.items() if k != "download"} for a in attachments_of(issue)]
    out({"issue": issue["key"], "title": issue["fields"]["summary"],
         "counts": {"images": sum(a["kind"] == "image" for a in items), "files": sum(a["kind"] == "file" for a in items)},
         "attachments": items})


def cmd_fetch(args):
    client = make_client(args)
    issue = load_issue(client, args)
    key = issue["key"]
    folder = long_path(Path(args.out) / key)
    att_dir = folder / "attachments"

    wanted = {"images": {"image"}, "files": {"file"}, "all": {"image", "file"}, "none": set()}[args.what]
    only = set(args.only or [])
    items = attachments_of(issue)
    downloaded, skipped, saved, used = [], [], {}, set()
    blocked = False
    for a in items:
        if a["kind"] not in wanted or (only and a["name"] not in only):
            continue
        if a["size"] and a["size"] > args.max_mb * 1024 * 1024:
            skipped.append({"name": a["name"], "reason": f"larger than {args.max_mb} MB ({a['size']} bytes)"})
            continue
        if blocked:
            skipped.append({"name": a["name"], "reason": "session cookie rejected"})
            continue
        att_dir.mkdir(parents=True, exist_ok=True)
        fname = safe_name(a["name"])
        if fname in used:  # same file name uploaded twice
            fname = f"{a['id']}_{fname}"
        used.add(fname)
        dest = att_dir / fname
        try:
            client.download(a["download"], dest)
        except CookieBlocked:
            blocked = True
            skipped.append({"name": a["name"], "reason": "session cookie rejected"})
            continue
        except Exception as e:  # noqa: BLE001 - keep going with the rest
            skipped.append({"name": a["name"], "reason": f"error: {e}"})
            continue
        saved[a["name"]] = dest
        downloaded.append({"name": a["name"], "kind": a["kind"], "media_type": a["media_type"],
                           "size": a["size"], "path": show(dest)})
    missing = only - {a["name"] for a in items}
    skipped += [{"name": n, "reason": "no attachment with this name"} for n in sorted(missing)]

    text_path = None
    if args.text:
        folder.mkdir(parents=True, exist_ok=True)
        text_path = folder / "issue.md"
        text_path.write_text(issue_markdown(client, issue, saved, issue.get("names") or {}), encoding="utf-8")

    result = {"issue": key, "title": issue["fields"]["summary"], "folder": show(folder),
              "text": show(text_path) if text_path else None, "downloaded": downloaded, "skipped": skipped}
    if blocked:
        mark_rejected(client.host)
        note("Jira rejected the session cookie: run set-cookie to store a new one (see renew_command).")
        result.update(renew_info(args.url, {**cookie_state(client.host), "state": "rejected"}))
        out(result, EXIT_COOKIE)
    if not os.environ.get("JIRA_COOKIE"):
        update_entry(client.host, last_ok=now().isoformat(timespec="seconds"))
    state = cookie_state(client.host)
    result["cookie"] = state
    if state["state"] == "expiring":
        result["warning"] = f"the session cookie expires on {state['expires']}; renew it soon with set-cookie"
    out(result)


def cmd_set_cookie(args):
    base = args.base or split_base(args.url)[0]
    host = urllib.parse.urlsplit(base).netloc
    if not host:
        out({"error": f"need the Jira URL, got '{args.url}'"}, EXIT_ERROR)
    if not is_interactive():
        out({"error": "set-cookie is interactive: run it in your own terminal, not through an agent",
             "command": f'python "{SCRIPT}" set-cookie "{args.url}"'}, EXIT_ERROR)
    note(COOKIE_HELP)
    try:
        value = normalize_cookie(getpass.getpass("Cookie value (hidden; Enter to cancel): "), args.cookie_name)
    except ValueError as e:
        note(f"Not saved: {e}")
        sys.exit(EXIT_ERROR)
    if not value:
        note("Cancelled, nothing saved.")
        sys.exit(EXIT_ERROR)

    expires = None
    if args.expires:
        expires = parse_expiry(args.expires)
    else:
        while True:
            raw = input("Expiry date (the 'Expires / Max-Age' value or YYYY-MM-DD; Enter for a session cookie): ")
            try:
                expires = parse_expiry(raw)
                break
            except ValueError as e:
                note(f"  {e}")

    verified, user = None, None
    try:
        me = Client(base, build_ssl(args), value).json("/rest/api/2/myself")
        verified, user = True, me.get("displayName") or me.get("name")
    except CookieBlocked:
        verified = False
    except Exception as e:  # noqa: BLE001
        note(f"Could not check the cookie against Jira: {e}")
    if verified is False:
        note("Jira rejected this cookie (not signed in). Check that you copied the whole value.")
        if input("Save it anyway? [y/N]: ").strip().lower() not in ("y", "yes", "s", "si"):
            sys.exit(EXIT_COOKIE)

    protection, stored = protect(value)
    data = load_store()
    stamp = now().isoformat(timespec="seconds")
    data[host] = {"cookie_name": args.cookie_name, "protection": protection, "value": stored, "expires": expires,
                  "saved_at": stamp, "last_ok": stamp if verified else None, "rejected_at": None}
    save_store(data)
    note(f"Saved for {host} in {store_file()}"
         + (f", expires {expires}." if expires else ", session cookie (no expiry date).")
         + (f" Checked against Jira: signed in as {user}." if verified else
            " Not checked against Jira." if verified is None else ""))
    out({"host": host, "saved": True, "expires": expires, "verified": verified, "user": user,
         "store": str(store_file())})


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(description="Jira issue text and attachments through a stored session cookie.")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("url", help="Jira issue URL (or PROJ-123 with --base; the Jira base URL for status / set-cookie)")
    common.add_argument("--base", help="Jira base URL, when it cannot be worked out from the URL")
    common.add_argument("--ca-bundle", help="PEM CA file (corporate proxy); default env JIRA_CA_BUNDLE")
    common.add_argument("--insecure", action="store_true", help="do not verify the TLS certificate")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", parents=[common], help="cookie state and live check")
    sub.add_parser("list", parents=[common], help="list the issue's attachments")
    f = sub.add_parser("fetch", parents=[common], help="write the issue as Markdown and/or download attachments")
    f.add_argument("--what", choices=["images", "files", "all", "none"], default="all",
                   help="images, other attachments, both (all) or none (with --text: text only)")
    f.add_argument("--only", action="append", metavar="NAME", help="download only this attachment (repeatable)")
    f.add_argument("--text", action="store_true", help="also write the issue (fields, description, comments) as issue.md")
    f.add_argument("--max-mb", type=float, default=25, help="skip attachments larger than this (default 25)")
    f.add_argument("-o", "--out", default=os.path.join(tempfile.gettempdir(), "jira-read"),
                   help="output folder; files go to <out>/<ISSUE-KEY>/ (default: system temp)")
    s = sub.add_parser("set-cookie", parents=[common], help="store a new session cookie (interactive)")
    s.add_argument("--expires", help="expiry date (YYYY-MM-DD, DD/MM/YYYY or ISO datetime); asked if omitted")
    s.add_argument("--cookie-name", default=DEFAULT_COOKIE, help=f"name used when only a value is pasted (default {DEFAULT_COOKIE})")
    args = p.parse_args()
    try:
        {"status": cmd_status, "list": cmd_list, "fetch": cmd_fetch, "set-cookie": cmd_set_cookie}[args.cmd](args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        out({"error": str(e)}, EXIT_ERROR)


if __name__ == "__main__":
    main()
