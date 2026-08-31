#!/usr/bin/env python3
"""Reference RSS/Atom poller for tender-harvester (CanadaBuys).

Stateless helper: fetches one feed with conditional headers and prints new/changed
entries as JSON lines. Cursor state stays in the facility's state/tender-intelligence.json — the agent
passes it in and persists what comes back. Stdlib only.

Usage:
  feed_poll.py URL [--etag ETAG] [--modified HTTP_DATE] [--since ISO8601]

Output (stdout):
  {"kind":"feed_meta","status":200,"etag":"…","last_modified":"…"}
  {"kind":"entry","id":"…","title":"…","link":"…","updated":"…","summary":"…"}
Exit codes: 0 ok, 3 not-modified (304), 4 fetch error, 5 parse error.
"""
import json
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

UA = "Atomic47-TenderIntelligence/1.0 (+https://atomic47.co; polite crawler)"
ATOM = "{http://www.w3.org/2005/Atom}"


def parse_when(text):
    if not text:
        return None
    text = text.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main(argv):
    url, etag, modified, since = argv[0], None, None, None
    args = argv[1:]
    while args:
        flag = args.pop(0)
        val = args.pop(0) if args else None
        if flag == "--etag":
            etag = val
        elif flag == "--modified":
            modified = val
        elif flag == "--since":
            since = parse_when(val)

    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/atom+xml, application/rss+xml, application/xml"})
    if etag:
        req.add_header("If-None-Match", etag)
    if modified:
        req.add_header("If-Modified-Since", modified)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            emit({"kind": "feed_meta", "status": resp.status,
                  "etag": resp.headers.get("ETag"),
                  "last_modified": resp.headers.get("Last-Modified")})
    except urllib.error.HTTPError as e:
        if e.code == 304:
            emit({"kind": "feed_meta", "status": 304})
            return 3
        emit({"kind": "error", "status": e.code, "detail": str(e)})
        return 4
    except (urllib.error.URLError, TimeoutError) as e:
        emit({"kind": "error", "detail": str(e)})
        return 4

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        emit({"kind": "error", "detail": f"parse: {e}"})
        return 5

    entries = []
    if root.tag == f"{ATOM}feed":  # Atom
        for e in root.findall(f"{ATOM}entry"):
            link = ""
            for l in e.findall(f"{ATOM}link"):
                if l.get("rel") in (None, "alternate"):
                    link = l.get("href", "")
                    break
            entries.append({
                "id": (e.findtext(f"{ATOM}id") or link or "").strip(),
                "title": (e.findtext(f"{ATOM}title") or "").strip(),
                "link": link,
                "updated": (e.findtext(f"{ATOM}updated") or e.findtext(f"{ATOM}published") or "").strip(),
                "summary": (e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content") or "").strip(),
            })
    else:  # RSS 2.0
        for item in root.iter("item"):
            entries.append({
                "id": (item.findtext("guid") or item.findtext("link") or "").strip(),
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "updated": (item.findtext("pubDate") or "").strip(),
                "summary": (item.findtext("description") or "").strip(),
            })

    for entry in entries:
        when = parse_when(entry["updated"])
        if since and when:
            s = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
            w = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
            if w <= s:
                continue
        emit({"kind": "entry", **entry})
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
