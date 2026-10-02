#!/usr/bin/env python3
"""Open MindMap Studio with a mindmap-vibe JSON loaded via #vibe= URL hash."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

STUDIO = Path.home() / "Desktop" / "simple-minds.html"
INBOX = Path.home() / "Desktop" / "mindmap-inbox" / "latest.vibe.json"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def main() -> int:
    path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else INBOX
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    if not STUDIO.is_file():
        print(f"MindMap Studio not found: {STUDIO}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    url = STUDIO.resolve().as_uri() + "#vibe=" + b64url(payload)
    subprocess.run(["open", url], check=False)
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
