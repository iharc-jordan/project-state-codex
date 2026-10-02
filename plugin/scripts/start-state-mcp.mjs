#!/usr/bin/env node
// Codex launch adapter. The checked state engine remains the upstream bundle.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const payload = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node start-state-mcp.mjs [--root <project or project-state directory>]');
  process.exit(0);
}
if (!process.env.PROJECT_STATE_CAPABILITIES_DIR) {
  process.env.PROJECT_STATE_CAPABILITIES_DIR = path.join(payload, 'capabilities');
}
// Use the explicit native binding when set; never inherit a third-party session directory.
delete process.env.CLAUDE_PROJECT_DIR;
const rootAt = args.indexOf('--root');
if (rootAt !== -1) {
  if (!args[rootAt + 1]) throw new Error('--root requires a directory');
  const supplied = path.resolve(args[rootAt + 1]);
  const found = [supplied, path.join(supplied, 'project-state'), path.join(supplied, '.project-state')]
    .find(dir => fs.existsSync(path.join(dir, 'manifest.yaml')));
  if (!found) throw new Error(`No project-state manifest in ${supplied}`);
  args[rootAt + 1] = found;
} else if (process.env.PROJECT_STATE_DIR) {
  const supplied = path.resolve(process.env.PROJECT_STATE_DIR);
  const found = [supplied, path.join(supplied, 'project-state'), path.join(supplied, '.project-state')]
    .find(dir => fs.existsSync(path.join(dir, 'manifest.yaml')));
  if (found) process.env.PROJECT_STATE_DIR = found;
}
process.argv = [process.argv[0], process.argv[1], ...args];
await import(new URL('../server/state-mcp-local.mjs', import.meta.url));
