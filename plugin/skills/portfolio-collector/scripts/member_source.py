"""Where the portfolio collector reads a member from.

Decision 2026-09-27-local-mcp-multi-project-and-portfolio, ruling 4: the collector reads members through
the state MCP's tool vocabulary, so one collector serves members on disk and members in the cloud; the
file reader stays as the fallback for bare environments. Three sources, one interface:

    FileSource   a member's project-state/ on this disk, read directly           read_via: files
    McpSource    a member served by an MCP: the local project-state server over    read_via: local-mcp
                 stdio (registry projects within the portfolio's workspace_root),
                 or the cloud server over HTTPS with a bearer token                read_via: cloud

Every source hands back the member's files as text, and collect.py parses them the same way whichever
source read them, so a snapshot does not depend on the transport. Nothing here writes to a member.

Stdlib only (PyYAML comes from collect.py's own requirement).
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import queue
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

import yaml

READ_SET_FILES = ("manifest.yaml", "state.json", "reporting-matrix.yaml", "logs/activity.ndjson", "documents/index.yaml")
READ_SET_DIRS = ("milestones", "risks", "decisions", "people", "harvest/cursors")
PROTOCOL = "2025-06-18"
TIMEOUT_S = 60


class McpError(RuntimeError):
    pass


def parse_yaml(text: str, where: str):
    try:
        return yaml.safe_load(text) if text else None
    except Exception as e:  # malformed
        raise RuntimeError(f"malformed: {where}: {e}") from e


# ── files ────────────────────────────────────────────────────────────────────
class FileSource:
    def __init__(self, root: Path, via: str = "files"):
        self.root, self.via = root, via  # via "cloud": a copy the cloud server materialized for its own collect

    def text(self, rel: str) -> str:
        try:
            return (self.root / rel).read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def listdir(self, d: str) -> list[str]:
        return [f"{d}/{p.name}" for p in sorted((self.root / d).glob("*.yaml"))]

    def activity_text(self, since_iso: str) -> str:
        return self.text("logs/activity.ndjson")

    def as_of(self) -> str | None:
        """When this copy last changed: the newest of its manifest, state and log."""
        ts = [(self.root / rel).stat().st_mtime for rel in ("manifest.yaml", "state.json", "logs/activity.ndjson") if (self.root / rel).exists()]
        return dt.datetime.fromtimestamp(max(ts), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None

    def rev(self) -> str:
        """A revision that changes when the files the snapshot reads change.

        A clean git checkout is identified by its HEAD. Anything else — a dirty tree, a substrate that
        is not its own repo, a fixture inside another repo — gets a content hash over the read set, so
        the unchanged short-circuit never hides an edit behind a stale HEAD.
        """
        h = hashlib.sha1()
        for rel in READ_SET_FILES:
            h.update(self.text(rel).encode())
        for d in READ_SET_DIRS:
            for rel in self.listdir(d):
                h.update(rel.rsplit("/", 1)[1].encode()); h.update(self.text(rel).encode())
        sha = "sha:" + h.hexdigest()[:10]
        try:
            out = subprocess.run(["git", "-C", str(self.root), "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True, timeout=10)
            if out.returncode == 0 and out.stdout.strip():
                dirty = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain", "--", "."],
                                       capture_output=True, text=True, timeout=10).stdout.strip()
                return out.stdout.strip() if not dirty else f"{out.stdout.strip()}+{sha}"
        except Exception:
            pass
        return sha

    def close(self):
        pass


# ── an MCP client: stdio (the local server) or streamable HTTP (the cloud) ───
class McpClient:
    def __init__(self, *, cmd: list[str] | None = None, env: dict | None = None, url: str | None = None, token: str | None = None):
        self.cmd, self.url, self.token = cmd, url, token
        self.proc = None
        self.next_id = 0
        if cmd:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         text=True, encoding="utf-8", env=env, bufsize=1)
            self.lines: queue.Queue = queue.Queue()
            threading.Thread(target=self._pump, daemon=True).start()
        self._request("initialize", {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "portfolio-collector", "version": "1"}})
        self._notify("notifications/initialized")

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _notify(self, method: str):
        msg = {"jsonrpc": "2.0", "method": method}
        if self.proc:
            self.proc.stdin.write(json.dumps(msg) + "\n"); self.proc.stdin.flush()
        else:
            self._post(msg, expect=False)

    def _request(self, method: str, params: dict):
        self.next_id += 1
        msg = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        if self.proc:
            self.proc.stdin.write(json.dumps(msg) + "\n"); self.proc.stdin.flush()
            while True:
                try:
                    line = self.lines.get(timeout=TIMEOUT_S)
                except queue.Empty:
                    raise McpError(f"{method}: no answer from the local server in {TIMEOUT_S}s")
                if line is None:
                    raise McpError(f"{method}: the local server exited")
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("id") == self.next_id:
                    return self._result(method, obj)
        return self._result(method, self._post(msg))

    def _post(self, msg: dict, expect: bool = True):
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode(), method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {})})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                body = r.read().decode("utf-8")
                ctype = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raise McpError(f"{msg.get('method')}: HTTP {e.code}" + (" (sign in again: the token is missing or expired)" if e.code == 401 else ""))
        except urllib.error.URLError as e:
            raise McpError(f"{msg.get('method')}: {e.reason}")
        if not expect or not body.strip():
            return None
        if "text/event-stream" in ctype:  # the answer is the data: line carrying our id
            for line in body.splitlines():
                if line.startswith("data:"):
                    obj = json.loads(line[5:].strip())
                    if obj.get("id") == msg["id"]:
                        return obj
            raise McpError(f"{msg.get('method')}: no answer in the event stream")
        return json.loads(body)

    @staticmethod
    def _result(method: str, obj: dict):
        if obj.get("error"):
            raise McpError(f"{method}: {obj['error'].get('message')}")
        return obj.get("result") or {}

    def call(self, tool: str, args: dict) -> dict:
        r = self._request("tools/call", {"name": tool, "arguments": args})
        if r.get("isError"):
            raise McpError(((r.get("content") or [{}])[0]).get("text") or f"{tool} failed")
        if r.get("structuredContent") is not None:
            return r["structuredContent"]
        return json.loads(((r.get("content") or [{}])[0]).get("text") or "{}")

    def close(self):
        if self.proc:
            try:
                self.proc.stdin.close(); self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()


class McpSource:
    """A member read through get_entity and view_substrate: the same files, served."""

    def __init__(self, client: McpClient, ref: str, via: str):
        self.client, self.ref, self.via = client, ref, via
        self.cache: dict[tuple, dict | None] = {}
        self._paths: list[str] | None = None
        self._as_of: str | None = None

    def _get(self, rel: str, since: str | None = None) -> dict | None:
        key = (rel, since)
        if key not in self.cache:
            try:
                self.cache[key] = self.client.call("get_entity", {"project": self.ref, "path": rel, **({"since": since} if since else {})})
            except McpError as e:
                if "no entity at" not in str(e):
                    raise
                self.cache[key] = None
            self._as_of = self._as_of or (self.cache[key] or {}).get("as_of")
        return self.cache[key]

    def text(self, rel: str) -> str:
        e = self._get(rel)
        if not e:
            return ""
        if e.get("truncated"):
            raise RuntimeError(f"malformed: {self.ref}:{rel}: too large to read through the server")
        return e.get("raw") or ""

    def listdir(self, d: str) -> list[str]:
        if self._paths is None:
            self._paths = [f["path"] for f in self.client.call("view_substrate", {"project": self.ref}).get("files", [])]
        return sorted(p for p in self._paths if p.startswith(d + "/") and "/" not in p[len(d) + 1:] and p.endswith(".yaml"))

    def activity_text(self, since_iso: str) -> str:
        e = self._get("logs/activity.ndjson", since_iso)
        return (e or {}).get("raw") or ""

    def rev(self) -> str:
        """A content hash over the read set, from the sha256 the server keeps for each file."""
        h = hashlib.sha1()
        for rel in READ_SET_FILES:
            # a log's sha256 is the whole file's; asking for no lines keeps the answer small
            e = self._get(rel, "9999-12-31") if rel.endswith(".ndjson") else self._get(rel)
            h.update(((e or {}).get("sha256") or "-").encode())
        for d in READ_SET_DIRS:
            for rel in self.listdir(d):
                h.update(rel.encode()); h.update(((self._get(rel) or {}).get("sha256") or "-").encode())
        return "sha:" + h.hexdigest()[:10]

    def as_of(self) -> str | None:
        """When the server's copy last changed (for a Published mirror: when it was last published)."""
        if self._as_of is None:
            self._get("manifest.yaml")
        return self._as_of

    def close(self):
        pass


