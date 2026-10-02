"""render_glance — "Portfolio at a Glance" as a self-contained HTML report.

Called by collect.py after the index and registry are compiled. Draws the three pictures the
collector can draw from state alone — the 90-day lanes, one figure per member, what moved this
week — plus the digest strip. Every mark is computed from the latest snapshots, the registry and
the checks; nothing is narrated. Query and synthesis figures are the reviewer's and are not here.

Encodings match capabilities/portfolio/views/{home,project}.dash.yaml and the reviewed page
examples/html/portfolio-lean-views.html: owner colours in fixed order, at-risk as a critical
ring, silent lanes hatched, milestones as pips, risks as circles sized by score, status colours
always carrying a label. No scripts and no external resources: the app's content-security policy
forbids them, so the page rides the system font stacks and is fully self-contained.
"""
from __future__ import annotations

import datetime as dt
import html
from collections import Counter

OWNER_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#e87ba4", "#eda100"]  # fixed order, never cycled past 6


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _date(s) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


class Glance:
    def __init__(self, run, members, latest, prevs, checks, index):
        self.run, self.members, self.latest, self.prevs, self.checks, self.index = run, members, latest, prevs, checks, index
        self.today = run.today
        self.active = [m for m in members if m.get("status") in ("active", "paused", "closing")]
        self.proposed = [m for m in members if m.get("status") == "proposed"]
        owners = []
        for m in self.active:
            s = latest.get(m["id"])
            for d in (s or {}).get("deadlines", []):
                if d.get("owner") and d["owner"] not in owners:
                    owners.append(d["owner"])
        self.owner_color = {o: OWNER_COLORS[min(i, len(OWNER_COLORS) - 1)] for i, o in enumerate(owners)}
        self.checks_by_member = {}
        for c in checks:
            self.checks_by_member.setdefault(c["member"], []).append(c)

    # ── 1. lanes ─────────────────────────────────────────────────────────────
    def lanes_svg(self) -> str:
        days = self.run.deadline_window
        x0, x1, lane_h, top = 180, 936, 64, 60
        px = (x1 - x0) / days
        def X(d: dt.date) -> float:
            return x0 + max(0, min(days, (d - self.today).days)) * px
        rows = self.active
        h = top + lane_h * max(1, len(rows)) + 20
        out = [f'<svg viewBox="0 0 960 {h}" role="img" aria-label="Member lanes over the next {days} days">']
        out.append(f'<line class="rule" x1="{x0}" y1="44" x2="{x1}" y2="44"/><text x="{x0}" y="30" class="mono">{self.today.strftime("%b %-d")} · today</text>')
        # month ticks
        d = self.today.replace(day=1)
        while True:
            d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
            if (d - self.today).days > days:
                break
            out.append(f'<text x="{X(d):.0f}" y="30" class="mono" text-anchor="middle">{d.strftime("%b")}</text><line class="grid" x1="{X(d):.0f}" y1="44" x2="{X(d):.0f}" y2="{h-20}"/>')
        out.append(f'<line class="today" x1="{x0}" y1="44" x2="{x0}" y2="{h-20}"/>')
        # collision windows: ≥3 dots one owner within 5 days across lanes
        dots = []
        for i, m in enumerate(rows):
            s = self.latest.get(m["id"]) or {}
            for dl in s.get("deadlines", []):
                dd = _date(dl["date"])
                if dd and 0 <= (dd - self.today).days <= days and dl.get("owner"):
                    dots.append((dd, dl["owner"], i))
        dots.sort()
        shaded = set()
        for k, (dd, o, _) in enumerate(dots):
            win = [x for x in dots if x[1] == o and 0 <= (x[0] - dd).days <= 5]
            if len(win) >= 3 and (o, dd) not in shaded:
                shaded.add((o, dd))
                lanes_in = sorted({x[2] for x in win})
                y_a = top + lanes_in[0] * lane_h - 8; y_b = top + lanes_in[-1] * lane_h + lane_h - 8
                out.append(f'<rect x="{X(dd)-6:.0f}" y="{y_a}" width="{(win[-1][0]-dd).days*px+12:.0f}" height="{y_b-y_a}" fill="var(--crit-soft)" rx="3"/>'
                           f'<text x="{X(dd)+((win[-1][0]-dd).days*px)/2:.0f}" y="{y_b+12}" class="tiny" text-anchor="middle" fill="var(--crit)">{len(win)} in {max(1,(win[-1][0]-dd).days)} days · {esc(o)}</text>')
        for i, m in enumerate(rows):
            s = self.latest.get(m["id"])
            y = top + i * lane_h
            silent = any(c["id"] == "portfolio.member-silent" for c in self.checks_by_member.get(m["id"], []))
            unreach = any(c["id"] == "portfolio.member-unreachable" for c in self.checks_by_member.get(m["id"], []))
            out.append(f'<g transform="translate(0,{y})">')
            if silent or unreach:
                out.append(f'<rect x="{x0}" y="6" width="{x1-x0}" height="40" fill="url(#hatch)" opacity=".45" rx="3"/>')
            fill = ' fill="var(--muted)"' if silent or unreach else ""
            out.append(f'<text x="12" y="16" class="lbl"{fill}>{esc(m.get("name") or m["id"])}</text>')
            phase = (s or {}).get("project", {}).get("current_phase") or "—"
            out.append(f'<text x="12" y="32" class="mut">{esc(phase)} · {esc(m.get("priority") or "")}</text>')
            # pips
            ms = (s or {}).get("milestones") or {}
            done, total = ms.get("complete", 0), ms.get("total", 0)
            at_risk_ids = {x["id"] for x in ms.get("next_due", []) if x["status"] in ("at_risk", "blocked", "overdue")}
            open_rows = ms.get("next_due", [])
            px_i = 0
            out.append('<g transform="translate(12,40)">')
            for k in range(done):
                out.append(f'<rect x="{px_i}" y="0" width="10" height="10" rx="2" fill="var(--ink)"/>'); px_i += 14
                if px_i > 150: break
            for x in open_rows:
                if px_i > 150: break
                stroke = "var(--crit)" if x["id"] in at_risk_ids else "var(--faint)"
                sw = 2 if x["id"] in at_risk_ids else 1
                out.append(f'<rect x="{px_i}" y="0" width="10" height="10" rx="2" fill="none" stroke="{stroke}" stroke-width="{sw}"><title>{esc(x["id"])} · {esc(x["status"])}</title></rect>'); px_i += 14
            out.append(f'<text x="{px_i+4}" y="9" class="tiny">{done} of {total}</text></g>')
            out.append(f'<line class="grid" x1="{x0}" y1="26" x2="{x1}" y2="26"/>')
            if unreach:
                out.append(f'<text x="{(x0+x1)/2:.0f}" y="30" class="mut" text-anchor="middle">unreachable at the last collect — {esc(next(c.get("reason") for c in self.checks_by_member[m["id"]] if c["id"]=="portfolio.member-unreachable"))}</text>')
            elif silent:
                dd = next(c.get("days") for c in self.checks_by_member[m["id"]] if c["id"] == "portfolio.member-silent")
                out.append(f'<text x="{(x0+x1)/2:.0f}" y="30" class="mut" text-anchor="middle">silent {dd if dd is not None else "—"} days — nothing written</text>')
            for dl in (s or {}).get("deadlines", []):
                dd = _date(dl["date"])
                if not dd or not (0 <= (dd - self.today).days <= days):
                    continue
                col = self.owner_color.get(dl.get("owner"), "var(--faint)")
                risky = dl.get("status") in ("at_risk", "blocked", "overdue")
                ring = ' stroke="var(--crit)" stroke-width="3"' if risky else ""
                out.append(f'<circle cx="{X(dd):.0f}" cy="26" r="6" fill="{col}"{ring}><title>{esc(dl["date"])} · {esc(dl["label"])} · {esc(dl.get("owner") or "no owner")}{" · "+esc(dl.get("status")) if dl.get("status") else ""}</title></circle>')
                if risky:
                    out.append(f'<text x="{X(dd)+12:.0f}" y="19" class="tiny" fill="var(--crit)">{esc(dl["ref"])} {esc(dl.get("status")).replace("_"," ")}</text>')
            out.append("</g>")
        out.append('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--faint)" stroke-width="1.5"/></pattern></defs></svg>')
        return "".join(out)

    def lanes_legend(self) -> str:
        items = "".join(f'<span><i style="background:{c}"></i>{esc(o)}</span>' for o, c in self.owner_color.items())
        return (f'<div class="legend">{items}<span class="ring"><i></i>at risk</span><span class="sq"><i style="background:var(--ink)"></i>milestone done</span><span class="hatch"><i></i>silent or unreachable</span></div>')

    def counts(self) -> str:
        nd = min((_date(d["date"]) for m in self.active for d in (self.latest.get(m["id"]) or {}).get("deadlines", []) if _date(d["date"]) and _date(d["date"]) >= self.today), default=None)
        tiles = [(len(self.active), "members"), (len(self.proposed), "in the hopper"),
                 (f'{(nd - self.today).days}<small> d</small>' if nd else "—", "to next deadline"), (len(self.checks), "checks fired")]
        return '<div class="counts">' + "".join(f'<div class="c"><b>{v}</b><span>{k}</span></div>' for v, k in tiles) + "</div>"

    # ── 2. one member ────────────────────────────────────────────────────────
    def project_svg(self, m, s) -> str:
        p, ms, rk, dc, act, hv = s["project"], s["milestones"], s["risks"], s["decisions"], s["activity"], s["harvest"]
        out = ['<svg viewBox="0 0 960 300" role="img" aria-label="Member at a glance">']
        # milestones as blocks
        out.append('<text x="12" y="20" class="mono">MILESTONES</text><g transform="translate(120,6)">')
        x = 0
        blocks = [dict(id=f"done-{i}", status="complete", percent_complete=100) for i in range(ms["complete"])] + ms["next_due"]
        for b in blocks[:10]:
            st = b["status"]; pct = b.get("percent_complete") or 0
            if st in ("complete", "completed", "done"):
                out.append(f'<rect x="{x}" y="0" width="56" height="18" rx="3" fill="var(--ink)"/>')
            else:
                stroke = "var(--crit)" if st in ("at_risk", "blocked", "overdue") else "var(--faint)"
                sw = 2 if stroke == "var(--crit)" else 1
                dash = ' stroke-dasharray="3 2"' if not b.get("owner") else ""
                out.append(f'<rect x="{x}" y="0" width="56" height="18" rx="3" fill="none" stroke="{stroke}" stroke-width="{sw}"{dash}/>'
                           f'<rect x="{x}" y="0" width="{56*min(100,pct)/100:.0f}" height="18" rx="3" fill="{"var(--crit-soft)" if stroke=="var(--crit)" else "var(--line)"}"/>'
                           f'<text x="{x+28}" y="13" class="tiny" text-anchor="middle">{esc(b["id"].split("-")[0])}</text><title>{esc(b["id"])} · {esc(st)} · {pct}%</title>')
            x += 62
        out.append(f'<text x="0" y="36" class="tiny">{ms["complete"]} of {ms["total"]} done · {ms["in_progress"]+ms["at_risk"]+ms["blocked"]} in flight · {ms["at_risk"]+ms["blocked"]} at risk or blocked</text></g>')
        # countdown ring
        nxt = ms["next_due"][0] if ms["next_due"] else None
        if nxt and nxt.get("planned_end"):
            dd = _date(nxt["planned_end"]); daysn = (dd - self.today).days if dd else None
            pct = nxt.get("percent_complete") or 0; crit = nxt["status"] in ("at_risk", "blocked", "overdue")
            col = "var(--crit)" if crit else "var(--accent)"
            circ = 2 * 3.14159 * 46
            out.append(f'<g transform="translate(740,10)"><circle cx="60" cy="60" r="46" fill="none" stroke="var(--line)" stroke-width="8"/>'
                       f'<circle cx="60" cy="60" r="46" fill="none" stroke="{col}" stroke-width="8" stroke-dasharray="{circ:.0f}" stroke-dashoffset="{circ*(1-pct/100):.0f}" transform="rotate(-90 60 60)" stroke-linecap="round"/>'
                       f'<text x="60" y="56" class="big" text-anchor="middle" fill="{col}">{daysn if daysn is not None else "—"}</text><text x="60" y="74" class="tiny" text-anchor="middle">days</text>'
                       f'<text x="60" y="126" class="lbl" text-anchor="middle">{esc(nxt["id"])}</text><text x="60" y="142" class="mut" text-anchor="middle">{esc(nxt["planned_end"])} · {pct}% · {esc(nxt["status"]).replace("_"," ")}</text></g>')
        # people
        out.append('<text x="12" y="90" class="mono">PEOPLE</text><g transform="translate(120,74)">')
        y = 0
        for pp in s["people"][:4]:
            col = self.owner_color.get(pp["id"], "var(--faint)")
            n = len(pp.get("in_flight_milestones") or [])
            out.append(f'<circle cx="12" cy="{y+12}" r="12" fill="{col}"/><text x="32" y="{y+10}" class="lbl">{esc(pp.get("name") or pp["id"])}</text><text x="32" y="{y+24}" class="tiny">{esc(pp.get("role") or "role not recorded")}</text>')
            for k in range(min(n, 6)):
                out.append(f'<rect x="{260+k*30}" y="{y+6}" width="26" height="12" rx="2" fill="{col}"/>')
            out.append(f'<text x="{260+min(n,6)*30+6}" y="{y+16}" class="tiny">{n} in flight</text>' if n else f'<rect x="260" y="{y+6}" width="26" height="12" rx="2" fill="none" stroke="var(--line)"/><text x="292" y="{y+16}" class="tiny">nothing in flight</text>')
            y += 34
        out.append("</g>")
        # risks
        out.append('<text x="12" y="232" class="mono">OPEN RISKS</text><g transform="translate(120,214)">')
        x = 0
        for r in rk["high"][:3]:
            sc = r.get("score") or 0; rad = 8 + sc * 1.8
            stroke = "var(--crit)" if sc >= 9 else "var(--warn)"
            fill = "var(--crit-soft)" if sc >= 9 else "none"
            out.append(f'<circle cx="{x+24}" cy="24" r="{rad:.0f}" fill="{fill}" stroke="{stroke}" stroke-width="2"><title>{esc(r["id"])} · {esc(r.get("title"))}</title></circle><text x="{x+24}" y="28" class="lbl" text-anchor="middle">{sc}</text>'
                       f'<text x="{x+58}" y="20" class="lbl">{esc(r["id"])}</text><text x="{x+58}" y="34" class="tiny">{esc((r.get("title") or "")[:38])}{"…" if len(r.get("title") or "")>38 else ""}</text>')
            x += 240
        if not rk["high"]:
            out.append('<text x="0" y="28" class="tiny">no risk scored 6 or more</text>')
        out.append("</g>")
        # activity + harvest
        out.append('<g transform="translate(740,190)"><text x="0" y="0" class="mono">ACTIVITY · 7 D</text>')
        ev = act.get("events_7d", 0)
        out.append(f'<rect x="0" y="12" width="{min(120, ev*2)}" height="10" fill="var(--faint)"/><text x="{min(120, ev*2)+6}" y="21" class="tiny">{ev} events</text>')
        out.append('<text x="0" y="46" class="mono">HARVEST</text>')
        xh = 0
        for sf in hv.get("surfaces", [])[:4]:
            age = sf.get("cursor_age_days"); col = "var(--ok)" if age is not None and age <= self.run.stale_days else "var(--warn)"
            out.append(f'<circle cx="{xh+6}" cy="60" r="5" fill="{col}"/><text x="{xh+16}" y="64" class="tiny">{esc(sf["surface"])} {age if age is not None else "—"} d</text>'); xh += 74
        if not hv.get("surfaces"):
            out.append('<text x="0" y="64" class="tiny">no harvest cursors</text>')
        out.append("</g></svg>")
        return "".join(out)

    # ── 3. week ──────────────────────────────────────────────────────────────
    def week_rows(self) -> str:
        rows = []
        for m in self.active:
            s = self.latest.get(m["id"]); prev = self.prevs.get(m["id"]) or {}
            if not s:
                rows.append(f'<tr><td class="lbl mut">{esc(m["id"])}</td><td colspan="3" class="mut">unreachable</td></tr>'); continue
            moved = []
            if prev and "milestones" in prev:
                pm = {x["id"]: x for x in prev["milestones"]["next_due"]}
                for x in s["milestones"]["next_due"]:
                    q = pm.get(x["id"])
                    if q and (q["status"] != x["status"] or q.get("percent_complete") != x.get("percent_complete")):
                        moved.append(f'{esc(x["id"])} <span class="mono">{q.get("percent_complete")} → {x.get("percent_complete")}%</span>')
                new_r = [x["id"] for x in s["risks"]["high"] if x["id"] not in {y["id"] for y in prev["risks"]["high"]}]
                new_d = [x["id"] for x in s["decisions"]["recent"] if x["id"] not in {y["id"] for y in prev["decisions"]["recent"]}]
            else:
                new_r, new_d = [], []
            ev = s["activity"].get("events_7d", 0)
            chk = self.checks_by_member.get(m["id"], [])
            new_bits = [f'<span class="chip bad">▲ risk {esc(i)}</span>' for i in new_r] + [f'<span class="chip decl">● decision {esc(i)}</span>' for i in new_d] + [f'<span class="chip warn">check: {esc(c["id"].split(".")[-1])}</span>' for c in chk]
            rows.append(f'<tr><td class="lbl">{esc(m.get("name") or m["id"])}</td><td><span class="bar" style="width:{min(140, ev*2)}px"></span> <span class="tiny">{ev}</span></td><td>{"; ".join(moved) if moved else "<span class=mut>no movement</span>"}</td><td>{" ".join(new_bits) if new_bits else "<span class=mut>—</span>"}</td></tr>')
        return "".join(rows)

    def digest(self) -> str:
        nd = min((_date(d["date"]) for m in self.active for d in (self.latest.get(m["id"]) or {}).get("deadlines", []) if _date(d["date"]) and _date(d["date"]) >= self.today), default=None)
        nm = next((m["id"] for m in self.active for d in (self.latest.get(m["id"]) or {}).get("deadlines", []) if nd and d["date"] == str(nd)), "")
        line = f'Portfolio — {len(self.members)} members ({len(self.active)} active · {len(self.proposed)} proposed) · next deadline {nd or "—"} {esc(nm)} · last collect {self.run.now.strftime("%Y-%m-%d %H:%M")}'
        if self.checks:
            body = "\n".join(f'<span class="warn">⚠ {c["severity"].upper():<6}</span> {esc(c["id"])} — {esc(c["member"])}' + (f' {esc(c.get("surface"))} {c.get("days")} d' if c.get("surface") else (f' {c.get("days")} d' if c.get("days") is not None else "")) + (f' ({esc(c.get("reason"))})' if c.get("reason") else "") for c in self.checks)
        else:
            body = f'💤 Portfolio is current — {len(self.active)} members collected, nothing unreachable, silent, or stale.'
        return f'<div class="strip">{line}\n\n{body}</div>'

    # ── page ─────────────────────────────────────────────────────────────────
    def html(self) -> str:
        sections = [f'''
  <section><header><div class="q">Where is everyone, and what is coming?</div><div class="w">One lane per member · the next {self.run.deadline_window} days · dots are dated commitments, coloured by who owns them</div></header>
  <div class="fig">{self.lanes_svg()}{self.lanes_legend()}</div>{self.counts()}</section>''']
        for m in self.active:
            s = self.latest.get(m["id"])
            if not s:
                continue
            cites = "manifest.yaml · state.json · milestones/ · people/ · risks/ · logs/activity.ndjson · harvest/cursors/"
            sections.append(f'''
  <section><header><div class="q">What is {esc(m.get("name") or m["id"])}, right now?</div><div class="w">Understanding · as of {esc(s["captured_at"][:10])} · rev {esc(s.get("source_rev") or "—")} · <a href="../understanding/{esc(m["id"])}.md">the cited page</a></div></header>
  <div class="fig">{self.project_svg(m, s)}<p class="cites">Marks trace to <b>{cites}</b> in the member's project-state.</p></div></section>''')
        sections.append(f'''
  <section><header><div class="q">What moved this week?</div><div class="w">A diff between the last two collects</div></header>
  <div class="fig"><div class="tbl"><table><thead><tr><th>Member</th><th>Activity · 7 d</th><th>Moved</th><th>New</th></tr></thead><tbody>{self.week_rows()}</tbody></table></div></div></section>''')
        sections.append(f'''
  <section><header><div class="q">What reaches the daily digest?</div><div class="w">One standing line and at most three checks: unreachable, silent, harvest stale</div></header>{self.digest()}</section>''')
        return PAGE.format(title=esc(self.run.portfolio_name), date=esc(str(self.today)), now=esc(self.run.now.strftime("%Y-%m-%d %H:%M")), body="".join(sections))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — at a glance</title>
