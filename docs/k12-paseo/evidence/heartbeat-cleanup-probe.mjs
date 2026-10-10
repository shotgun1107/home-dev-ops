// Isolated replay of the installed Paseo 0.10.3 schedule lifecycle.
// Does not connect to the daemon or call start(); runner is a local stub.
// The newly created /tmp fixture is retained. No existing data is removed.
import { ScheduleService } from '/usr/local/lib/node_modules/@getpaseo/cli/node_modules/@getpaseo/server/dist/server/server/schedule/service.js';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const root = await mkdtemp(join(tmpdir(), 'k12-heartbeat-lifecycle-'));
const logger = { child() { return this; }, error() {}, warn() {}, info() {}, debug() {} };
const agentId = '00000000-0000-4000-8000-000000000001';
const results = [];
for (const scenario of ['delete-during-run', 'delete-after-completion']) {
  const service = new ScheduleService({
    paseoHome: join(root, scenario), logger,
    runner: async (schedule) => {
      if (scenario === 'delete-during-run') await service.delete(schedule.id);
      return { agentId, output: 'isolated fixture result' };
    },
  });
  const schedule = await service.create({
    name: 'local fixture', prompt: 'local fixture, no provider',
    cadence: { type: 'cron', expression: '* * * * *', timezone: 'Asia/Seoul' },
    target: { type: 'agent', agentId }, maxRuns: 1,
  });
  let error = null;
  try { await service.runSchedule(schedule, new Date()); }
  catch (exception) { error = exception.message.replace(schedule.id, '<fixture-id>'); }
  const after = await service.store.get(schedule.id);
  if (scenario === 'delete-after-completion') await service.delete(schedule.id);
  results.push({
    scenario, error,
    statusBeforeCleanup: after?.status ?? null,
    runStatuses: after?.runs.map(run => run.status) ?? [],
    removedAfterCleanup: (await service.store.get(schedule.id)) === null,
    runningSetCleared: !service.runningScheduleIds.has(schedule.id),
  });
}
console.log(JSON.stringify({
  observedAt: new Date().toISOString(), node: process.version,
  source: '/usr/local/lib/node_modules/@getpaseo/cli/node_modules/@getpaseo/server/dist/server/server/schedule/service.js',
  fixtureRoot: root, daemonConnected: false, providerStarted: false, results,
}, null, 2));
if (results[0].error !== 'Schedule not found: <fixture-id>' ||
    results[1].error !== null || results[1].runStatuses[0] !== 'succeeded' ||
    !results.every(result => result.removedAfterCleanup && result.runningSetCleared)) {
  process.exitCode = 1;
}