# ── finding the servers ──────────────────────────────────────────────────────
def local_server_cmd(script: Path) -> list[str] | None:
    """The local project-state server: $PROJECT_STATE_LOCAL_MCP, else the nearest one above this script — the
    plugin's own (<plugin>/server/, with the skill at <plugin>/skills/portfolio-collector/scripts/) or this
    checkout's source (services/state-mcp/, with its dependencies installed). None when node or the server
    is not there."""
    node = shutil.which("node")
    if not node:
        return None
    env = os.environ.get("PROJECT_STATE_LOCAL_MCP")
    if env:
        return [node, env] if Path(env).exists() else None
    for d in script.resolve().parents:
        if (d / "server" / "state-mcp-local.mjs").exists():
            return [node, str(d / "server" / "state-mcp-local.mjs")]
        src = d / "services" / "state-mcp" / "src" / "local.mjs"
        if src.exists() and (d / "services" / "state-mcp" / "node_modules").exists():
            return [node, str(src)]
    return None


def cloud_folders() -> dict[str, Path] | None:
    """Inside the cloud server's own collect (portfolio_collect, tools-portfolio.mjs): the members the caller
    can see, already materialized as folders — {"org/project": dir} in $PORTFOLIO_CLOUD_FOLDERS. None when the
    collector is not running inside the server; {} when it is and the caller can see no member."""
    raw = os.environ.get("PORTFOLIO_CLOUD_FOLDERS")
    if raw is None:
        return None
    try:
        return {k: Path(v) for k, v in json.loads(raw or "{}").items()}
    except Exception:
        return {}


