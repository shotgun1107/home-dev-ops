// K12-only integration regression: installed scheduler + an uninstalled patch.
// Synthetic homes, injected time, runner/agent stubs. Never call service.start(),
// a daemon/CLI API, a provider, auth, or an existing schedule. No real sleep.
import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const base = '/usr/local/lib/node_modules/@getpaseo/cli/node_modules/@getpaseo/server/dist/server/server';
const sourcePath = join(base, 'schedule/service.js');
const source = await readFile(sourcePath, 'utf8');
const hash = text => createHash('sha256').update(text).digest('hex');
assert.equal(hash(source), '325066fba80c259ed0f5385042f15045820791fe048e622151259ed036dcd3c6',
  'Installed scheduler changed: review the source and patch before replay');
const root = await mkdtemp('/tmp/k12-heartbeat-night-');
const patchPath = resolve(dirname(fileURLToPath(import.meta.url)),
  '../docs/k12-paseo/proposals/paseo-heartbeat-schedule.patch');
const observations = [];
let serial = 0;
const fixtureAgent = '00000000-0000-4000-8000-000000000001';
const logger = Object.fromEntries(['trace', 'debug', 'info', 'warn', 'error'].map(k => [k, () => {}]));
logger.child = () => logger;

// Apply only to a new disposable copy; preserve the installed file byte-for-byte.
await writeFile(join(root, 'service.js'), source);
execFileSync('git', ['apply', '--no-index', patchPath], { cwd: root, timeout: 5000, stdio: 'pipe' });
const patched = await readFile(join(root, 'service.js'), 'utf8');
const importable = patched.replace(/from "(\.[^"]+)"/g,
  (_, relative) => `from ${JSON.stringify(pathToFileURL(resolve(dirname(sourcePath), relative)).href)}`);
await writeFile(join(root, 'candidate.mjs'), importable);
const { ScheduleService: Installed } = await import(pathToFileURL(sourcePath).href);
const { ScheduleService: Candidate } = await import(pathToFileURL(join(root, 'candidate.mjs')).href);

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

async function fixture(Service, overrides = {}) {
  const home = join(root, `case-${++serial}`);
  await mkdir(home);
  let time = new Date('2026-10-09T13:08:05.164Z');
  const config = {
    paseoHome: home, logger, now: () => new Date(time),
    runner: async () => ({ agentId: fixtureAgent, output: 'synthetic result' }),
    createAgent: () => { throw new Error('forbidden-new-provider'); },
    archiveWorkspace: () => { throw new Error('forbidden-archive'); },
    ...overrides,
  };
  const service = new Service(config);
  service.start = () => { throw new Error('forbidden-scheduler-start'); };
  return { service, home, setTime: next => { time = new Date(next); }, now: () => new Date(time),
    create: input => service.create({ name: 'synthetic heartbeat', prompt: 'synthetic only',
      cadence: { type: 'cron', expression: '*/20 * * * *', timezone: 'Asia/Seoul' },
      target: { type: 'agent', agentId: fixtureAgent }, maxRuns: 72, ...input }) };
}

function running(schedule) {
  return { id: randomUUID(), scheduledFor: schedule.nextRunAt, startedAt: schedule.nextRunAt,
    endedAt: null, status: 'running', agentId: null, output: null, error: null };
}

function fakeAgent({ busy = false, permission = false, gone = false } = {}) {
  const state = { starts: 0, permissionPending: permission };
  const agent = { id: fixtureAgent, provider: 'synthetic' };
  return { state,
    agentStorage: { get: async () => gone ? null : { archivedAt: null } },
    agentManager: {
      getAgent: () => agent, hasInFlightRun: () => busy, tryRunOutOfBand: () => false,
      steerOrReplaceActiveTurn: async () => ({ status: 'no_active_run' }),
      streamAgent: async function* () { state.starts++; },
      waitForAgentEvent: async () => ({ status: 'idle', permission: permission ? {} : null, lastMessage: 'synthetic result' }),
    },
  };
}

