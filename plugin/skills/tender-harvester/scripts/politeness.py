#!/usr/bin/env python3
"""Global per-domain politeness ledger for tender listing connectors.

Spec §19.3: connectors run per facility, but per-domain rate limits must hold
globally — three facilities polling SaskTenders must not triple the load. The
ledger lives ABOVE facilities at ~/.tender-politeness/ledger.json and every
listing request checks in here first. File-locked via atomic rename; stdlib only.

Usage:
  politeness.py check  DOMAIN            -> prints {"allowed": bool, "wait_seconds": int}
  politeness.py record DOMAIN [STATUS]   -> records a request (and backoff on 403/429)
  politeness.py show                     -> dumps the ledger

Domains have a minimum interval (default 3600s). A 403/429 doubles the domain's
interval up to 24h until a clean record resets it.
"""
import json
import os
import sys
import time

LEDGER_DIR = os.path.expanduser("~/.tender-politeness")
LEDGER = os.path.join(LEDGER_DIR, "ledger.json")
DEFAULT_INTERVAL = 3600          # spec: hard minimum one hour between listing polls
MAX_INTERVAL = 86400
DEFAULTS = {
    "sasktenders.ca": 4 * 3600,  # spec-recommended 4h
    "bidsandtenders.ca": 4 * 3600,
    "canadabuys.canada.ca": 3600,
}


def load():
    try:
        with open(LEDGER) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"domains": {}}


def save(data):
    os.makedirs(LEDGER_DIR, exist_ok=True)
    tmp = LEDGER + f".tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, LEDGER)  # atomic on POSIX


def domain_entry(data, domain):
    return data["domains"].setdefault(domain, {
        "min_interval_seconds": DEFAULTS.get(domain, DEFAULT_INTERVAL),
        "last_request_at": 0,
        "request_count": 0,
        "backoff_until": 0,
    })


def check(domain):
    data = load()
    d = domain_entry(data, domain)
    now = time.time()
    wait = 0
    if now < d["backoff_until"]:
        wait = int(d["backoff_until"] - now)
    else:
        due = d["last_request_at"] + d["min_interval_seconds"]
        if now < due:
            wait = int(due - now)
    print(json.dumps({"allowed": wait == 0, "wait_seconds": wait,
                      "min_interval_seconds": d["min_interval_seconds"]}))
    return 0 if wait == 0 else 1


def record(domain, status="200"):
    data = load()
    d = domain_entry(data, domain)
    now = time.time()
    d["last_request_at"] = now
    d["request_count"] += 1
    if status in ("403", "429"):
        d["min_interval_seconds"] = min(MAX_INTERVAL, d["min_interval_seconds"] * 2)
        d["backoff_until"] = now + d["min_interval_seconds"]
    elif status.startswith("2"):
        base = DEFAULTS.get(domain, DEFAULT_INTERVAL)
        if d["min_interval_seconds"] > base and d["backoff_until"] < now:
            d["min_interval_seconds"] = max(base, d["min_interval_seconds"] // 2)
    save(data)
    print(json.dumps({"recorded": True, "domain": domain, "status": status,
                      "min_interval_seconds": d["min_interval_seconds"]}))
    return 0


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "check" and len(argv) >= 2:
        return check(argv[1])
    if cmd == "record" and len(argv) >= 2:
        return record(argv[1], argv[2] if len(argv) > 2 else "200")
    if cmd == "show":
        print(json.dumps(load(), indent=2))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