# ── entitlements (decision 2026-09-27-capability-entitlements; the Node side: services/state-mcp/src/entitlements.mjs)
def _b64url_int(s: str) -> int:
    return int.from_bytes(base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)), "big")


def _canonical(v) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _rsa_sha256_ok(n: int, e: int, msg: bytes, sig: bytes) -> bool:
    """RSASSA-PKCS1-v1_5 with SHA-256, verification only, standard library."""
    k = (n.bit_length() + 7) // 8
    if len(sig) != k:
        return False
    em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big")
    info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(msg).digest()
    return hmac.compare_digest(em, b"\x00\x01" + b"\xff" * (k - len(info) - 3) + b"\x00" + info)


def trusted_keys(script: Path) -> list[dict]:
    """$PROJECT_STATE_ENTITLEMENT_KEYS, else the nearest keys/entitlement-keys.json above this script (the plugin's or
    this checkout's). [] when none: the local check is then not enforced (the rollout rule)."""
    env = os.environ.get("PROJECT_STATE_ENTITLEMENT_KEYS")
    files = [Path(env)] if env else [d / "keys" / "entitlement-keys.json" for d in script.resolve().parents]
    for f in files:
        if f.exists():
            try:
                return [k for k in json.loads(f.read_text(encoding="utf-8")).get("keys") or [] if k.get("kty") == "RSA" and k.get("n") and k.get("e")]
            except Exception:
                return []
    return []


def entitlement_status(capability: str, script: Path, today: str) -> dict:
    """Is `capability` unlocked on this install? {enforced, entitled, reason?} — offline, from the signed files."""
    keys = trusted_keys(script)
    if not keys:
        return {"enforced": False, "entitled": True}
    kids = {k.get("kid") or hashlib.sha256(k["n"].encode()).hexdigest()[:16]: k for k in keys}
    d = Path(os.environ.get("PROJECT_STATE_ENTITLEMENTS_DIR") or Path.home() / ".config" / "project-state" / "entitlements")
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            ent = json.loads(f.read_text(encoding="utf-8"))
            p, sig = ent["payload"], base64.b64decode(ent["signature"])
        except Exception:
            continue
        k = kids.get(p.get("kid"))
        if not k or not _rsa_sha256_ok(_b64url_int(k["n"]), _b64url_int(k["e"]), _canonical(p), sig):
            continue
        if (p.get("expires") or "9999-12-31") >= today and capability in (p.get("capabilities") or []):
            return {"enforced": True, "entitled": True, "org": p.get("org"), "expires": p.get("expires")}
    return {"enforced": True, "entitled": False,
            "reason": f"no valid entitlement on this install unlocks {capability}; activate it through the Project State connector"}


def cloud_endpoint() -> tuple[str | None, str | None]:
    """The cloud server's /mcp URL ($PS_MCP_URL) and a bearer token ($PS_MCP_TOKEN, else
    ~/.config/project-state/mcp-token). The collector never signs in or asks: no token, no cloud read."""
    url = os.environ.get("PS_MCP_URL") or None
    tok = os.environ.get("PS_MCP_TOKEN")
    if not tok:
        f = Path.home() / ".config" / "project-state" / "mcp-token"
        tok = f.read_text(encoding="utf-8").strip() if f.exists() else None
    return url, tok or None


def registry_rows() -> list[dict]:
    """The workspace registry's projects on disk, found the way the kanban and the local server find it."""
    return (read_registry() or {}).get("projects") or []


def registry_cloud_rows() -> list[dict]:
    """The registry's projects whose home is the cloud (scripts/build-registry.py, the `cloud` block)."""
    return [r for r in ((read_registry() or {}).get("cloud") or {}).get("projects") or [] if isinstance(r, dict)]


def read_registry() -> dict | None:
    env = os.environ.get("PROJECT_STATE_REGISTRY")
    if env is not None:
        f = Path(env) if env and env != "off" else None
    else:
        ws = os.environ.get("PS_WORKSPACE_ROOT")
        if not ws:
            try:
                ws = json.loads((Path.home() / ".project-state" / "config.json").read_text(encoding="utf-8")).get("workspaceRoot")
            except Exception:
                ws = None
        f = Path(ws) / "registry.json" if ws else None
    if not f or not f.exists():
        return None
    try:
        reg = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    reg["projects"] = [p for p in (reg.get("projects") or []) if isinstance(p, dict)]
    return reg


def registry_folder(ref: str) -> Path | None:
    """A registry row "org/project" → its project-state folder on disk (stateDir, else the usual names)."""
    org, _, project = ref.partition("/")
    for p in registry_rows():
        if str(p.get("org")) == org and str(p.get("project")) == project and not p.get("archived") and (p.get("stateType") in (None, "project-state")):
            for d in [p.get("stateDir"), "project-state", ".project-state"]:
                if d and (Path(p["path"]) / d / "manifest.yaml").exists():
                    return (Path(p["path"]) / d).resolve()
    return None
