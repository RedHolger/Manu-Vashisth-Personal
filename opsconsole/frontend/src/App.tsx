import { useEffect, useState } from 'react';
import type { JSX } from 'react';
import { api, actWithRetry, getRole, setRole } from './api';
import { can, cancelAllowed, retryAllowed } from './auth';
import { clampPage, totalPages } from './paging';
import type { Incident, Job, Role } from './types';

export default function App(): JSX.Element {
  const [role, setRoleState] = useState<Role>('viewer');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [detail, setDetail] = useState<Job | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [msg, setMsg] = useState('');

  const perPage = 5;
  const pages = totalPages(total, perPage);

  async function loadJobs(p: number, s: string): Promise<void> {
    try {
      const r = await api.jobs(p, s);
      setJobs(r.items);
      setTotal(r.total);
      setPage(clampPage(p, r.total, perPage));
    } catch (e) {
      setMsg(String(e));
    }
  }

  useEffect(() => {
    setRole(role);
    loadJobs(1, status).catch(() => undefined);
    api.incidents().then((r) => setIncidents(r.items)).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role]);

  async function act(kind: 'retry' | 'cancel', job: Job): Promise<void> {
    try {
      const { body: r, retried } = await actWithRetry(kind, job.id, job.version);
      setDetail(r.job);
      setMsg(`${kind} ok (version now ${r.job.version})${retried ? ' — retried once on ambiguous outcome' : ''}`);
      loadJobs(page, status).catch(() => undefined);
    } catch (e) {
      setMsg(String(e));
    }
  }

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 900, margin: '0 auto', padding: 16 }}>
      <h1>OpsConsole (demo — synthetic data, no live services)</h1>
      <label>
        Role:{' '}
        <select value={role} onChange={(e) => setRoleState(e.target.value as Role)}>
          <option value="viewer">viewer</option>
          <option value="operator">operator</option>
          <option value="admin">admin</option>
        </select>
      </label>
      {msg && <p><b>{msg}</b></p>}
      <h2>Jobs</h2>
      <label>
        Status:{' '}
        <select value={status} onChange={(e) => { setStatus(e.target.value); loadJobs(1, e.target.value); }}>
          <option value="">all</option>
          <option value="failed">failed</option>
          <option value="running">running</option>
          <option value="queued">queued</option>
          <option value="done">done</option>
          <option value="canceled">canceled</option>
        </select>
      </label>
      <ul>
        {jobs.map((j) => (
          <li key={j.id}>
            <button onClick={() => api.job(j.id).then(setDetail).catch((e) => setMsg(String(e)))}>
              #{j.id} {j.name}
            </button>{' '}
            [{j.status}] v{j.version} runs={j.runs.length}
          </li>
        ))}
      </ul>
      <p>
        Page {page}/{pages}{' '}
        <button disabled={page <= 1} onClick={() => loadJobs(page - 1, status)}>prev</button>{' '}
        <button disabled={page >= pages} onClick={() => loadJobs(page + 1, status)}>next</button>
      </p>
      {detail && (
        <div>
          <h3>Job #{detail.id} {detail.name}</h3>
          <p>Status {detail.status}, version {detail.version}</p>
          <button
            disabled={!can(role, 'retry') || !retryAllowed(detail.status)}
            onClick={() => act('retry', detail)}
          >
            Retry (operator+, failed only)
          </button>{' '}
          <button
            disabled={!can(role, 'cancel') || !cancelAllowed(detail.status)}
            onClick={() => act('cancel', detail)}
          >
            Cancel (operator+, queued/running)
          </button>
        </div>
      )}
      <h2>Incidents</h2>
      <ul>
        {incidents.map((i) => (
          <li key={i.id}>[{i.severity}] {i.title} — actions: {i.actions.join('; ') || 'none'}</li>
        ))}
      </ul>
      <p>Viewer is read-only; mutations need operator; audit view needs admin (API-enforced).</p>
    </div>
  );
}
