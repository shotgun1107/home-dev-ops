// Installed read-only daemon/PID paths, synthetic files, process.kill stub only.
// Never acquire/release a real lock, start/stop anything, or send any signal.
import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile, rm, readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const base = '/usr/local/lib/node_modules/@getpaseo/cli/node_modules/@getpaseo/server/dist/server/server';
const sources = [
  {path: join(base, 'pid-lock.js'), sha256: '7ad798710140a3a831974637cacc0eff40f0403fbd583e307a2b68dc8947c02b'},
  {path: join(base, 'daemon-instance.js'), sha256: '029dea3bd91af1295dddb1427f152648657ad43efa1bd097894db901d0832cb9'},
];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
for (const source of sources) assert.equal(hash(await readFile(source.path)), source.sha256);
const { isPidLockOwnerRunning, isSamePidLock } = await import(pathToFileURL(sources[0].path));
const { readDaemonInstance } = await import(pathToFileURL(sources[1].path));
const root = await mkdtemp('/tmp/k12-recovery-pid-node-');
const observations = [];
const info = () => ({ pid: 900001, startedAt: new Date().toISOString(), hostname: 'synthetic',
  uid: 12345, listen: null });
const path = join(root, 'paseo.pid');
async function probe(lock, code) {
  await writeFile(path, JSON.stringify(lock));
  const original = process.kill; let calls = 0;
  process.kill = (pid, signal) => {
    assert.equal(pid, 900001); assert.equal(signal, 0); calls++;
    if (code) throw Object.assign(new Error('synthetic'), { code });
    return true;
  };
  try {
    return { instance: await readDaemonInstance(root), calls: () => calls };
  } finally { process.kill = original; }
}
function check(name, fn) {
  test(name, { timeout: 3000 }, async () => observations.push({ scenario: name, ...await fn() }));
}

check('ESRCH-hidden-or-gone-preserves-lock', async () => {
  const lock = info(); const r = await probe(lock, 'ESRCH'); assert.equal(r.instance, null);
  assert.deepEqual(JSON.parse(await readFile(path)), lock); assert.equal(r.calls(), 1);
  return { instance: null, lockPreserved: true, hostLivenessInferred: false };
});
check('EPERM-counts-as-visible-not-daemon-identity', async () => {
  const lock = info(); const r = await probe(lock, 'EPERM'); assert.deepEqual(r.instance, lock);
  return { instanceReturned: true, realPermissionChanged: false };
});
check('other-probe-error-is-not-visible', async () => {
  const r = await probe(info(), 'EACCES'); assert.equal(r.instance, null); return { instance: null };
});
check('preboot-stale-lock-ignores-reused-pid', async () => {
  const lock = { ...info(), startedAt: '1970-01-01T00:00:00Z' };
  const r = await probe(lock); assert.equal(r.instance, null); assert.equal(r.calls(), 0);
  assert.deepEqual(JSON.parse(await readFile(path)), lock); return { pidProbes: 0, lockPreserved: true };
});
check('same-boot-reused-pid-cannot-prove-owner', async () => {
  const lock = info(); const r = await probe(lock); assert.deepEqual(r.instance, lock);
  return { instanceReturned: true, processIdentityVerified: false };
});
check('same-pid-different-start-stamp-is-replaced', async () => {
  const lock = info(); assert.equal(isSamePidLock(lock, { ...lock, startedAt: 'different' }), false);
  assert.equal(isSamePidLock(lock, { ...lock }), true); return { stampCompared: true };
});
check('invalid-time-stamp-does-not-prove-current-boot', async () => {
  const r = await probe({ ...info(), startedAt: 'invalid-time' }); assert.ok(r.instance);
  return { acceptedByInstalledSchema: true, processIdentityVerified: false };
});
check('truncated-lock-bounded-read-error-preserves-bytes', async () => {
  const raw = '{"pid":'; await writeFile(path, raw);
  const original = process.kill; process.kill = () => { throw new Error('unexpected probe'); };
  try { await assert.rejects(readDaemonInstance(root), error => error.code === 'DAEMON_STATE_READ_FAILED'); }
  finally { process.kill = original; }
  assert.equal(await readFile(path, 'utf8'), raw); return { errorCode: 'DAEMON_STATE_READ_FAILED', lockPreserved: true };
});
check('missing-synthetic-lock-does-not-create-state', async () => {
  // Only remove the single file made by this suite, never a real PID lock.
  await rm(path); const original = process.kill; process.kill = () => { throw new Error('unexpected probe'); };
  try { assert.equal(await readDaemonInstance(root), null); } finally { process.kill = original; }
  assert.deepEqual(await readdir(root), []); return { createdState: false };
});

after(async () => {
  assert.equal(observations.length, 9);
  for (const source of sources) assert.equal(hash(await readFile(source.path)), source.sha256);
  await rm(root, { recursive: true }); // this new task fixture only
  console.log('K12_RECOVERY_PID_RESULT ' + JSON.stringify({ node: process.version, sources, observations,
    realSignals: 0, realServiceActions: 0, realCredentialReads: 0, fixtureRemoved: true }));
});