<style>
:root{{--ground:#F5F7F4;--paper:#FFFFFF;--ink:#1B2230;--muted:#6B7480;--faint:#A9B1B8;--line:#DDE3DE;--rule:#B9C2BC;--accent:#1F5F6B;--accent-soft:#E3EEF0;--crit:#d03b3b;--crit-soft:#F6E0E0;--warn:#c98500;--warn-soft:#F7ECD6;--ok:#2E7D4F;--bad-soft:#F6E0E0;
--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--serif:"Newsreader",Georgia,serif}}
@media (prefers-color-scheme:dark){{:root{{--ground:#12181E;--paper:#1A222A;--ink:#E7EBEE;--muted:#A3ACB4;--faint:#5B6670;--line:#2C3640;--rule:#465262;--accent:#6FBFC9;--accent-soft:#1E3238;--crit:#e66767;--crit-soft:#3E2222;--warn:#e0b463;--warn-soft:#3A2F17;--ok:#6CC58F;--bad-soft:#3E2222}}}}
*{{box-sizing:border-box}}body{{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 20px 64px}}h1{{font-family:var(--serif);font-weight:600;font-size:2rem;line-height:1.1;margin:0}}
.eyebrow{{font-family:var(--mono);font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}.lede{{color:var(--muted);max-width:62ch;margin:8px 0 28px}}
section{{margin-bottom:56px}}section>header .q{{font-family:var(--serif);font-size:1.5rem;font-weight:600}}section>header .w{{color:var(--muted);font-size:.92rem;margin-top:2px}}
.fig{{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px 20px 14px;margin-top:14px}}svg{{width:100%;height:auto;display:block;font-family:var(--sans)}}
svg text{{fill:var(--ink);font-size:12.5px}}svg .mut{{fill:var(--muted);font-size:11px}}svg .tiny{{fill:var(--muted);font-size:10px}}svg .mono{{font-family:var(--mono);font-size:10.5px;fill:var(--muted)}}
svg .lbl{{font-weight:600;font-size:13px}}svg .big{{font-family:var(--serif);font-weight:600;font-size:30px}}svg .grid{{stroke:var(--line);stroke-width:1}}svg .rule{{stroke:var(--rule);stroke-width:1}}svg .today{{stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3}}
.legend{{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.8rem;color:var(--muted);margin-top:10px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}}.legend .sq i{{border-radius:2px}}.legend .ring i{{background:none;border:2px solid var(--crit)}}.legend .hatch i{{border-radius:2px;background:repeating-linear-gradient(45deg,var(--faint) 0 2px,transparent 2px 5px)}}
.counts{{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}}.counts .c{{border:1px solid var(--line);border-radius:8px;background:var(--paper);padding:10px 14px;min-width:96px}}.counts .c b{{display:block;font-family:var(--serif);font-size:1.6rem;font-weight:600;line-height:1}}.counts .c small{{font-size:.9rem;color:var(--muted)}}.counts .c span{{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.cites{{font-family:var(--mono);font-size:.74rem;color:var(--muted);margin:10px 0 0;line-height:1.7}}.cites b{{color:var(--accent);font-weight:500}}
.tbl{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-family:var(--mono);font-size:.7rem;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:500}}
td.lbl{{font-weight:600}}.mut{{color:var(--muted)}}.tiny{{font-size:.78rem;color:var(--muted)}}.bar{{display:inline-block;height:10px;background:var(--faint);vertical-align:middle}}
.chip{{display:inline-block;border-radius:3px;padding:1px 7px;font-family:var(--mono);font-size:.74rem;white-space:nowrap}}.chip.bad{{background:var(--bad-soft);color:var(--crit)}}.chip.warn{{background:var(--warn-soft);color:var(--warn)}}.chip.decl{{background:var(--accent-soft);color:var(--accent)}}
.strip{{font-family:var(--mono);font-size:.84rem;white-space:pre-wrap;line-height:1.6;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:14px 18px;margin-top:14px}}.strip .warn{{color:var(--warn);font-weight:600}}
a{{color:var(--accent)}}
</style></head><body><div class="wrap">
  <div class="eyebrow">portfolio capability · generated by portfolio-collector · {now}</div>
  <h1>{title} — at a glance</h1>
  <p class="lede">Drawn from the latest snapshot of each member, the compiled index and the registry. Every mark carries its source; nothing is narrated. Regenerated on every collect.</p>
{body}
</div></body></html>
"""


def render(run, members, latest, prevs, checks, index) -> str:
    return Glance(run, members, latest, prevs, checks, index).html()
