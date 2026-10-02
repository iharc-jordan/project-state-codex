#!/usr/bin/env node
// ---------------------------------------------------------------------------
// build-sred-dashboard — renders the SR&ED capture status of a project-state
// facility as a single self-contained HTML page.
//
//   node build-sred-dashboard.mjs <facility-dir> [options]
//
//   --out, -o <path>     output file (default: <facility>/reports/adhoc/sred-dashboard.html)
//   --artifact           emit body-only HTML for the Claude Artifact publisher
//   --as-of <YYYY-MM-DD> compute deadline countdowns from this date (default: today)
//   --json <path>        also write the derived data as JSON (for other consumers)
//
// Reads (all optional except sred/):
//   sred/uncertainties/*.yaml   sred/experiments/*.yaml   sred/advancements/*.yaml
//   sred/evidence-log.ndjson    sred/inbox/*.yaml         sred/cost-tracking/*.yaml
//   sred/criteria.yaml          state/sred.json           manifest.yaml
//   milestones/*.yaml
//
// Writes nothing back into the substrate. Read-only by design: this is a lens,
// not a writer. Nothing here asserts eligibility — it reports what is captured
// and what is missing. Eligibility is the advisor's call.
// ---------------------------------------------------------------------------

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseYaml } from './lib-yaml.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GENERATOR = 'capabilities/sred/views/build-sred-dashboard.mjs';

// ── args ───────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const opt = { artifact: false, asOf: null, out: null, json: null, facility: null };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--artifact') opt.artifact = true;
  else if (a === '--as-of') opt.asOf = argv[++i];
  else if (a === '--out' || a === '-o') opt.out = argv[++i];
  else if (a === '--json') opt.json = argv[++i];
  else if (a.startsWith('-')) { console.error('unknown option ' + a); process.exit(2); }
  else opt.facility = a;
}
if (!opt.facility) {
  console.error('usage: node build-sred-dashboard.mjs <facility-dir> [--out FILE] [--artifact] [--as-of YYYY-MM-DD]');
  process.exit(2);
}
const FAC = path.resolve(opt.facility);
if (!fs.existsSync(path.join(FAC, 'sred'))) {
  console.error(`no sred/ directory under ${FAC} — is the sred capability enabled on this facility?`);
  process.exit(1);
}

// ── small helpers ──────────────────────────────────────────────────────────
const readText = (p) => { try { return fs.readFileSync(p, 'utf8'); } catch { return null; } };
const readYaml = (p) => { const t = readText(p); return t === null ? null : parseYaml(t); };
const listYaml = (dir) => {
  try {
    return fs.readdirSync(dir).filter((f) => /\.ya?ml$/.test(f) && !f.startsWith('.')).sort()
      .map((f) => ({ file: f, data: readYaml(path.join(dir, f)) })).filter((x) => x.data);
  } catch { return []; }
};
const s = (v) => (v === null || v === undefined ? '' : String(v)).trim();
const arr = (v) => (Array.isArray(v) ? v : v === null || v === undefined || v === '' ? [] : [v]);
const dayMs = 86400000;
const asOf = opt.asOf || new Date().toISOString().slice(0, 10);
const daysBetween = (a, b) => {
  const x = Date.parse(String(a).slice(0, 10) + 'T00:00:00Z');
  const y = Date.parse(String(b).slice(0, 10) + 'T00:00:00Z');
  return Number.isNaN(x) || Number.isNaN(y) ? null : Math.round((y - x) / dayMs);
};
const sinceAsOf = (d) => (d ? daysBetween(d, asOf) : null);
const shortId = (m) => s(m).split('-')[0];

