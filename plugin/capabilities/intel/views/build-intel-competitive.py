#!/usr/bin/env python3
"""build-intel-competitive — the competitive layer at a glance, as a self-contained HTML report.

    python3 build-intel-competitive.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD]

Reads:
    manifest.yaml                 capabilities.intel.competitive (self, scope, half-lives)
    intel/entities/*.yaml         the registry (self, competitors)
    intel/claims/*.yaml           the atoms — freshness is DERIVED here from the half-life table
    intel/changes/*.yaml          change events (noise omitted)
    intel/battlecards/*.md        projection frontmatter (generated_at) for currency
    state/intel.json              projection hashes (forks are flagged)

Writes ONE file (default <facility>/intel/reports/competitive.html) and nothing else. A lens.
Declared in surfaces.yaml (`reports:`), rendered in place by the app's Intel page; no scripts,
no external resources. Five pictures (docs/INTEL-CI-SPEC.md §9.2): coverage per competitor
(claims stacked fresh / aging / stale, stale hatched, self first), the contested grid, open
unknowns on P0 competitors, battlecard currency, and the last 30 days of change events.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("build-intel-competitive: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DEFAULT_HALF_LIVES = {"pricing": 90, "packaging": 90, "product": 180, "feature": 180, "integration": 180, "positioning": 180, "messaging": 180, "go-to-market": 180, "security": 180,
                      "customer": 270, "partnership": 270, "compliance": 270, "leadership": 365, "funding": 365, "market": 365, "objection": 120, "win-loss": 120, "sales-tactic": 120, "product-gap": 120}
CATEGORIES = list(DEFAULT_HALF_LIVES)
SIG_R = {"material": 8, "notable": 5}


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def yload(p: Path):
    try:
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def to_date(v):
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def load_dir(d: Path):
    out = []
    for p in sorted(d.glob("*.yaml")):
        x = yload(p)
        if isinstance(x, dict):
            x.setdefault("id", p.stem)
            out.append(x)
    return out


def frontmatter(p: Path):
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        return None, None
    if not t.startswith("---"):
        return None, t
    end = t.find("\n---", 3)
    if end < 0:
        return None, t
    try:
        return yaml.safe_load(t[3:end]) or {}, t
    except Exception:
        return None, t


def scalar(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility"); ap.add_argument("--out"); ap.add_argument("--as-of")
    args = ap.parse_args(argv)
    fac = Path(args.facility).resolve()
    today = dt.date.fromisoformat(args.as_of) if args.as_of else dt.datetime.utcnow().date()
    now_s = (today.strftime("%Y-%m-%d 05:30") if args.as_of else dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
    if not (fac / "intel").is_dir():
        print(f"build-intel-competitive: {fac}/intel not found — is the intel capability enabled here?", file=sys.stderr); return 1
    manifest = yload(fac / "manifest.yaml") or {}
    cap = (manifest.get("capabilities") or {}).get("intel") or {}
    comp = cap.get("competitive") or {}
    half = dict(DEFAULT_HALF_LIVES); half.update(comp.get("half_lives_days") or {})
    name = ((manifest.get("project") or {}).get("name")) or fac.parent.name
    ents = {e["id"]: e for e in load_dir(fac / "intel" / "entities")}
    claims = load_dir(fac / "intel" / "claims")
    changes = load_dir(fac / "intel" / "changes")
    try:
        state = json.loads((fac / "state" / "intel.json").read_text())
    except Exception:
        state = {}
    self_id = scalar(comp.get("self_entity"))
    scope = [scalar(x) for x in (comp.get("competitors") or [])] or [i for i, e in ents.items() if e.get("type") == "competitor"]
    subjects = ([self_id] if self_id and self_id in ents else []) + [i for i in scope if i in ents and i != self_id]

    # ── derive freshness per claim ───────────────────────────────────────────
    def freshness(c):
        d = to_date(c.get("source_date")) or to_date(c.get("retrieved_at")) or to_date(c.get("created"))
        if not d:
            return "stale"
        hl = int(half.get(str(c.get("category")), 180)); age = (today - d).days
        return "fresh" if age < hl else ("aging" if age < 2 * hl else "stale")
    for c in claims:
        c["_fresh"] = freshness(c); c["_subject"] = ((c.get("subject") or {}).get("entity") if isinstance(c.get("subject"), dict) else c.get("subject"))
    superseded = {c.get("supersedes") for c in claims if c.get("supersedes")}
    by_id = {c["id"]: c for c in claims}
    current = [c for c in claims if c["id"] not in superseded]

    # ── 1. coverage ──────────────────────────────────────────────────────────
    rows = []
    max_n = 1
    for sid in subjects:
        cs = [c for c in current if c["_subject"] == sid]
        n = {k: sum(1 for c in cs if c["_fresh"] == k) for k in ("fresh", "aging", "stale")}
        max_n = max(max_n, len(cs)); rows.append((sid, n, len(cs)))
    bw = 600; x0 = 220; rh = 34; h = 30 + rh * max(1, len(rows)) + 30
    svg = [f'<svg viewBox="0 0 960 {h}" role="img" aria-label="Claim coverage per competitor">',
           '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--muted)" stroke-width="2"/></pattern></defs>']
    for k in range(0, max_n + 1, max(1, max_n // 5 or 1)):
        xx = x0 + k * bw / max_n
        svg.append(f'<line class="grid" x1="{xx:.0f}" y1="18" x2="{xx:.0f}" y2="{h-24}"/><text x="{xx:.0f}" y="{h-8}" class="mono" text-anchor="middle">{k}</text>')
    for i, (sid, n, tot) in enumerate(rows):
        y = 30 + i * rh; e = ents[sid]; lab = ("us · " if sid == self_id else "") + str(e.get("name") or sid)[:26]
        svg.append(f'<text x="{x0-10}" y="{y+16}" text-anchor="end" class="lbl">{esc(lab)}</text><text x="{x0-10}" y="{y+27}" text-anchor="end" class="tiny">{esc(e.get("priority"))} · {tot} current claim(s)</text>')
        xx = x0
        for k, col in (("fresh", "var(--accent)"), ("aging", "var(--accent-mid)"), ("stale", "url(#hatch)")):
            w = n[k] * bw / max_n
            if w > 0:
                svg.append(f'<rect x="{xx:.1f}" y="{y+4}" width="{max(w-2,1):.1f}" height="20" rx="3" fill="{col}"><title>{esc(lab)} · {n[k]} {k}</title></rect>')
                if w > 18:
                    svg.append(f'<text x="{xx+w/2:.1f}" y="{y+18}" text-anchor="middle" class="onbar">{n[k]}</text>')
                xx += w
        if tot == 0:
            svg.append(f'<text x="{x0+6}" y="{y+18}" class="mut">no claims — nothing is evidenced</text>')
    svg.append("</svg>")
    coverage_svg = "".join(svg)
    legend = '<div class="legend"><span><i style="background:var(--accent)"></i>fresh · under the half-life</span><span><i style="background:var(--accent-mid)"></i>aging · up to twice it</span><span><i class="hatchbox"></i>stale · beyond, marked wherever cited</span></div>'

    # ── 2. contested grid ────────────────────────────────────────────────────
    open_conf = defaultdict(list)  # (subject, category) → [(a, b)]
    seen = set()
    for c in current:
        for other in c.get("conflicts_with") or []:
            o = by_id.get(other)
            if not o or o["id"] in superseded:
                continue
            key = tuple(sorted((c["id"], o["id"])))
            if key in seen:
                continue
            seen.add(key); open_conf[(c["_subject"], str(c.get("category")))].append((c, o))
    cats_used = sorted({str(c.get("category")) for c in current if c["_subject"] in subjects}, key=lambda k: CATEGORIES.index(k) if k in CATEGORIES else 99)
    cw = 36; gx0 = 200; gh = 30 + 26 * max(1, len(subjects)) + 90
    g = [f'<svg viewBox="0 0 {gx0 + cw*max(1,len(cats_used)) + 20} {gh}" role="img" aria-label="Contested categories">']
    for j, cat in enumerate(cats_used):
        g.append(f'<text transform="translate({gx0 + j*cw + cw/2:.0f},{gh-70}) rotate(45)" class="tiny">{esc(cat)}</text>')
    for i, sid in enumerate(subjects):
        y = 30 + i * 26
        g.append(f'<text x="{gx0-8}" y="{y+16}" text-anchor="end" class="lbl">{esc(str(ents[sid].get("name") or sid)[:24])}</text>')
        for j, cat in enumerate(cats_used):
            x = gx0 + j * cw
            has = [c for c in current if c["_subject"] == sid and str(c.get("category")) == cat]
            pairs = open_conf.get((sid, cat), [])
            if pairs:
                a, b = pairs[0]
                g.append(f'<rect x="{x+3}" y="{y+3}" width="{cw-6}" height="20" rx="3" fill="var(--warn)"><title>contested · {esc(a["id"])} ({esc(a.get("epistemic_status"))}, {esc(a.get("source_date") or a.get("retrieved_at"))}) vs {esc(b["id"])} ({esc(b.get("epistemic_status"))}, {esc(b.get("source_date") or b.get("retrieved_at"))})</title></rect>'
                         f'<text x="{x+cw/2:.0f}" y="{y+17}" text-anchor="middle" class="onbar">{len(pairs)}</text>')
            elif has:
                g.append(f'<rect x="{x+3}" y="{y+3}" width="{cw-6}" height="20" rx="3" fill="var(--line)"><title>{len(has)} claim(s), none contested</title></rect>')
            else:
                g.append(f'<rect x="{x+3}" y="{y+3}" width="{cw-6}" height="20" rx="3" fill="none" stroke="var(--line)" stroke-dasharray="2 2"><title>no claims</title></rect>')
    g.append("</svg>")
    contested_svg = "".join(g)
    n_conf = sum(len(v) for v in open_conf.values())
    conf_rows = "".join(f'<tr><td class="lbl">{esc(ents.get(s, {}).get("name") or s)}</td><td>{esc(cat)}</td>' + "".join(f'<td class="tiny"><b>{esc(a["id"])}</b> {esc(a.get("epistemic_status"))} · {esc(a.get("source_date") or a.get("retrieved_at"))}: {esc((a.get("statement") or "")[:90])}<br><b>{esc(b["id"])}</b> {esc(b.get("epistemic_status"))} · {esc(b.get("source_date") or b.get("retrieved_at"))}: {esc((b.get("statement") or "")[:90])}</td>' for a, b in pairs) + "</tr>" for (s, cat), pairs in sorted(open_conf.items()))

    # ── 3. unknowns on P0 competitors ────────────────────────────────────────
    unk = [c for c in current if c.get("epistemic_status") == "unknown" and c["_subject"] in subjects and c["_subject"] != self_id and str(ents[c["_subject"]].get("priority")) == "P0"]
    def age(c):
        d = to_date(c.get("retrieved_at")) or to_date(c.get("created")); return (today - d).days if d else 0
    unk.sort(key=age, reverse=True)
    unk_rows = "".join(f'<tr><td class="lbl">{esc(ents[c["_subject"]].get("name"))}</td><td>{esc(c.get("category"))}</td><td>{esc(c.get("statement"))}</td><td class="num">{age(c)} d</td><td class="tiny">{"past half-life — re-search" if age(c) > half.get(str(c.get("category")),180) else "open"} · {esc(c["id"])}</td></tr>' for c in unk) or '<tr><td colspan="5" class="mut">No open unknowns on P0 competitors.</td></tr>'

    # ── 4. battlecard currency ───────────────────────────────────────────────
    proj = (state.get("projections") or {})
    cards = []
    for p in sorted((fac / "intel" / "battlecards").glob("*.md")):
        fm, text = frontmatter(p)
        if not fm:
            continue
        sid = fm.get("subject"); gen = to_date(fm.get("generated_at"))
        newer = [c for c in current if c["_subject"] == sid and c.get("material") and to_date(c.get("created")) and gen and to_date(c.get("created")) > gen]
        rel = "intel/battlecards/" + p.name
        rec = proj.get(rel) or {}
        forked = bool(rec.get("sha256")) and hashlib.sha256(text.encode("utf-8")).hexdigest() != rec.get("sha256")
        h = (fm.get("health") or {})
        cards.append((p.name, sid, gen, len(newer), forked, h.get("stale_claims_used", "—"), h.get("unsourced_lines", "—"), (fm.get("audience") or {}).get("id")))
    card_rows = "".join(
        f'<tr><td class="lbl">{esc(ents.get(sid, {}).get("name") or sid)}{(" · " + esc(aud)) if aud else ""}</td><td class="mono">{gen or "?"}</td>'
        f'<td>{("<span class=badge-warn>behind by " + str(n) + " material claim(s)</span>") if n else "<span class=badge-ok>current</span>"}{" <span class=badge-crit>fork — edited after generation</span>" if fk else ""}</td>'
        f'<td class="num">{esc(st)}</td><td class="num">{esc(us)}</td></tr>'
        for (fn, sid, gen, n, fk, st, us, aud) in cards) or '<tr><td colspan="5" class="mut">No battlecard yet — run intel-battlecard on a competitor once its claims exist.</td></tr>'

    # ── 5. changes, 30 days ──────────────────────────────────────────────────
    sx0, sx1 = 60, 936; spx = (sx1 - sx0) / 30
    recent = [x for x in changes if x.get("significance") in SIG_R and to_date(x.get("detected_at")) and 0 <= (today - to_date(x.get("detected_at"))).days <= 30]
    ss = ['<svg viewBox="0 0 960 130" role="img" aria-label="Change events over the last 30 days">']
    for k in (0, 7, 14, 21, 30):
        d = today - dt.timedelta(days=30 - k); xx = sx0 + k * spx
        ss.append(f'<line class="grid" x1="{xx:.0f}" y1="24" x2="{xx:.0f}" y2="100"/><text x="{xx:.0f}" y="118" class="mono" text-anchor="middle">{d.strftime("%b %-d")}</text>')
    ss.append(f'<line class="today" x1="{sx1}" y1="24" x2="{sx1}" y2="100"/>')
    lanes = {"material": 48, "notable": 80}
    for k, yy in lanes.items():
        ss.append(f'<text x="8" y="{yy+4}" class="mut">{k}</text><line class="grid" x1="{sx0}" y1="{yy}" x2="{sx1}" y2="{yy}"/>')
    placed = defaultdict(int)
    for x in sorted(recent, key=lambda x: str(x.get("detected_at"))):
        d = to_date(x.get("detected_at")); sig = x["significance"]; yy = lanes[sig]
        xx = sx0 + (30 - (today - d).days) * spx; key = (round(xx / 12), sig); dy = placed[key] * 8; placed[key] += 1
        col = "var(--crit)" if sig == "material" else "var(--accent)"
        ss.append(f'<circle cx="{xx:.0f}" cy="{yy-dy}" r="{SIG_R[sig]}" fill="{col}"><title>{esc(x["id"])} · {esc(ents.get(x.get("subject"), {}).get("name") or x.get("subject"))} · {esc(x.get("change_type"))} · {esc(x.get("detected_at"))} · {esc(x.get("recommended_action"))}</title></circle>')
    ss.append("</svg>")
    changes_svg = "".join(ss)
    change_rows = "".join(f'<tr><td class="mono">{esc(x.get("detected_at"))}</td><td class="lbl">{esc(ents.get(x.get("subject"), {}).get("name") or x.get("subject"))}</td><td>{esc(x.get("change_type"))}</td><td>{esc(x.get("significance"))}</td><td class="tiny">{" → ".join(esc(", ".join(x.get(k) or [])) for k in ("before", "after"))}</td><td class="tiny">{esc(x.get("recommended_action"))}</td></tr>' for x in sorted(recent, key=lambda x: str(x.get("detected_at")), reverse=True))
    noise_n = sum(1 for x in changes if x.get("significance") == "noise")

    n_cur = len([c for c in current if c["_subject"] in subjects]); n_fresh = sum(1 for c in current if c["_subject"] in subjects and c["_fresh"] == "fresh")
    n_stale_mat = sum(1 for c in current if c["_subject"] in subjects and c.get("material") and c["_fresh"] == "stale")
    counts = [(n_cur, "current claims"), (n_fresh, "fresh"), (n_stale_mat, "material & stale"), (n_conf, "open conflicts"), (len(unk), "P0 unknowns"), (sum(1 for c in cards if c[3]), "battlecards behind")]
    counts_html = '<div class="counts">' + "".join(f'<div class="c"><b>{v}</b><span>{k}</span></div>' for v, k in counts) + "</div>"
    self_note = (f'Self entity <b>{esc(ents[self_id].get("name"))}</b> ({esc(self_id)}) with {sum(1 for c in current if c["_subject"] == self_id)} claim(s).' if self_id in ents else '<b>No self entity declared</b> — nothing about us is provable; battlecards cannot pass the three-part test. Run intel-onboarding competitive.')
    page = PAGE.format(title=esc(name), now=esc(now_s), self_note=self_note, coverage=coverage_svg, legend=legend, counts=counts_html, contested=contested_svg, conf_rows=conf_rows or "", n_conf=n_conf,
                       unk_rows=unk_rows, card_rows=card_rows, changes=changes_svg, change_rows=change_rows or '<tr><td colspan="6" class="mut">No material or notable change in the last 30 days.</td></tr>', noise=noise_n, nclaims=len(claims), nsup=len(superseded))
    out = Path(args.out) if args.out else fac / "intel" / "reports" / "competitive.html"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(page, encoding="utf-8")
    print(f"intel-competitive → {out}\n  as of {today} · {n_cur} current claims ({n_fresh} fresh, {n_stale_mat} material stale) · {n_conf} open conflict(s) · {len(unk)} P0 unknown(s) · {len(cards)} battlecard(s), {sum(1 for c in cards if c[3])} behind · {len(recent)} change(s) in 30 d")
    return 0


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — competitive at a glance</title>
<style>
:root{{--ground:#F5F7F4;--paper:#FFFFFF;--ink:#1B2230;--muted:#6B7480;--faint:#A9B1B8;--line:#DDE3DE;--rule:#B9C2BC;--accent:#1F5F6B;--accent-mid:#7FB0B8;--accent-soft:#E3EEF0;--crit:#d03b3b;--crit-soft:#F6E0E0;--warn:#c98500;--warn-soft:#F7ECD6;--ok:#2E7D4F;--ok-soft:#E1F0E6;
--mono:ui-monospace,Menlo,monospace;--sans:system-ui,-apple-system,"Segoe UI",sans-serif;--serif:Georgia,"Times New Roman",serif}}
@media (prefers-color-scheme:dark){{:root{{--ground:#12181E;--paper:#1A222A;--ink:#E7EBEE;--muted:#A3ACB4;--faint:#5B6670;--line:#2C3640;--rule:#465262;--accent:#6FBFC9;--accent-mid:#3E7A84;--accent-soft:#1E3238;--crit:#e66767;--crit-soft:#3E2222;--warn:#e0b463;--warn-soft:#3A2F17;--ok:#6CC58F;--ok-soft:#1D3327}}}}
*{{box-sizing:border-box}}body{{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 20px 64px}}h1{{font-family:var(--serif);font-weight:600;font-size:2rem;line-height:1.1;margin:0}}
.eyebrow{{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}.lede{{color:var(--muted);max-width:66ch;margin:8px 0 28px}}
.focus{{border-left:3px solid var(--accent);background:var(--accent-soft);padding:10px 14px;border-radius:0 6px 6px 0;margin:0 0 28px;font-size:.95rem}}
section{{margin-bottom:52px}}section>header .q{{font-family:var(--serif);font-size:1.5rem;font-weight:600}}section>header .w{{color:var(--muted);font-size:.92rem;margin-top:2px}}
.fig{{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px 20px 14px;margin-top:14px}}svg{{width:100%;height:auto;display:block;font-family:var(--sans)}}
svg text{{fill:var(--ink);font-size:12.5px}}svg .mut{{fill:var(--muted);font-size:11px}}svg .tiny{{fill:var(--muted);font-size:10px}}svg .mono{{font-family:var(--mono);font-size:10.5px;fill:var(--muted)}}
svg .lbl{{font-weight:600;font-size:12.5px}}svg .onbar{{fill:#fff;font-size:11px;font-weight:600}}svg .grid{{stroke:var(--line);stroke-width:1}}svg .today{{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.8rem;color:var(--muted);margin-top:10px}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:5px;vertical-align:-2px}}.legend i.hatchbox{{background:repeating-linear-gradient(45deg,var(--muted) 0 2px,transparent 2px 6px)}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}}.counts .c{{border:1px solid var(--line);border-radius:8px;background:var(--paper);padding:10px 14px;min-width:96px}}.counts .c b{{display:block;font-family:var(--serif);font-size:1.6rem;font-weight:600;line-height:1}}.counts .c span{{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.tbl{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-family:var(--mono);font-size:.7rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500}}
td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}td.lbl,.lbl{{font-weight:600}}.mut{{color:var(--muted)}}.tiny{{font-size:.78rem;color:var(--muted)}}td.mono{{font-family:var(--mono);font-size:.8rem}}
.badge-ok,.badge-warn,.badge-crit{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.75rem;font-weight:600}}.badge-ok{{background:var(--ok-soft);color:var(--ok)}}.badge-warn{{background:var(--warn-soft);color:var(--warn)}}.badge-crit{{background:var(--crit-soft);color:var(--crit)}}
.cites{{font-family:var(--mono);font-size:.74rem;color:var(--muted);margin:10px 0 0;line-height:1.7}}.cites b{{color:var(--accent);font-weight:500}}
</style></head><body><div class="wrap">
  <div class="eyebrow">intel capability · competitive layer · generated by build-intel-competitive · {now}</div>
  <h1>{title} — competitive at a glance</h1>
  <p class="lede">Drawn from intel/claims (append-only), intel/changes, the battlecards' own frontmatter and the half-life table in the manifest. Freshness is derived here, never stored. Every mark carries its claim ids.</p>
  <div class="focus">{self_note}</div>

  <section><header><div class="q">How much of each competitor is actually evidenced?</div><div class="w">Current claims per subject, stacked by derived freshness · the honesty budget, drawn</div></header>
  <div class="fig">{coverage}{legend}</div>{counts}</section>

  <section><header><div class="q">Where do the sources disagree?</div><div class="w">Category × competitor · a filled cell is an open conflict, shown side by side and dated, never resolved silently</div></header>
  <div class="fig">{contested}<div class="tbl"><table><thead><tr><th>Subject</th><th>Category</th><th>Contested claims</th></tr></thead><tbody>{conf_rows}</tbody></table></div><p class="cites">{n_conf} open conflict(s). A new claim with <b>supersedes:</b> closes one; nothing else does.</p></div></section>

  <section><header><div class="q">What do we not know about the competitors that matter most?</div><div class="w">Open unknown claims on P0 competitors, oldest first · "no evidence found" is a record, not a gap</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Competitor</th><th>Category</th><th>Unknown</th><th class="num">Age</th><th>Status</th></tr></thead><tbody>{unk_rows}</tbody></table></div></div></section>

  <section><header><div class="q">Are the battlecards current with the evidence?</div><div class="w">Each card's generation date against the newest material claim on its subject · a hand-edited card is a fork</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Battlecard</th><th>Generated</th><th>Currency</th><th class="num">Stale used</th><th class="num">Unsourced</th></tr></thead><tbody>{card_rows}</tbody></table></div></div></section>

  <section><header><div class="q">What changed in the last 30 days?</div><div class="w">Change events as claim deltas · material and notable only · {noise} noise event(s) suppressed</div></header>
  <div class="fig">{changes}<div class="tbl"><table><thead><tr><th>Detected</th><th>Subject</th><th>Type</th><th>Significance</th><th>Before → after</th><th>Action</th></tr></thead><tbody>{change_rows}</tbody></table></div>
  <p class="cites">{nclaims} claims on file, {nsup} superseded. Claims are never edited; a correction is a new claim pointing at the old one.</p></div></section>
</div></body></html>
"""

if __name__ == "__main__":
    sys.exit(main())
