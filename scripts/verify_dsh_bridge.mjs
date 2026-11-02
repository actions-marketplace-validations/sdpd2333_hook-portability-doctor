#!/usr/bin/env node
/** Run the real bridge with a recording context; intercept shell execution before spawn. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { mkdir } from 'node:fs/promises';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { values } = parseArgs({ options: {
  modules: { type: 'string', default: path.join(root, 'integrations/dsh/node_modules') },
  out: { type: 'string', default: path.join(root, 'reports/dsh-contracts.json') },
}});
const requirePackage = createRequire(path.join(path.resolve(values.modules), '__probe__.cjs'));
const modulePath = requirePackage.resolve('@deepseek-ai/dsh-hooks-claude-code');
const bridge = await import(pathToFileURL(modulePath).href);
const packageInfo = requirePackage('@deepseek-ai/dsh-hooks-claude-code/package.json');
assert.equal(packageInfo.version, '0.2.1-rc.5', 'This probe is pinned to the documented package version.');
const work = path.join(root, '.work');
await mkdir(work, { recursive: true });
const temporary = await mkdtemp(path.join(work, 'bridge-contract-'));
assert.equal(path.dirname(temporary), work, 'Recursive cleanup stays inside this project .work directory.');
const results = [];
const group = (handler, matcher) => ({ hooks: [handler], ...(matcher === undefined ? {} : { matcher }) });

async function observe(hooks, event = 'PreToolUse', config = {}) {
  const file = path.join(temporary, 'hooks.json');
  await writeFile(file, JSON.stringify({ hooks }));
  const callbacks = new Map();
  const warnings = [];
  const requests = [];
  const cleanup = [];
  const ctx = {
    logger: { warn: message => warnings.push(message) },
    on: (name, callback) => callbacks.set(name, callback),
    effect: effect => cleanup.push(effect()),
    get: () => undefined,
    workingDirectory: { ensure: async () => temporary, get: () => temporary },
    shell: {
      resolve: request => {
        requests.push(request);
        // Deliberately stop at the service seam. This is not a shell execution test.
        throw new Error('HPD contract probe: shell invocation intercepted');
      },
    },
  };
  bridge.apply(ctx, { configPath: file, ...config });
  const signal = new AbortController().signal;
  if (event === 'PreToolUse' && callbacks.has('tools/pre-execute')) {
    await callbacks.get('tools/pre-execute')({ name: 'read', arguments: {}, callId: 'probe', signal }, async () => ({ kind: 'allow' }));
  } else if (event === 'Stop' && callbacks.has('agent/turn-stopping')) {
    await callbacks.get('agent/turn-stopping')({ agent: { session: { header: { id: 'probe' } } }, signal });
  }
  for (const dispose of cleanup) await dispose();
  return { requests, warnings, callbacks };
}

async function check(name, action) {
  await action();
  results.push({ name, passed: true });
}

try {
  await check('missing-type-defaults-to-command', async () => {
    const result = await observe({ PreToolUse: [group({ command: 'example' })] });
    assert.equal(result.requests.length, 1);
  });
  await check('nonstring-type-defaults-to-command', async () => {
    const result = await observe({ PreToolUse: [group({ type: null, command: 'example' })] });
    assert.equal(result.requests.length, 1);
  });
  await check('prompt-handler-is-skipped', async () => {
    const result = await observe({ PreToolUse: [group({ type: 'prompt', command: 'must-not-run' })] });
    assert.equal(result.requests.length, 0);
    assert.ok(result.warnings.some(w => w.includes('skipping unsupported')));
  });
  await check('unsupported-event-invalid-matcher-does-not-reject-config', async () => {
    const result = await observe({ PreCompact: [group({ command: 'must-not-run' }, '[')],
                                  PreToolUse: [group({ command: 'supported' })] });
    assert.equal(result.requests.length, 1);
    assert.equal(result.requests[0].command, 'supported');
    assert.equal(result.warnings.length, 0);
  });
  await check('invalid-supported-matcher-rejects-entire-config', async () => {
    const result = await observe({ PreToolUse: [group({ command: 'example' }, '[')],
                                  Stop: [group({ command: 'also-not-registered' })] });
    assert.equal(result.callbacks.size, 0);
    assert.ok(result.warnings.some(w => w.includes('no hooks registered')));
  });
  await check('stop-matcher-is-discarded-before-regex-validation', async () => {
    const result = await observe({ Stop: [group({ command: 'example' }, '[')] }, 'Stop');
    assert.equal(result.requests.length, 1);
  });
  await check('matcher-is-not-parsed-without-runnable-handlers', async () => {
    const result = await observe({ PreToolUse: [group({ type: 'prompt' }, '[')],
                                  Stop: [group({ command: 'example' })] }, 'Stop');
    assert.equal(result.requests.length, 1);
  });
  await check('root-substitution-args-and-timeout-contract', async () => {
    const result = await observe({ PreToolUse: [group({ command: 'run ${CLAUDE_PLUGIN_ROOT} ${CLAUDE_PROJECT_DIR}',
      args: ['not-appended'], shell: 'unused', async: true, timeout: 0.25 })] }, 'PreToolUse',
      { pluginRoot: 'PLUGIN', projectDir: 'PROJECT' });
    assert.equal(result.requests[0].command, 'run PLUGIN PROJECT');
    assert.equal(result.requests[0].timeoutMs, 250);
    assert.equal(result.requests[0].env.CLAUDE_PROJECT_DIR, 'PROJECT');
    assert.equal(JSON.parse(result.requests[0].stdin).hook_event_name, 'PreToolUse');
  });
  const report = { passed: true, package: packageInfo.name, version: packageInfo.version,
    module_sha256: createHash('sha256').update(await readFile(modulePath)).digest('hex'),
    node: process.version, platform: process.platform, checks: results,
    mode: 'real-bridge-recording-context-shell-intercepted', subprocess_execution_tested: false,
    installed_git_revision_known: false };
  await mkdir(path.dirname(path.resolve(values.out)), { recursive: true });
  await writeFile(values.out, JSON.stringify(report, null, 2) + '\n');
  console.log(`PASS: ${results.length} DSH bridge contracts; no model or shell commands executed`);
} finally {
  await rm(temporary, { recursive: true, force: true });
}