// Block scalars in the substrate are hard-wrapped at ~80 columns for the sake of
// `git diff`. Rewrap them for the screen: join wrapped lines, keep list items and
// paragraph breaks as the author wrote them.
const reflow = (t) => String(t || '').split(/\n{2,}/).map((par) =>
  par.split('\n').reduce((acc, raw) => {
    const line = raw.trim();
    if (!line) return acc;
    if (!acc.length || /^(\d+[.)]|[-*\u2022])\s/.test(line) || /^[A-Z][A-Z0-9 \/&-]{3,}[:\u2014]/.test(line)) acc.push(line);
    else acc[acc.length - 1] += ' ' + line;
    return acc;
  }, []).join('\n')
).join('\n\n').trim();

// ── load ───────────────────────────────────────────────────────────────────
const SRED = path.join(FAC, 'sred');
const manifestRaw = readText(path.join(FAC, 'manifest.yaml')) || '';
const manifest = manifestRaw ? parseYaml(manifestRaw) : {};
const capSred = manifest?.capabilities?.sred || {};
const stateSred = (() => { const t = readText(path.join(FAC, 'state', 'sred.json')); try { return t ? JSON.parse(t) : null; } catch { return null; } })();
const criteria = readYaml(path.join(SRED, 'criteria.yaml'));

const tus = listYaml(path.join(SRED, 'uncertainties')).map((x) => x.data);
const exs = listYaml(path.join(SRED, 'experiments')).map((x) => x.data);
const advs = listYaml(path.join(SRED, 'advancements')).map((x) => x.data);
const inbox = listYaml(path.join(SRED, 'inbox')).map((x, i, a) => ({ ...x.data, _file: a[i]?.file }));
const inboxFiles = listYaml(path.join(SRED, 'inbox'));
inbox.forEach((r, i) => { r._file = inboxFiles[i].file; });

const costFiles = listYaml(path.join(SRED, 'cost-tracking'));
const effortBasis = costFiles.map((x) => x.data).find((d) => d && (d.entity === 'cost_effort_basis' || d.figures)) || null;

const evidence = (readText(path.join(SRED, 'evidence-log.ndjson')) || '')
  .split('\n').map((l) => l.trim()).filter(Boolean)
  .map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean)
  .sort((a, b) => s(b.date).localeCompare(s(a.date)));

const milestones = {};
for (const { data } of listYaml(path.join(FAC, 'milestones'))) {
  if (data && data.id) milestones[shortId(data.id)] = data;
}

// ── index ──────────────────────────────────────────────────────────────────
const byId = {};
[...tus, ...exs, ...advs].forEach((e) => { if (e && e.id) byId[e.id] = e; });

const exsForTu = (tuId) => exs.filter((e) => s(e.linked_tu) === tuId || arr(e.linked_tus).includes(tuId))
  .concat(arr(byId[tuId]?.linked_experiments).map((id) => byId[id]).filter((e) => e && s(e.linked_tu) !== tuId))
  .filter((e, i, a) => a.indexOf(e) === i);
const advsForEx = (exId) => advs.filter((a) => arr(a.linked_experiments).includes(exId));
const evidenceFor = (id, key) => evidence.filter((e) => s(e[key]) === id);
const lastEvidenceDate = (exId) => {
  const d = evidenceFor(exId, 'ex_id').map((e) => s(e.date)).filter(Boolean).sort();
  return d.length ? d[d.length - 1] : null;
};
const effortFigure = (exId) => arr(effortBasis?.figures).find((f) => s(f.ex) === exId) || null;
const exDays = (e) => arr(e.people_involved).reduce((n, p) => n + (Number(p?.eligible_days) || 0), 0);

// ── findings (the gap analysis from project-sred-tracker) ───────────────────
const findings = [];
const finding = (severity, code, title, entity, detail, action) =>
  findings.push({ severity, code, title, entity, detail, action });

