#!/usr/bin/env python3
"""build-research-library — the research capability's Library: what the research has concluded, as studies and articles.

    python3 build-research-library.py <facility-dir> [--out FILE] [--as-of YYYY-MM-DD] [--artifact]

The other reports show the research at work; this one shows its results, read against the evidence as it stands today.

  Studies    each mandate's deliverable (research/reports/RES-M-NNN-*.md, written by research-brief draft): shipped,
             draft, blocked by an open challenge, or living (a standing mandate's latest).
  Articles   topic pages compiled across mandates (research/topics/<slug>.md, written by research-brief article, spec
             §4.1): projections, never edited, regenerated when their evidence moves.

Every citation is checked again today: a finding since superseded (with what replaced it), withdrawn, gone stale, still
provisional or under an open challenge is flagged in the text and in the document's evidence ledger, and each document
carries a health bar and a notice when a reader should not rely on it as written. Drawn from views/_research.py
library(), the same model the Console's Library tab reads. One page: the shelves, then every document in full, linked by
anchors. Writes <facility>/research/reports/library.html and nothing else. No scripts, no external resources.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _research import Facility, esc, md, model, page  # noqa: E402

# the order a citation's health is drawn in, worst last, and how each reads
STATES = [("ok", "holds", "var(--ok)"), ("provisional", "provisional", "var(--t-secondary)"), ("stale", "stale", "var(--warn)"),
          ("challenged", "under challenge", "var(--f-change)"), ("superseded", "superseded", "var(--crit)"),
          ("withdrawn", "withdrawn", "var(--crit)"), ("missing", "missing", "var(--ink)")]
COLOR = {k: c for k, _, c in STATES}
WORD = {k: w for k, w, _ in STATES}
STATUS = {"shipped": ("ok", "shipped"), "living": ("acc", "living study"), "draft": ("", "draft"), "blocked": ("crit", "blocked")}

CSS = """
.shelf{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin-top:14px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:16px 18px 14px;display:flex;flex-direction:column;gap:8px;text-decoration:none;color:inherit;position:relative;overflow:hidden}
.card:hover{border-color:var(--accent)}.card .t{font-family:var(--serif);font-size:1.18rem;font-weight:600;line-height:1.25;text-wrap:balance}
.card .a{font-size:.9rem;color:var(--muted);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.card .meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:.78rem}.card .go{margin-top:auto;font-size:.82rem;color:var(--accent)}
.card.study::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--accent)}.card.study.blocked::before{background:var(--crit)}.card.study.draft::before{background:var(--faint)}.card.study.living::before{background:var(--f-change)}
.card.article{background:linear-gradient(180deg,var(--accent-soft),var(--paper) 42%)}
.hbar{display:flex;height:7px;border-radius:4px;overflow:hidden;background:var(--line)}.hbar span{display:block;height:100%}
.hnote{font-family:var(--mono);font-size:.68rem;color:var(--muted)}.hnote b{font-weight:600}
.doc{background:var(--paper);border:1px solid var(--line);border-radius:12px;margin-top:22px;display:grid;grid-template-columns:minmax(0,1fr) 290px}
@media (max-width:860px){.doc{grid-template-columns:1fr}}
.doc .body{padding:26px 34px 30px;min-width:0}.doc .body h1{font-size:1.75rem;margin:6px 0 10px}.doc .body h2{font-family:var(--serif);font-size:1.2rem;margin:26px 0 6px}
.doc .body p,.doc .body li{max-width:68ch;line-height:1.62}.doc .body ul{padding-left:20px}
.doc aside{border-left:1px solid var(--line);padding:22px 18px;background:var(--ground);border-radius:0 12px 12px 0}
@media (max-width:860px){.doc aside{border-left:0;border-top:1px solid var(--line);border-radius:0 0 12px 12px}}
.doc aside h3{font-family:var(--mono);font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:500;margin:0 0 10px}
.ledger{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px}.ledger li{font-size:.8rem;line-height:1.4;border-left:3px solid var(--ok);padding:2px 0 2px 9px}
.ledger li .i{font-family:var(--mono);font-size:.72rem;color:var(--muted)}.ledger li .w{font-weight:600}
.cite{font-family:var(--mono);font-size:.7rem;border:1px solid var(--line);border-radius:4px;padding:0 5px;margin:0 1px;white-space:nowrap;color:var(--accent);text-decoration:none;background:var(--paper)}
.cite.provisional{border-style:dashed}.cite.stale{color:var(--warn);border-color:var(--warn);background:var(--warn-soft)}
.cite.challenged{color:var(--f-change);border-color:var(--f-change)}.cite.superseded,.cite.withdrawn,.cite.missing{color:var(--crit);border-color:var(--crit);background:var(--crit-soft);text-decoration:line-through}
.notice{border-radius:8px;padding:10px 14px;font-size:.88rem;margin:4px 0 14px}.notice.crit{background:var(--crit-soft);border:1px solid var(--crit)}.notice.warn{background:var(--warn-soft);border:1px solid var(--warn)}
.notice ul{margin:6px 0 0;padding-left:18px}.notice li{margin:2px 0}
.top{font-size:.8rem;margin-top:18px;display:inline-block;color:var(--accent)}
"""


def hbar(health: dict) -> str:
    n = sum(health.values()) or 1
    segs = "".join(f'<span style="width:{100 * health[k] / n:.1f}%;background:{COLOR[k]}" title="{health[k]} {WORD[k]}"></span>'
                   for k, _, _ in STATES if health.get(k))
    words = " · ".join(f'<b style="color:{COLOR[k]}">{health[k]}</b> {WORD[k]}' for k, _, _ in STATES if health.get(k))
    return f'<div class="hbar">{segs}</div><div class="hnote">{words}</div>'


def anchor(d: dict) -> str:
    return "doc-" + (d.get("slug") or d["path"].rsplit("/", 1)[-1].rsplit(".", 1)[0])


def notice(d: dict) -> str:
    flagged = [c for c in d["citations"] if c["state"] != "ok"]
    items = []
    for c in flagged:
        if c["state"] == "superseded":
            items.append(f'<b>{esc(c["id"])}</b> has been superseded by <b>{esc(c.get("by"))}</b>'
                         + (f' ({esc(c["since"])})' if c.get("since") else "") + f' — now: “{esc(c.get("by_claim"))}”')
        elif c["state"] == "challenged":
            items.append(f'<b>{esc(c["id"])}</b> is under open challenge {esc(", ".join(c.get("challenges", [])))}')
        elif c["state"] == "stale":
            items.append(f'<b>{esc(c["id"])}</b> rests on a source past its half-life — re-check before relying on it')
        elif c["state"] == "provisional":
            items.append(f'<b>{esc(c["id"])}</b> is provisional — not yet established')
        else:
            items.append(f'<b>{esc(c["id"])}</b> is {WORD[c["state"]]}')
    head = []
    if d.get("status") == "blocked":
        head.append(f'This study cannot ship: blocking challenge {esc(", ".join(d.get("blocking") or []))} is open.')
    hard = any(c["state"] in ("superseded", "withdrawn", "missing") for c in flagged)
    if hard:
        head.append("The evidence has moved since this was written — the text below no longer matches what the research knows.")
    elif flagged:
        head.append("Some of the evidence below needs care.")
    if not head:
        return ""
    return (f'<div class="notice {"crit" if hard or d.get("status") == "blocked" else "warn"}"><b>{" ".join(head)}</b>'
            + (f'<ul>{"".join(f"<li>{i}</li>" for i in items)}</ul>' if items else "") + "</div>")


def reader(d: dict, mandates: dict) -> str:
    cs = {c["id"]: c for c in d["citations"]}
    aid = anchor(d)

    def badge(fid):
        c = cs.get(fid) or {"id": fid, "state": "missing"}
        tip = f'{c.get("claim") or "no such finding"} — {c.get("tier") or "?"} · {c.get("confidence") or "?"} · {WORD[c["state"]]}'
        return f'<a class="cite {c["state"]}" href="#{aid}-{esc(fid)}" title="{esc(tip)}">{esc(fid)}</a>'
    body = md(d["markdown"], badge)
    ledger = "".join(
        f'<li id="{aid}-{esc(c["id"])}" style="border-left-color:{COLOR[c["state"]]}"><span class="i">{esc(c["id"])} · {esc(c.get("tier") or "—")} · {esc(c.get("confidence") or "—")}'
        f' · {esc(c.get("epistemic") or "—")}</span><br><span class="w" style="color:{COLOR[c["state"]]}">{WORD[c["state"]]}</span> {esc(c.get("claim") or "no such finding")}'
        + (f'<br><span class="i">→ {esc(c["by"])}: {esc(c.get("by_claim"))}</span>' if c["state"] == "superseded" else "") + "</li>"
        for c in d["citations"])
    if d["kind"] == "study":
        cls, word = STATUS.get(d["status"], ("", d["status"]))
        m = mandates.get(d["mandate"]) or {}
        eyebrow = (f'study · {esc(d["mandate"])} · {esc(d.get("method") or "")} · <span class="chip {cls}">{esc(word)}</span>'
                   f' · written {esc(d.get("generated_at") or "—")}')
        extra = f'<p class="cites" style="margin:0 0 12px">Mandate: {esc(m.get("headline") or d["mandate"])}</p>'
    else:
        eyebrow = f'article · compiled {esc(d.get("compiled_at") or "—")} · from {esc(", ".join(d.get("mandates") or []))}'
        extra = f'<p class="lede" style="margin:0 0 10px">{esc(d.get("lede") or "")}</p>' if d.get("lede") else ""
    cut = body.find("</h1>") + 5 if "</h1>" in body else 0   # the title first, then what a reader must know before reading on
    body = body[:cut] + extra + notice(d) + body[cut:]
    return (f'<article class="doc" id="{aid}"><div class="body"><div class="eyebrow">{eyebrow}</div>{body}'
            f'<a class="top" href="#top">↑ back to the library</a></div>'
            f'<aside><h3>Evidence, as it stands today</h3>{hbar(d["health"])}<ul class="ledger" style="margin-top:14px">{ledger}</ul>'
            f'<p class="cites">{esc(d["path"])}</p></aside></article>')


def card(d: dict) -> str:
    n = len(d["citations"])
    if d["kind"] == "study":
        cls, word = STATUS.get(d["status"], ("", d["status"]))
        meta = f'<span class="chip {cls}">{esc(word)}</span><span class="id">{esc(d["mandate"])}</span><span class="mut">{esc(d.get("generated_at") or "")}</span>'
        text = d.get("answer") or ""
        k = f'card study {esc(d["status"])}'
    else:
        meta = "".join(f'<span class="chip">{esc(t)}</span>' for t in d.get("tags") or []) + f'<span class="mut">compiled {esc(d.get("compiled_at") or "")}</span>'
        text = d.get("lede") or ""
        k = "card article"
    return (f'<a class="{k}" href="#{anchor(d)}"><div class="meta">{meta}</div><div class="t">{esc(d["title"])}</div>'
            f'<div class="a">{esc(text)}</div>{hbar(d["health"])}<div class="go">Read · {n} citation{"s" if n != 1 else ""} →</div></a>')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("facility")
    ap.add_argument("--out")
    ap.add_argument("--as-of")
    ap.add_argument("--artifact", action="store_true")
    a = ap.parse_args(argv)
    fac = Path(a.facility).resolve()
    if not (fac / "research").is_dir():
        print(f"build-research-library: {fac}/research not found — is the research capability enabled here?", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(a.as_of) if a.as_of else dt.datetime.utcnow().date()
    fx = Facility(fac, today)
    M = model(fx)
    L = M["library"]
    studies, articles = L["studies"], L["articles"]
    docs = studies + articles
    mandates = {m["id"]: m for m in M["mandates"]}
    cites = sum(len(d["citations"]) for d in docs)
    flagged = sum(1 for d in docs for c in d["citations"] if c["state"] != "ok")
    moved = sum(1 for d in docs if any(c["state"] in ("superseded", "withdrawn", "missing") for c in d["citations"]))
    counts = "".join(f'<div class="c{" alert" if al else ""}"><b>{v}</b><span>{k}</span></div>' for v, k, al in [
        (sum(1 for d in studies if d["status"] in ("shipped", "living")), "studies out", False),
        (sum(1 for d in studies if d["status"] in ("draft", "blocked")), "in draft", False), (len(articles), "articles", False),
        (cites, "citations", False), (flagged, "flagged today", flagged > 0), (moved, "evidence moved", moved > 0)])
    fixture = '<span class="fixture">fixture · every fact invented</span>' if M["fixture"] else ""
    shelf_s = "".join(card(d) for d in studies) or '<p class="mut">No study yet — research-brief draft writes a mandate\'s deliverable.</p>'
    shelf_a = "".join(card(d) for d in articles) or '<p class="mut">No article yet — research-brief article compiles a topic page across mandates.</p>'
    body = f"""
  <div class="eyebrow" id="top">research capability · generated by build-research-library · {esc(str(today))}</div>
  <h1>{esc(fx.name)} — the research library {fixture}</h1>
  <p class="lede">What the research has concluded: each mandate's study, and articles that compile what several mandates found about one topic. Every citation is read against the evidence as it stands today — a finding since superseded, challenged or gone stale is flagged where it is cited.</p>
  <div class="counts">{counts}</div>
  <section><header><div class="q">What has the research concluded?</div><div class="w">One study per mandate: its answer, how it stands, and how much of the evidence it cites still holds. A standing mandate's latest study is living; a draft with a blocking challenge open cannot ship.</div></header>
  <div class="shelf">{shelf_s}</div></section>
  <section><header><div class="q">What do we know, by topic?</div><div class="w">Articles compiled across mandates. They are projections — regenerated, never edited — so an article whose evidence has moved is due for recompiling.</div></header>
  <div class="shelf">{shelf_a}</div>
  <div class="legend">{"".join(f'<span><i style="background:{c}"></i>{w}</span>' for _, w, c in STATES)}</div></section>
  <section><header><div class="q">The documents</div><div class="w">Each in full, with its evidence ledger. Hover a citation for the finding; follow it to the ledger entry.</div></header>
  {"".join(reader(d, mandates) for d in docs)}</section>
"""
    title = "Research Library" if a.artifact else f"{fx.name} — research library"
    out = Path(a.out) if a.out else fac / "research" / "reports" / "library.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(title, body, CSS, a.artifact), encoding="utf-8")
    print(f"research-library → {out}\n  {len(studies)} stud{'y' if len(studies) == 1 else 'ies'} · {len(articles)} article(s) · {cites} citation(s), {flagged} flagged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
