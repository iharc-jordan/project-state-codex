#!/usr/bin/env python3
"""build-research-evidence — the evidence behind every answer, as a self-contained HTML report.

    python3 build-research-evidence.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD] [--artifact]

The depth the At a glance report deliberately leaves out (spec §10.3). Four pictures:

  1. What each finding rests on   the register — tier, confidence, epistemic status, freshness,
                                  status, independence, and every flag a reviewer would raise
  2. Where the evidence came from registered documents and web references folded by host,
                                  each with the findings it fed
  3. What stands against it       every challenge, its argument, and how it was ruled
  4. What it adds up to           longlist rankings and the deliverables each mandate shipped

Writes ONE file (default <facility>/research/reports/evidence.html). Read-only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _research import Facility, esc, host, is_fixture, page  # noqa: E402

FRESH_CHIP = {"fresh": "ok", "aging": "warn", "stale": "crit", "undated": ""}
STATUS_CHIP = {"established": "ok", "provisional": "warn", "withdrawn": "", "superseded": ""}
TIER_CHIP = {"primary": "acc", "secondary": "", "tertiary": "warn", "speculative": "crit"}
SEV_CHIP = {"blocking": "crit", "material": "warn", "minor": ""}
RULE_CHIP = {"open": "crit", "accepted": "ok", "rejected": "", "resolved": "ok"}

CSS = """
.mhead{font-family:var(--serif);font-size:1.05rem;font-weight:600;margin:18px 0 6px}.mhead:first-child{margin-top:0}
.claim{max-width:46ch}.flags{display:flex;flex-wrap:wrap;gap:4px}.sup{color:var(--muted);text-decoration:line-through}
.ex{font-family:var(--serif);font-style:italic;color:var(--muted);font-size:.84rem;margin-top:3px}
.host{font-weight:600}.fed{font-family:var(--mono);font-size:.74rem;color:var(--muted)}
.arg{max-width:60ch}.res{margin-top:4px;font-size:.84rem;color:var(--muted)}.res b{color:var(--ink);font-weight:600}
.score{font-family:var(--mono);font-variant-numeric:tabular-nums}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility")
    ap.add_argument("--out")
    ap.add_argument("--as-of")
    ap.add_argument("--artifact", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    if not (fac / "research").is_dir():
        print(f"build-research-evidence: {fac}/research not found", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    now_s = today.strftime("%Y-%m-%d 06:00") if a.as_of else dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    fx = Facility(fac, today)
    mandates = [m for m in fx.mandates if fx.findings_for(m["id"])]

    # ── 1. the register ──────────────────────────────────────────────────────
    reg = []
    for m in mandates:
        rows = []
        for f in sorted(fx.findings_for(m["id"]), key=lambda f: f["id"]):
            sup = fx.superseded(f)
            status = "superseded" if sup else f.get("status")
            fr = fx.freshness(f)
            flags = []
            if f.get("supersedes"):
                flags.append(f'<span class="chip">replaces {esc(f["supersedes"])}</span>')
            if sup:
                flags.append(f'<span class="chip">replaced by {esc(fx.superseded_by[f["id"]])}</span>')
            if fx.not_triangulated(f):
                flags.append('<span class="chip crit" title="Several references, one independent origin — reads as corroborated and is not">not triangulated</span>')
            if int(f.get("independent_sources") or 0) < 2 and f.get("confidence") == "medium" and not fx.not_triangulated(f):
                flags.append('<span class="chip warn" title="Medium confidence is licensed by triangulation; there is one source">single source</span>')
            for c in fx.challenged(f["id"]):
                flags.append(f'<span class="chip {RULE_CHIP.get(c.get("status"), "")}">{esc(c["id"])} {esc(c.get("status"))}</span>')
            if f.get("epistemic_status") == "unknown":
                flags.append('<span class="chip acc" title="A search that failed, kept so it is not re-run">recorded absence</span>')
            ex = next((e.get("excerpt") for e in (f.get("evidence") or []) if isinstance(e, dict) and e.get("excerpt")), None)
            rows.append(
                f'<tr><td class="id">{esc(f["id"])}<div class="mut small">{esc(", ".join(f.get("answers") or []))}</div></td>'
                f'<td class="claim"><span class="{"sup" if sup else ""}">{esc(f.get("claim"))}</span>'
                + (f'<div class="ex">“{esc(ex)}”</div>' if ex else "") + "</td>"
                f'<td><span class="chip {TIER_CHIP.get(f.get("source_tier"), "")}">{esc(f.get("source_tier"))}</span></td>'
                f'<td class="small">{esc(f.get("confidence"))}<div class="mut">{esc(f.get("epistemic_status"))}</div></td>'
                f'<td><span class="chip {FRESH_CHIP.get(fr, "")}">{esc(fr)}</span><div class="mut small">{esc(f.get("category"))}</div></td>'
                f'<td><span class="chip {STATUS_CHIP.get(status, "")}">{esc(status)}</span></td>'
                f'<td class="num">{esc(f.get("independent_sources"))}</td>'
                f'<td><div class="flags">{"".join(flags)}</div></td></tr>')
        reg.append(f'<div class="mhead">{esc(m["id"])} · {esc(m.get("headline"))}</div>'
                   '<div class="tbl"><table><thead><tr><th>Finding</th><th>Claim</th><th>Tier</th><th>Conf.</th><th>Fresh</th>'
                   '<th>Status</th><th class="num">Indep.</th><th>Flags</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")
    register_html = "".join(reg) or '<p class="mut">No findings on file.</p>'

    # ── 2. where the evidence came from ──────────────────────────────────────
    docs = defaultdict(set)
    hosts = defaultdict(lambda: defaultdict(set))
    for f in fx.findings:
        for e in f.get("evidence") or []:
            if not isinstance(e, dict):
                continue
            r = str(e.get("ref") or "")
            if r.startswith("documents/"):
                docs[r].add(f["id"])
            elif r.startswith("http"):
                hosts[host(r)][r].add(f["id"])
    doc_rows = "".join(f'<tr><td class="small">{esc(d)}</td><td class="fed">{esc(", ".join(sorted(ids)))}</td></tr>' for d, ids in sorted(docs.items()))
    host_rows = "".join(
        f'<tr><td class="host">{esc(h)}</td><td class="num">{len(urls)}</td><td class="num">{len(set().union(*urls.values()))}</td>'
        f'<td class="small">' + "<br>".join(f'<a href="{esc(u)}">{esc(u)}</a> <span class="fed">→ {esc(", ".join(sorted(ids)))}</span>' for u, ids in sorted(urls.items())) + "</td></tr>"
        for h, urls in sorted(hosts.items(), key=lambda kv: -len(set().union(*kv[1].values()))))
    sources_html = (
        ('<div class="mhead">Registered documents</div><div class="tbl"><table><thead><tr><th>Document</th><th>Fed</th></tr></thead>'
         f'<tbody>{doc_rows}</tbody></table></div>' if docs else "")
        + '<div class="mhead">The web, folded by host</div><div class="tbl"><table><thead><tr><th>Host</th><th class="num">Pages</th>'
        f'<th class="num">Findings</th><th>Pages and what they fed</th></tr></thead><tbody>{host_rows}</tbody></table></div>')

    # ── 3. what stands against it ────────────────────────────────────────────
    ch_rows = "".join(
        f'<tr><td class="id">{esc(c["id"])}<div class="mut small">{esc(c.get("mandate_id"))}</div></td>'
        f'<td><span class="chip {SEV_CHIP.get(c.get("severity"), "")}">{esc(c.get("severity"))}</span><div class="mut small">{esc(c.get("kind"))}</div></td>'
        f'<td class="id">{esc(c.get("finding_id"))}</td>'
        f'<td class="arg">{esc(c.get("argument"))}'
        + (f'<div class="res"><b>Ruling.</b> {esc(c.get("resolution"))}</div>' if c.get("resolution") else "") + "</td>"
        f'<td><span class="chip {RULE_CHIP.get(c.get("status"), "")}">{esc(c.get("status"))}</span></td></tr>'
        for c in sorted(fx.challenges, key=lambda c: ({"open": 0}.get(c.get("status"), 1), {"blocking": 0, "material": 1}.get(c.get("severity"), 2), c["id"])))
    challenges_html = ('<div class="tbl"><table><thead><tr><th>Challenge</th><th>Severity</th><th>Against</th><th>Argument</th><th>Status</th></tr></thead>'
                       f'<tbody>{ch_rows}</tbody></table></div>') if ch_rows else '<p class="mut">No challenges on file.</p>'

    # ── 4. what it adds up to ────────────────────────────────────────────────
    parts = []
    for m in fx.mandates:
        cands = [c for c in fx.candidates if c.get("mandate_id") == m["id"]]
        if not cands:
            continue
        crits = sorted({s.get("criterion") for c in cands for s in (c.get("scores") or [])})
        ranked = sorted(cands, key=lambda c: (c.get("status") == "excluded", -(c.get("total") or -1)))
        rows = "".join(
            f'<tr><td class="num">{i + 1 if c.get("total") is not None and c.get("status") != "excluded" else "—"}</td>'
            f'<td><b>{esc(c.get("name"))}</b> <span class="id">{esc(c["id"])}</span></td>'
            f'<td class="num score">{esc(c.get("total") if c.get("total") is not None else "—")}</td>'
            + "".join(f'<td class="num score">{esc(next((s.get("score") for s in (c.get("scores") or []) if s.get("criterion") == k), "—"))}</td>' for k in crits)
            + f'<td><span class="chip {"ok" if c.get("status") == "shortlisted" else ""}">{esc(c.get("status"))}</span></td></tr>'
            for i, c in enumerate(ranked))
        _, thr, verdict = fx.gate(m)
        blk = fx.open_blocking(m["id"])
        held = f' <span class="chip crit">held: {len(blk)} blocking challenge</span>' if blk else ""
        parts.append(f'<div class="mhead">{esc(m["id"])} · the longlist as it stands{held}</div>'
                     '<div class="tbl"><table><thead><tr><th class="num">#</th><th>Candidate</th><th class="num">Total</th>'
                     + "".join(f'<th class="num">{esc(k)}</th>' for k in crits) + f'<th>Status</th></tr></thead><tbody>{rows}</tbody></table></div>')
    shipped = "".join(f'<tr><td class="small">research/reports/{esc(r)}</td><td class="id">{esc(r[:9])}</td></tr>' for r in fx.reports)
    parts.append('<div class="mhead">Deliverables shipped</div>' + (
        f'<div class="tbl"><table><thead><tr><th>File</th><th>Mandate</th></tr></thead><tbody>{shipped}</tbody></table></div>'
        if shipped else '<p class="mut">Nothing shipped yet. A mandate composes only once its gate passes and no blocking challenge is open.</p>'))
    adds_html = "".join(parts)

    fixture = '<span class="fixture">fixture · every fact invented</span>' if is_fixture(fx) else ""
    body = f"""
  <div class="eyebrow">research capability · generated by build-research-evidence · {esc(now_s)}</div>
  <h1>{esc(fx.name)} — the evidence{fixture}</h1>
  <p class="lede">Every finding with what it rests on, every source with what it fed, every objection with how it was ruled. Superseded findings stay on the record, struck through, beside the finding that replaced them.</p>

  <section><header><div class="q">What does each finding rest on?</div>
  <div class="w">Tier and confidence are separate axes; epistemic status says what kind of knowing it is. Freshness is derived from the half-life of the finding's category. Only established findings count toward a gate.</div></header>
  <div class="fig">{register_html}</div></section>

  <section><header><div class="q">Where did the evidence come from?</div>
  <div class="w">Documents registered through the house inbox, and the web folded by host. A host that feeds many findings is a single point of failure worth knowing about.</div></header>
  <div class="fig">{sources_html}</div></section>

  <section><header><div class="q">What stands against it?</div>
  <div class="w">Objections a hostile reviewer would raise, filed before anything ships. Only a person rules on one; a rejected challenge stays on the record with its reason.</div></header>
  <div class="fig">{challenges_html}</div></section>

  <section><header><div class="q">What does it add up to?</div>
  <div class="w">Longlist rankings as they stand, and the deliverables each mandate has shipped.</div></header>
  <div class="fig">{adds_html}</div></section>
"""
    out = Path(a.out) if a.out else fac / "research" / "reports" / "evidence.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(("Research Evidence Register" if a.artifact else f"{fx.name} — the evidence"), body, CSS, a.artifact), encoding="utf-8")
    print(f"research-evidence → {out}\n  {len(fx.findings)} findings · {len(docs)} documents · {len(hosts)} hosts · {len(fx.challenges)} challenges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