for (const tu of tus) {
  const linked = exsForTu(tu.id);
  if (linked.length === 0) {
    finding('high', 'tu-no-ex', 'Uncertainty with no experiment', tu.id,
      'No experiment record investigates this uncertainty. Section E without a Section F counterpart.',
      'Record the experimental work as an EX this fiscal year, or exclude this TU from the claim.');
  }
  for (const ex of linked) {
    const lag = daysBetween(s(ex.start_date), s(tu.identified_date));
    if (lag !== null && lag > 0) {
      const where = s(ex.capture_note) ? ex.id : s(tu.capture_note) ? tu.id : null;
      finding(where ? 'low' : 'medium', 'tu-after-ex',
        'Uncertainty identified after the work began', `${tu.id} ← ${ex.id}`,
        `${tu.id} identified ${s(tu.identified_date)}, ${lag} days after ${ex.id} started ${s(ex.start_date)}.` +
        (where ? ` The capture note on ${where} explains when the record was written.` : ' No capture note explains the gap.'),
        where ? 'Keep the disclosure visible at T661 drafting — an assessor will read the dates before the prose.'
              : 'Add a capture_note stating when the record was written and which contemporaneous evidence it draws on.');
    }
  }
  for (const mid of arr(tu.linked_milestones)) {
    const m = milestones[shortId(mid)];
    if (m && (s(m.status) === 'planned' || Number(m.percent_complete) === 0)) {
      finding('medium', 'anchor-mismatch', 'Anchored to a milestone that has not started', `${tu.id} → ${shortId(mid)}`,
        `${shortId(mid)} is ${s(m.status) || 'planned'} at ${Number(m.percent_complete) || 0}% while the uncertainty is ${s(tu.status)}.`,
        'Re-anchor to the milestone where the work actually landed, or update the milestone record.');
    }
  }
}

for (const ex of exs) {
  if (!s(ex.linked_tu) && arr(ex.linked_tus).length === 0) {
    finding('high', 'ex-no-tu', 'Experiment with no uncertainty', ex.id,
      'Work recorded without a declared technological uncertainty behind it.',
      'Link an existing TU or record the uncertainty this work was investigating.');
  }
  if (arr(ex.evidence_records).length === 0) {
    finding('high', 'ex-no-evidence', 'Experiment with no evidence records', ex.id,
      'No contemporaneous records cited. This is the first thing an audit asks for.',
      'Cite commits, test output, design docs or meeting notes dated at the time of the work.');
  }
  if (!s(ex.observations_and_results)) {
    finding('high', 'ex-no-results', 'Experiment with no documented outcome', ex.id,
      'Section F needs what was found — including failures, limits and iterations.',
      'Record observations and results, or mark the experiment abandoned with a reason.');
  }
  const linkedAdv = advsForEx(ex.id);
  const done = s(ex.status) === 'complete';
  const age = done ? sinceAsOf(s(ex.end_date) || s(ex.start_date)) : null;
  if (done && linkedAdv.length === 0) {
    const stale = age !== null && age > 90;
    finding(stale ? 'medium' : 'low', 'ex-no-adv', 'Completed experiment with no advancement', ex.id,
      `Complete${age !== null ? ` for ${age} days` : ''} with nothing recorded in Section G.`,
      'Record a narrow advancement proportionate to the observed results, or state why no knowledge gain is claimed.');
  }
  if (!done) {
    const last = lastEvidenceDate(ex.id);
    const gap = last ? sinceAsOf(last) : null;
    if (gap === null) {
      finding('medium', 'ex-no-log', 'Active experiment absent from the evidence log', ex.id,
        'No evidence-log entry references this experiment.',
        'Append a log entry — one line per session is enough to keep the record contemporaneous.');
    } else if (gap > 30) {
      finding('medium', 'ex-stale', 'Evidence capture going stale', ex.id,
        `Last evidence-log entry ${last} — ${gap} days ago.`,
        'Log what has happened since, or move the experiment to complete/abandoned.');
    } else if (gap > 14) {
      finding('low', 'ex-stale', 'Evidence capture slowing', ex.id,
        `Last evidence-log entry ${last} — ${gap} days ago.`,
        'Append an entry this week to stay inside the 14-day capture rhythm.');
    }
  }
  for (const mid of arr(ex.linked_milestones)) {
    const m = milestones[shortId(mid)];
    if (m && (s(m.status) === 'planned' || Number(m.percent_complete) === 0)) {
      finding('medium', 'anchor-mismatch', 'Anchored to a milestone that has not started', `${ex.id} → ${shortId(mid)}`,
        `${shortId(mid)} is ${s(m.status) || 'planned'} at ${Number(m.percent_complete) || 0}% while ${ex.id} cites dated work.`,
        'Update the milestone to reflect the work, or re-point the experiment.');
    }
  }
}

