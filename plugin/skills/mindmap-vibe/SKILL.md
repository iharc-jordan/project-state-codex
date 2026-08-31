---
name: mindmap-vibe
description: >-
  Generate a mindmap-vibe JSON from a user's idea and load it into MindMap Studio
  (~/Desktop/simple-minds.html). Writes to ~/Desktop/mindmap-inbox/, opens the
  studio in the browser, or returns a #vibe= share link. Trigger when the user
  says vibe mindmap, mind map from idea, mindmap studio, simple-minds, map this
  idea, brainstorm map, or wants a Cursor-generated map loaded into the desktop app.
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# MindMap Vibe (Cursor → MindMap Studio)

Generate structured mind maps from ideas inside Cursor and load them into **MindMap Studio** at `~/Desktop/simple-minds.html`.

## Workflow

1. **Clarify** — If the idea is vague, ask one short question (audience, goal, or depth). Otherwise proceed.
2. **Generate** — Produce a `mindmap-vibe` JSON (schema below). Aim for 1 root, 4–12 top-level branches, 2–5 children per branch where useful. Alternate `left` / `right` on top-level branches.
3. **Write** — Save to:
   - `~/Desktop/mindmap-inbox/latest.vibe.json` (always)
   - `~/Desktop/mindmap-inbox/<slug>.vibe.json` (named copy)
4. **Open** — Run the open script so the map appears in the browser:
   ```bash
   python3 skills/mindmap-vibe/scripts/open-in-studio.py ~/Desktop/mindmap-inbox/latest.vibe.json
   ```
   From outside the repo, use the personal install path:
   `python3 ~/.cursor/skills/mindmap-vibe/scripts/open-in-studio.py …`
5. **Tell the user** — Path saved, studio opened (or manual **Load Vibe** / drag-drop onto canvas if open failed).

## JSON schema (`mindmap-vibe`)

```json
{
  "format": "mindmap-vibe",
  "version": 1,
  "title": "Short central topic",
  "idea": "Optional one-line source prompt",
  "theme": "blueprint",
  "branches": [
    {
      "text": "Branch label",
      "side": "left",
      "children": [
        { "text": "Child node" },
        { "text": "Another child", "children": [{ "text": "Grandchild" }] }
      ]
    },
    {
      "text": "Right branch",
      "side": "right",
      "children": [{ "text": "Detail" }]
    }
  ]
}
```

Rules:
- `format` must be `"mindmap-vibe"`.
- `text` on every node; keep labels short (2–6 words).
- `side` only on top-level branches under root (`left` or `right`).
- Do **not** emit x/y coordinates — the app layouts automatically.
- Optional: `theme` (`blueprint` | `midnight` | `forest` | `sunset`), `connector` (`curve` | `elbow` | `straight` | `dashed` | `organic`).

## Slug helper

Derive `<slug>` from `title`: lowercase, alphanumeric + hyphens, max 40 chars.

## Manual load (if script fails)

User can in MindMap Studio: **Load Vibe** → pick `~/Desktop/mindmap-inbox/latest.vibe.json`, or drag the file onto the canvas.

## Full spec

See `docs/MINDMAP-VIBE.md` in the project-state repo (or `reference.md` in this skill folder).
