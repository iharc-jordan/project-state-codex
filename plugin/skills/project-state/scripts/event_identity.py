"""Stable identity for a canonical Project State activity event.

The activity log keeps its existing ``id`` field. Event kinds that reserve it
for an entity keep the entity ID and compare this same normalized tuple when
checking for a repeat.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")


def deterministic_event_id(event: str, target: str, fact: Any) -> str:
    """Identify an event by its name, canonical target, and resulting fact."""
    payload = bytearray()
    for part in (event, target, fact):
        encoded = _canonical(part)
        payload.extend(len(encoded).to_bytes(8, "big"))
        payload.extend(encoded)
    return "evt-" + hashlib.sha256(payload).hexdigest()[:20]


def main() -> int:
    """Read a JSON tuple or object from stdin and print the log's id value."""
    value = json.load(sys.stdin)
    if isinstance(value, list) and len(value) == 3:
        event, target, fact = value
        entity_id = None
    elif isinstance(value, dict):
        event, target, fact = (value[key] for key in ("event", "target", "fact"))
        entity_id = value.get("entity_id")
    else:
        raise ValueError("expected [event, target, fact] or an event object")
    print(entity_id or deterministic_event_id(event, target, fact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