for (const a of advs) {
  if (arr(a.linked_experiments).length === 0) {
    finding('high', 'adv-no-ex', 'Advancement with no experimental basis', a.id,
      'Section G claim with nothing in Section F beneath it.', 'Link the experiments whose results support this advancement.');
  }
  if (!s(a.linked_tu)) {
    finding('high', 'adv-no-tu', 'Advancement with no uncertainty', a.id,
      'The chain does not reach back to a declared uncertainty.', 'Link the TU this advancement resolves.');
  }
}

if (exs.length > 0 && advs.length === 0) {
  finding('high', 'no-adv-at-all', 'Section G is empty', '—',
    `${exs.length} experiments recorded, no technological advancement claimed anywhere.`,
    'Either record advancements proportionate to the results already observed, or note deliberately that none is yet claimable.');
}

// counter drift between state/sred.json and the files on disk
const declared = stateSred?.counters || null;
const actual = { tu: tus.length, ex: exs.length, adv: advs.length };
const drift = declared
  ? Object.keys(actual).filter((k) => Number(declared[k] ?? -1) !== actual[k])
  : [];
if (drift.length) {
  finding('medium', 'counter-drift', 'State counters drifted from the files on disk', 'state/sred.json',
    drift.map((k) => `${k}: declared ${declared[k]} · on disk ${actual[k]}`).join(' · '),
    'Reconcile state/sred.json — downstream deadline and digest logic reads these counters.');
}

const sevRank = { high: 0, medium: 1, low: 2 };
findings.sort((a, b) => sevRank[a.severity] - sevRank[b.severity] || a.code.localeCompare(b.code));

// ── advisor-handoff gates ──────────────────────────────────────────────────
const gates = [];
const gate = (label, clear, detail) => gates.push({ label, clear, detail });

gate('Innovation criteria reviewed', s(criteria?.status) === 'reviewed',
  criteria ? `sred/criteria.yaml is ${s(criteria.status) || 'unset'}${s(criteria.reviewed_by) ? ` · reviewed by ${s(criteria.reviewed_by)}` : ''}` : 'No sred/criteria.yaml found');
gate('SR&ED advisor engaged', capSred?.advisor?.engaged === true,
  capSred?.advisor?.engaged === true ? s(capSred.advisor.contact) || 'engaged' : 'No qualified advisor named in the manifest — nothing here is an eligibility determination');
gate('Every uncertainty has an experiment', tus.length > 0 && tus.every((t) => exsForTu(t.id).length > 0),
  `${tus.filter((t) => exsForTu(t.id).length > 0).length} of ${tus.length} uncertainties have at least one linked experiment`);
gate('Every experiment cites evidence', exs.length > 0 && exs.every((e) => arr(e.evidence_records).length > 0),
  `${exs.filter((e) => arr(e.evidence_records).length > 0).length} of ${exs.length} experiments cite contemporaneous records`);
gate('Section G has a claim', advs.length > 0,
  advs.length ? `${advs.length} advancement${advs.length === 1 ? '' : 's'} recorded` : 'No advancement recorded — correct only while the core hypotheses stay untested');
gate('Effort from prospective time records', !effortBasis,
  effortBasis ? `Current figures are reconstruction: ${s(effortBasis.title)}` : 'No reconstruction basis on file');
gate('Evidence candidates all confirmed', inbox.length === 0,
  inbox.length ? `${inbox.length} unconfirmed candidate${inbox.length === 1 ? '' : 's'} in sred/inbox/` : 'sred/inbox/ is empty');

