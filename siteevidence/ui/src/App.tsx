import { useEffect, useState } from 'react';
import type { JSX } from 'react';
import { bucketByOwner, dueLabel } from './labels';
import type { Rfi } from './labels';

async function get(path: string): Promise<any> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

const TODAY = '2026-10-08'; // frozen demo date, matches backend

export default function App(): JSX.Element {
  const [rfis, setRfis] = useState<Rfi[]>([]);
  const [weekly, setWeekly] = useState<any>(null);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    Promise.all([get('/api/rfis'), get('/report/weekly')])
      .then(([r, w]) => {
        setRfis(r);
        setWeekly(w);
      })
      .catch((e) => setMsg(String(e)));
  }, []);

  const buckets = bucketByOwner(rfis);

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 900, margin: '0 auto', padding: 16 }}>
      <h1>SiteEvidence (demo — fictional site, no real data)</h1>
      {msg && <p><b>{msg}</b></p>}
      <h2>RFIs</h2>
      <ul>
        {rfis.map((r) => (
          <li key={r.id}>
            <b>{r.id}</b> {r.title} ({r.owner}, rev {r.rev}) — {dueLabel(r.status, r.due, TODAY)}
          </li>
        ))}
      </ul>
      <h2>Open by owner</h2>
      <ul>
        {Object.entries(buckets).map(([o, n]) => (
          <li key={o}>{o}: {n}</li>
        ))}
      </ul>
      <h2>Weekly gaps</h2>
      {weekly && (
        <ul>
          <li>Overdue: {weekly.overdue.join(', ') || 'none'}</li>
          <li>Missing evidence: {weekly.missing_evidence.join(', ') || 'none'}</li>
          <li>Mismatches: {weekly.mismatches.map((m: any) => `${m.inspection}(rev ${m.tested} vs ${m.current})`).join(', ') || 'none'}</li>
        </ul>
      )}
    </div>
  );
}