for (const [variant, Service] of [['installed', Installed], ['candidate', Candidate]]) {
  const check = (name, fn) => test(`${variant}: ${name}`, { timeout: 5000 }, async () => {
    const data = await fn();
    observations.push({ variant, scenario: name, ...data });
  });

  check('24h-cron-72-terminal-runs', async () => {
    const f = await fixture(Service);
    const expiresAt = new Date(f.now().getTime() + 86400000).toISOString();
    let s = await f.create({ expiresAt });
    for (let i = 0; i < 72; i++) {
      assert.equal(s.status, 'active'); f.setTime(s.nextRunAt); await f.service.tick();
      s = await f.service.inspect(s.id);
    }
    assert.equal(s.status, 'completed'); assert.equal(s.runs.length, 72);
    assert.equal(new Set(s.runs.map(r => r.scheduledFor)).size, 72);
    assert.ok(s.runs.every(r => r.status === 'succeeded'));
    f.setTime(expiresAt); await f.service.tick();
    assert.equal((await f.service.inspect(s.id)).runs.length, 72);
    return { terminalRuns: 72, distinctScheduledSlots: 72, virtualHours: 24, real24hObservation: false };
  });

  check('aligned-24h-expiry-excludes-boundary-slot', async () => {
    const f = await fixture(Service); f.setTime('2026-10-09T13:00:00Z');
    let s = await f.create({ expiresAt: '2026-10-10T13:00:00Z' });
    for (let i = 0; i < 72; i++) { f.setTime(s.nextRunAt); await f.service.tick(); s = await f.service.inspect(s.id); }
    assert.equal(s.status, 'completed'); assert.equal(s.runs.length, 71);
    return { terminalRuns: 71, reason: 'expiry checked before equal-time dispatch' };
  });

  check('expiry-at-first-tick-no-dispatch', async () => {
    let calls = 0;
    const f = await fixture(Service, { runner: async () => { calls++; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create({ expiresAt: '2026-10-09T13:20:00Z' });
    f.setTime(s.nextRunAt); await f.service.tick();
    assert.equal(calls, 0); assert.equal((await f.service.inspect(s.id)).status, 'completed');
    return { runnerCalls: calls };
  });

  check('expiry-does-not-cancel-running-job', async () => {
    const entered = deferred(), release = deferred();
    const f = await fixture(Service, { runner: async () => { entered.resolve(); await release.promise; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create({ expiresAt: '2026-10-09T13:21:00Z' });
    f.setTime(s.nextRunAt); const active = f.service.tick(); await entered.promise;
    f.setTime('2026-10-09T15:00:00Z'); await f.service.tick();
    const mid = await f.service.inspect(s.id);
    release.resolve(); await active;
    const end = await f.service.inspect(s.id);
    assert.equal(mid.status, 'active'); assert.equal(mid.runs[0].status, 'running');
    assert.equal(end.status, 'completed'); assert.equal(end.runs[0].status, 'succeeded');
    assert.ok(new Date(end.runs[0].endedAt) > new Date(s.expiresAt));
    return { afterExpiryWhileHeld: mid.status, afterRelease: end.status, hardStop: false };
  });

  check('active-agent-rejection-consumes-maxRuns', async () => {
    const fake = fakeAgent({ busy: true });
    const f = await fixture(Service, { ...fake, runner: undefined });
    let s = await f.create({ maxRuns: 2 });
    for (let i = 0; i < 2; i++) { f.setTime(s.nextRunAt); await f.service.tick(); s = await f.service.inspect(s.id); }
    assert.equal(s.status, 'completed'); assert.ok(s.runs.every(r => r.status === 'failed' && r.error.includes('already has an active run')));
    assert.equal(fake.state.starts, 0);
    return { failedRuns: s.runs.length, providerStarts: fake.state.starts, status: s.status };
  });

  check('permission-wait-fails-schedule-not-agent-cleanup', async () => {
    const fake = fakeAgent({ permission: true });
    const f = await fixture(Service, { ...fake, runner: undefined });
    const s = await f.create({ maxRuns: 1 }); f.setTime(s.nextRunAt); await f.service.tick();
    const end = await f.service.inspect(s.id);
    assert.equal(fake.state.starts, 1, end.runs[0].error); assert.equal(end.runs[0].status, 'failed');
    assert.ok(end.runs[0].error.includes('waiting for permission'));
    assert.equal(end.status, 'completed'); assert.equal(fake.state.permissionPending, true);
    return { stubStarts: 1, scheduleStatus: end.status, stubPermissionStillPending: true };
  });

  check('crash-recovery-skips-missed-slots-and-is-idempotent', async () => {
    const f = await fixture(Service); const s = await f.create({ maxRuns: 1 });
    f.setTime(s.nextRunAt);
    assert.ok(await f.service.appendRunningRun(s.id, running(s)));
    // New object over synthetic persisted state; no daemon restart or killed process.
    let calls = 0;
    const restored = new Service({ paseoHome: f.home, logger, now: () => new Date('2026-10-09T15:05:00Z'),
      runner: async () => { calls++; return { agentId: fixtureAgent, output: null }; } });
    await restored.recoverInterruptedRuns();
    const recovered = await restored.inspect(s.id);
    assert.equal(recovered.runs[0].status, 'failed'); assert.equal(recovered.nextRunAt, '2026-10-09T15:20:00.000Z');
    await restored.recoverInterruptedRuns(); assert.deepEqual(await restored.inspect(s.id), recovered);
    await restored.tick(); assert.equal((await restored.inspect(s.id)).status, 'completed');
    assert.equal(calls, 0);
    return { recoveredRun: 'failed', missedSlotsReplayed: 0, idempotentRecovery: true, actualProcessCrash: false };
  });

  check('crash-after-side-effect-is-not-exactly-once', async () => {
    const f = await fixture(Service); const s = await f.create({ maxRuns: 2 });
    f.setTime(s.nextRunAt);
    assert.ok(await f.service.appendRunningRun(s.id, running(s)));
    const effect = join(f.home, 'synthetic-effect-count'); await writeFile(effect, '1');
    let clock = new Date('2026-10-09T13:25:00Z');
    const restored = new Service({ paseoHome: f.home, logger, now: () => clock,
      runner: async () => { await writeFile(effect, String(Number(await readFile(effect, 'utf8')) + 1)); return { agentId: fixtureAgent, output: null }; } });
    await restored.recoverInterruptedRuns(); clock = new Date((await restored.inspect(s.id)).nextRunAt); await restored.tick();
    const end = await restored.inspect(s.id);
    assert.equal(await readFile(effect, 'utf8'), '2'); assert.deepEqual(end.runs.map(r => r.status), ['failed', 'succeeded']);
    return { syntheticEffects: 2, statuses: end.runs.map(r => r.status), exactlyOnce: false };
  });

  check('overlapping-ticks-while-run-held', async () => {
    let calls = 0; const entered = deferred(), release = deferred();
    const f = await fixture(Service, { runner: async () => { calls++; entered.resolve(); await release.promise; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create({ maxRuns: 1 }); f.setTime(s.nextRunAt);
    const first = f.service.tick(); await entered.promise;
    await Promise.all(Array.from({ length: 8 }, () => f.service.tick()));
    release.resolve(); await first;
    assert.equal(calls, 1); assert.equal((await f.service.inspect(s.id)).runs.length, 1);
    return { overlappingTicks: 9, runnerCalls: calls };
  });

  check('stale-tick-snapshot-after-completion', async () => {
    let calls = 0;
    const f = await fixture(Service, { runner: async () => { calls++; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create({ maxRuns: 1 }); f.setTime(s.nextRunAt);
    const list = f.service.store.list.bind(f.service.store), captured = deferred(), release = deferred();
    let first = true;
    f.service.store.list = async () => { const items = await list(); if (first) { first = false; captured.resolve(); await release.promise; } return items; };
    const stale = f.service.tick(); await captured.promise; await f.service.tick(); release.resolve(); await stale;
    const end = await f.service.inspect(s.id);
    assert.equal(calls, variant === 'installed' ? 2 : 1); assert.equal(end.runs.length, calls);
    return { runnerCalls: calls, maxRuns: 1, uniqueSlots: new Set(end.runs.map(r => r.scheduledFor)).size,
      defectReproduced: variant === 'installed' };
  });

  check('stale-snapshot-after-pause', async () => {
    let calls = 0;
    const f = await fixture(Service, { runner: async () => { calls++; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create(); f.setTime(s.nextRunAt);
    const list = f.service.store.list.bind(f.service.store), captured = deferred(), release = deferred();
    f.service.store.list = async () => { const items = await list(); captured.resolve(); await release.promise; return items; };
    const stale = f.service.tick(); await captured.promise; await f.service.pause(s.id); release.resolve(); await stale;
    assert.equal(calls, variant === 'installed' ? 1 : 0);
    assert.equal((await f.service.inspect(s.id)).status, 'paused');
    return { runnerCallsAfterPause: calls, defectReproduced: variant === 'installed' };
  });

  check('append-storage-failure-releases-memory-guard', async () => {
    let calls = 0;
    const f = await fixture(Service, { runner: async () => { calls++; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create({ maxRuns: 1 }); f.setTime(s.nextRunAt);
    const update = f.service.store.update.bind(f.service.store); let fail = true;
    f.service.store.update = async (...args) => { if (fail) { fail = false; throw new Error('synthetic append failure'); } return update(...args); };
    await assert.rejects(f.service.tick(), /synthetic append failure/);
    const stuck = f.service.runningScheduleIds.has(s.id); await f.service.tick();
    assert.equal(stuck, variant === 'installed'); assert.equal(calls, variant === 'installed' ? 0 : 1);
    return { guardLeaked: stuck, runnerCallsAfterStorageRecovered: calls };
  });

  check('finish-storage-failure-leaves-orphan-running-record', async () => {
    let calls = 0, failedWrites = 0;
    const runner = async () => { calls++; return { agentId: fixtureAgent, output: null }; };
    const f = await fixture(Service, { runner });
    const s = await f.create({ maxRuns: null }); f.setTime(s.nextRunAt);
    assert.equal(s.expiresAt, null); assert.equal(s.maxRuns, null);
    const write = f.service.store.write.bind(f.service.store);
    f.service.store.write = async schedule => {
      if (schedule.runs.some(r => r.status !== 'running')) {
        failedWrites++; throw new Error('synthetic terminal storage failure');
      }
      return write(schedule);
    };
    await assert.rejects(f.service.tick(), /synthetic terminal storage failure/);
    assert.equal(failedWrites, 2); assert.equal(calls, 1);
    assert.equal(f.service.runningScheduleIds.has(s.id), false);
    f.service.store.write = write;
    for (const time of ['13:40', '14:00', '14:20']) {
      f.setTime(`2026-10-09T${time}:00Z`); await f.service.tick();
    }
    const orphaned = await f.service.inspect(s.id);
    assert.equal(orphaned.status, 'active'); assert.equal(orphaned.runs[0].status, 'running');
    assert.equal(calls, variant === 'installed' ? 4 : 1);
    assert.equal(orphaned.runs.length, calls);
    const afterStorageRecovery = calls;
    // Only a new object over this synthetic store; never restart the daemon.
    let clock = new Date('2026-10-09T15:05:00Z');
    const restored = new Service({ paseoHome: f.home, logger, now: () => clock, runner });
    await restored.recoverInterruptedRuns();
    const recovered = await restored.inspect(s.id);
    assert.equal(recovered.runs[0].status, 'failed');
    clock = new Date(recovered.nextRunAt); await restored.tick();
    assert.equal(calls, afterStorageRecovery + 1);
    assert.ok((await restored.inspect(s.id)).runs.every(r => r.status !== 'running'));
    return { terminalWritesFailed: failedWrites, memoryGuardCleared: true,
      callsAfterStorageRecoveryAndThreeTicks: afterStorageRecovery, orphanStatus: orphaned.runs[0].status,
      scheduleStatus: orphaned.status, candidateStalls: variant === 'candidate',
      syntheticRecoveryAllowsNextRun: true, actualProcessCrash: false };
  });

  check('deleted-snapshot-aborts-tick-but-next-tick-progresses', async () => {
    const calls = [];
    const f = await fixture(Service, { runner: async s => { calls.push(s.name); return { agentId: fixtureAgent, output: null }; } });
    const a = await f.create({ name: 'A', maxRuns: 1 }); f.setTime('2026-10-09T13:08:06Z');
    const b = await f.create({ name: 'B', maxRuns: 1 }); f.setTime(a.nextRunAt);
    const list = f.service.store.list.bind(f.service.store), captured = deferred(), release = deferred();
    f.service.store.list = async () => { const items = await list(); captured.resolve(); await release.promise; return items; };
    const stale = f.service.tick(); await captured.promise;
    await f.service.store.delete(a.id); release.resolve();
    await assert.rejects(stale, /Schedule not found/);
    assert.deepEqual(calls, []);
    const leaked = f.service.runningScheduleIds.has(a.id);
    assert.equal(leaked, variant === 'installed');
    await f.service.tick(); assert.deepEqual(calls, ['B']);
    assert.equal((await f.service.inspect(b.id)).status, 'completed');
    return { firstTickAborted: true, nextTickRunnerCalls: calls, deletedScheduleGuardLeaked: leaked };
  });

  check('expiry-elapses-between-list-and-claim', async () => {
    let calls = 0;
    const f = await fixture(Service, { runner: async () => { calls++; return { agentId: fixtureAgent, output: null }; } });
    const s = await f.create({ expiresAt: '2026-10-09T13:21:00Z' }); f.setTime(s.nextRunAt);
    const list = f.service.store.list.bind(f.service.store), captured = deferred(), release = deferred();
    f.service.store.list = async () => { const items = await list(); captured.resolve(); await release.promise; return items; };
    const stale = f.service.tick(); await captured.promise; f.setTime('2026-10-09T14:00:00Z'); release.resolve(); await stale;
    assert.equal(calls, variant === 'installed' ? 1 : 0);
    await f.service.tick(); assert.equal((await f.service.inspect(s.id)).status, 'completed');
    return { runnerCallsAfterExpiry: calls, freshClaimClockChecked: variant === 'candidate' };
  });

  check('independent-schedule-progress-without-global-tick-lock', async () => {
    const entered = deferred(), release = deferred(); const calls = { A: 0, B: 0 };
    const f = await fixture(Service, { runner: async schedule => { calls[schedule.name]++; if (schedule.name === 'A') { entered.resolve(); await release.promise; } return { agentId: fixtureAgent, output: null }; } });
    const a = await f.create({ name: 'A', maxRuns: 1 }); f.setTime('2026-10-09T13:08:06Z');
    await f.create({ name: 'B', maxRuns: 1, target: { type: 'agent', agentId: '00000000-0000-4000-8000-000000000002' } });
    f.setTime(a.nextRunAt); const first = f.service.tick(); await entered.promise;
    await f.service.tick(); const bWhileAHeld = calls.B; release.resolve(); await first;
    assert.equal(bWhileAHeld, 1); assert.equal(calls.A, 1); assert.equal(calls.B, variant === 'installed' ? 2 : 1);
    return { bWhileAHeld, finalRunnerCalls: calls, crossScheduleProgressPreserved: true };
  });

  check('manual-runOnce-is-not-an-expiry-or-cap-enforcer', async () => {
    const f = await fixture(Service); const s = await f.create({ maxRuns: 1, expiresAt: '2026-10-09T13:21:00Z' });
    f.setTime('2026-10-09T14:00:00Z'); await f.service.runOnce(s.id); await f.service.runOnce(s.id);
    const beforeTick = await f.service.inspect(s.id); assert.equal(beforeTick.runs.length, 2); assert.equal(beforeTick.status, 'active');
    await f.service.tick(); assert.equal((await f.service.inspect(s.id)).status, 'completed');
    return { manualRunsAfterExpiry: 2, maxRuns: 1, manualSemanticsUnchanged: true };
  });

  check('paused-expired-record-remains-paused', async () => {
    const f = await fixture(Service); const s = await f.create({ expiresAt: '2026-10-09T13:21:00Z' });
    await f.service.pause(s.id); f.setTime('2026-10-09T14:00:00Z'); await f.service.tick();
    const end = await f.service.inspect(s.id); assert.equal(end.status, 'paused'); assert.equal(end.runs.length, 0);
    return { statusAfterExpiry: end.status, runnerCalls: 0 };
  });

  check('missing-target-completes-without-starting-provider', async () => {
    const fake = fakeAgent({ gone: true }); const f = await fixture(Service, { ...fake, runner: undefined });
    const s = await f.create(); f.setTime(s.nextRunAt); await f.service.tick();
    const end = await f.service.inspect(s.id); assert.equal(end.status, 'completed'); assert.equal(end.runs[0].status, 'failed');
    assert.equal(fake.state.starts, 0); return { status: end.status, providerStarts: 0 };
  });
}

after(async () => {
  assert.equal(hash(await readFile(sourcePath, 'utf8')), hash(source), 'Installed source must remain unchanged');
  assert.equal(observations.length, 38, 'All bounded cases must finish');
  const sources = [];
  for (const name of ['service.js', 'store.js', 'cron.js']) {
    const path = join(base, 'schedule', name);
    sources.push({ path, sha256: hash(await readFile(path)) });
  }
  await rm(root, { recursive: true, force: true }); // only this mkdtemp fixture
  console.log('K12_HEARTBEAT_RESULT ' + JSON.stringify({ node: process.version, sources,
    patchSha256: hash(await readFile(patchPath)), candidateSourceSha256: hash(patched),
    daemonConnected: false, providersStarted: false, realSchedulesChanged: false,
    fixtureRemoved: true, real24hObservation: false, actualProcessCrash: false, observations }));
});