// unresolved annotations the manifest itself carries on the claim identity
const manifestFlags = [];
{
  // A trailing `#` note plus any pure-comment lines that continue it form one
  // block belonging to the key on the first line. Flag blocks that still carry
  // an unresolved annotation — the claim identity is not the substrate's to settle.
  const lines = manifestRaw.split(/\r?\n/);
  let inSred = false, sredIndent = 0, cur = null;
  const flush = () => {
    if (cur && /\b(ASSUMED|CONFIRM|TODO|UNCONFIRMED)\b/i.test(cur.note)) manifestFlags.push(cur);
    cur = null;
  };
  for (const line of lines) {
    const ind = line.match(/^(\s*)/)[1].length;
    if (/^\s*sred:\s*$/.test(line)) { inSred = true; sredIndent = ind; continue; }
    if (inSred && line.trim() && ind <= sredIndent && !/^\s*#/.test(line)) { flush(); inSred = false; }
    if (!inSred) continue;
    if (/^\s*#/.test(line)) { if (cur) cur.note += ' ' + line.replace(/^\s*#\s?/, '').trim(); continue; }
    const hash = line.indexOf('#');
    const key = (line.match(/^\s*([\w.-]+)\s*:/) || [])[1] || null;
    flush();
    if (hash !== -1) cur = { key, note: line.slice(hash + 1).trim() };
  }
  flush();
}
if (manifestFlags.length) {
  gate('Claim identity confirmed', false,
    manifestFlags.map((f) => (f.key ? f.key + ': ' : '') + f.note).join(' · '));
}

// ── deadlines ──────────────────────────────────────────────────────────────
const fyEntries = Object.entries(stateSred?.fiscal_years || {}).map(([fy, v]) => {
  const toHard = v.hard_deadline ? daysBetween(asOf, v.hard_deadline) : null;
  const toTarget = v.target_date ? daysBetween(asOf, v.target_date) : null;
  const tier = toHard === null ? 'none' : toHard < 0 ? 'forfeit' : toHard <= 90 ? 'crit' : toHard <= 180 ? 'warn' : 'ok';
  // The rail runs the whole life of the claim: first day of the fiscal year to the
  // statutory deadline, so "where are we" is legible before the year has even closed.
  let railStart = null;
  if (v.fy_end) {
    const d = new Date(Date.parse(v.fy_end + 'T00:00:00Z'));
    d.setUTCFullYear(d.getUTCFullYear() - 1);
    d.setUTCDate(d.getUTCDate() + 1);
    railStart = d.toISOString().slice(0, 10);
  }
  const span = railStart && v.hard_deadline ? daysBetween(railStart, v.hard_deadline) : null;
  const pct = (d) => (span && d ? Math.max(0, Math.min(100, (daysBetween(railStart, d) / span) * 100)) : null);
  const gone = v.fy_end ? daysBetween(v.fy_end, asOf) : null;
  return {
    fy, ...v, daysToHard: toHard, daysToTarget: toTarget, tier, railStart,
    pctToday: pct(asOf), pctFyEnd: pct(v.fy_end), pctTarget: pct(v.target_date),
    fyEnded: gone !== null && gone >= 0,
    escalation: arr(v.escalation_tiers_fired),
  };
}).filter((f) => !['filed', 'waived', 'forfeited'].includes(s(f.claim_status)));

// ── chains, entities, effort ───────────────────────────────────────────────
const chains = tus.map((tu) => {
  const links = exsForTu(tu.id).map((ex) => ({ ex: ex.id, advs: advsForEx(ex.id).map((a) => a.id) }));
  const state = links.length === 0 ? 'broken'
    : links.every((l) => l.advs.length > 0) ? 'complete' : 'partial';
  return { tu: tu.id, links, state };
});

const entity = (e, kind) => ({
  kind, id: s(e.id), slug: s(e.slug), status: s(e.status) || null,
  claim_fy: s(e.claim_fy) || (s(e.fiscal_year) ? 'FY' + s(e.fiscal_year) : null),
  title: s(e.slug).replace(/-/g, ' '),
  narrative: [
    ['Uncertainty', s(e.uncertainty_statement)],
    ['Standard-practice gap', s(e.standard_practice_gap)],
    ['Hypothesis', s(e.hypothesis)],
    ['Method and trials', s(e.method_and_trials)],
    ['Observations and results', s(e.observations_and_results)],
    ['Advancement', s(e.advancement_statement)],
    ['Knowledge gained', s(e.knowledge_gained)],
    ['Limitations', s(e.limitations)],
    ['Resolution', s(e.resolution)],
    ['Capture note', s(e.capture_note)],
  ].filter(([, v]) => v).map(([k, v]) => [k, reflow(v)]),
  dates: [
    ['Identified', s(e.identified_date)], ['Work start', s(e.work_start_date)],
    ['Start', s(e.start_date)], ['End', s(e.end_date)], ['Established', s(e.established_date)],
  ].filter(([, v]) => v),
  linked_tu: s(e.linked_tu) || null,
  linked_experiments: arr(e.linked_experiments).map(s),
  linked_milestones: arr(e.linked_milestones).map(shortId).map((m) => ({
    id: m, status: s(milestones[m]?.status) || null,
    percent: milestones[m] ? Number(milestones[m].percent_complete) || 0 : null,
    title: s(milestones[m]?.title) || null,
  })),
  evidence_records: arr(e.evidence_records).map((r) => ({
    type: s(r?.type), reference: s(r?.reference), date: s(r?.date), description: s(r?.description),
  })),
  people: arr(e.people_involved).map((p) => ({ name: s(p?.name), role: s(p?.role), days: Number(p?.eligible_days) || 0 })),
  review_notes: arr(e.review_notes).map(s).filter(Boolean),
  days: kind === 'ex' ? exDays(e) : null,
  lastEvidence: kind === 'ex' ? lastEvidenceDate(e.id) : null,
  evidenceGap: kind === 'ex' ? (lastEvidenceDate(e.id) ? sinceAsOf(lastEvidenceDate(e.id)) : null) : null,
  logCount: evidenceFor(s(e.id), kind === 'tu' ? 'tu_id' : kind === 'ex' ? 'ex_id' : 'adv_id').length,
  figure: kind === 'ex' ? effortFigure(s(e.id)) : null,
});

const DATA = {
  meta: {
    generatedAt: new Date().toISOString(),
    asOf,
    generator: GENERATOR,
    facility: path.basename(FAC),
    projectName: s(manifest?.project?.name) || path.basename(FAC),
    projectLongName: s(manifest?.project?.long_name),
    claimant: s(capSred.claimant_org) || null,
    bn: s(capSred.claimant_bn) || null,
    fiscalYearEnd: s(capSred.fiscal_year_end) || null,
    capabilityVersion: s(capSred.version) || null,
    pack: s(capSred.pack) || null,
    fieldOfScience: s(capSred.field_of_science_default) || null,
    advisorEngaged: capSred?.advisor?.engaged === true,
    sredLead: (arr(manifest?.stakeholders).find((x) => /sred-lead/.test(s(x?.id)))?.contacts?.lead) || null,
    manifestFlags,
  },
  fiscalYears: fyEntries,
  counters: { declared, actual, drift },
  entities: {
    tu: tus.map((e) => entity(e, 'tu')),
    ex: exs.map((e) => entity(e, 'ex')),
    adv: advs.map((e) => entity(e, 'adv')),
  },
  chains,
  findings,
  gates,
  effort: effortBasis ? {
    id: s(effortBasis.id), title: s(effortBasis.title), created: s(effortBasis.created),
    method: reflow(effortBasis.method), limitations: reflow(effortBasis.limitations),
    supersession: reflow(effortBasis.supersession_policy),
    source: effortBasis.source || null,
    figures: arr(effortBasis.figures).map((f) => ({
      ex: s(f.ex), proportional_h: f.proportional_h ?? null, session_inclusive_h: f.session_inclusive_h ?? null,
      days: Number(f.eligible_days_recorded) || 0, note: s(f.note),
    })),
    advisorHeld: arr(effortBasis.advisor_held_candidates).map((c) => ({
      cluster: s(c.cluster), proportional_h: c.proportional_h ?? null, session_inclusive_h: c.session_inclusive_h ?? null,
    })),
  } : null,
  totals: {
    recordedDays: exs.reduce((n, e) => n + exDays(e), 0),
    evidenceEntries: evidence.length,
    backfilled: evidence.filter((e) => e.backfilled === true || /BACK-?FILL/i.test(s(e.description)) || /back-?fill/i.test(s(e.logged_by))).length,
  },
  evidence: evidence.map((e) => ({
    date: s(e.date), type: s(e.entry_type), tu: s(e.tu_id) || null, ex: s(e.ex_id) || null,
    adv: s(e.adv_id) || null, description: s(e.description), record: s(e.record_reference),
    recordType: s(e.record_type), milestone: s(e.milestone_id) || null, people: arr(e.people).map(s),
    backfilled: e.backfilled === true || /BACK-?FILL/i.test(s(e.description)) || /back-?fill/i.test(s(e.logged_by)),
  })),
  inbox: inbox.map((r) => ({
    file: s(r._file), date: s(r.date), description: reflow(r.description_draft),
    suggested: s(r.suggested_ex) || null, people: arr(r.people).map(s),
    source: s(r?.source?.surface), ref: s(r?.source?.ref), proposedBy: s(r.proposed_by),
  })),
  criteria: criteria ? {
    status: s(criteria.status), reviewedBy: s(criteria.reviewed_by) || null, lastRefreshed: s(criteria?.review?.last_refreshed) || null,
    areas: arr(criteria.candidate_uncertainty_areas).map((a) => ({
      id: s(a.id), label: s(a.label), tus: arr(a.linked_tus).map(s), milestones: arr(a.linked_milestones).map(s),
    })),
    routine: arr(criteria.declared_routine).map(s),
  } : null,
};

// ── render ─────────────────────────────────────────────────────────────────
const template = readText(path.join(HERE, 'dashboard.template.html'));
if (template === null) { console.error('dashboard.template.html not found next to the generator'); process.exit(1); }

const payload = JSON.stringify(DATA).replace(/</g, '\\u003c').replace(/[\u2028\u2029]/g, (c) => '\\u202' + (c.charCodeAt(0) === 0x2028 ? '8' : '9'));
const titleText = `${DATA.meta.projectName} SR&ED Status`;
let body = template
  .replace('<!--SRED_DATA-->', payload)
  .replace(/<!--SRED_TITLE-->/g, titleText.replace(/&/g, '&amp;'));

const out = opt.artifact ? body : [
  '<!doctype html>',
  '<html lang="en">',
  '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
  '<style>*,*::before,*::after{box-sizing:border-box}body{margin:0}</style>',
  '</head>',
  '<body>',
  body,
  '</body></html>',
].join('\n');

const outPath = path.resolve(opt.out || path.join(FAC, 'reports', 'adhoc', 'sred-dashboard.html'));
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, out);
if (opt.json) { fs.mkdirSync(path.dirname(path.resolve(opt.json)), { recursive: true }); fs.writeFileSync(path.resolve(opt.json), JSON.stringify(DATA, null, 2)); }

const sev = (k) => findings.filter((f) => f.severity === k).length;
console.log(`sred-dashboard → ${outPath}`);
console.log(`  as of ${asOf} · ${tus.length} TU · ${exs.length} EX · ${advs.length} ADV · ${evidence.length} evidence entries`);
console.log(`  findings: ${sev('high')} high · ${sev('medium')} medium · ${sev('low')} low · gates clear ${gates.filter((g) => g.clear).length}/${gates.length}`);
