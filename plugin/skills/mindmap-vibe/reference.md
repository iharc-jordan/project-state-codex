# mindmap-vibe reference

## Studio app

- Path: `~/Desktop/simple-minds.html`
- Inbox: `~/Desktop/mindmap-inbox/`
- Import: **Load Vibe**, **Import**, drag-drop `.json`, URL hash `#vibe=<base64url-json>`

## Alternate envelope (import also accepts)

```json
{ "vibeMindmap": { "format": "mindmap-vibe", ... } }
```

## Full canvas export (not needed for vibe)

MindMap Studio native save uses `nodes[]` with `parent`, `side`, `x`, `y`. The vibe format is preferred for generation — smaller and layout is automatic.

## open-in-studio.py

Encodes the vibe JSON into `#vibe=` and opens the default browser on macOS (`open`).

Run from the project-state repo root:

```bash
python3 skills/mindmap-vibe/scripts/open-in-studio.py ~/Desktop/mindmap-inbox/latest.vibe.json
```
