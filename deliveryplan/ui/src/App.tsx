import { useEffect, useState } from 'react';
import type { JSX } from 'react';
import { driftLabel, groupByStatus } from './view';
import type { Task } from './view';

interface Milestone {
  name: string;
  planned: string;
  prereqs: string[];
  exit: string;
}
interface RaidRow {
  id: string;
  type: string;
  text: string;
  owner: string;
  rating: string;
}

async function get(path: string): Promise<any> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

export default function App(): JSX.Element {
  const [tasks, setTasks] = useState<Record<string, Task>>({});
  const [drift, setDrift] = useState<Record<string, any>>({});
  const [raid, setRaid] = useState<RaidRow[]>([]);
  const [weekly, setWeekly] = useState<any>(null);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    Promise.all([get('/api/tasks'), get('/reports/milestones'), get('/raid'), get('/reports/weekly')])
      .then(([t, d, r, w]) => {
        setTasks(t);
        setDrift(d);
        setRaid(r);
        setWeekly(w);
      })
      .catch((e) => setMsg(String(e)));
  }, []);

  const groups = groupByStatus(Object.keys(tasks), tasks);

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 900, margin: '0 auto', padding: 16 }}>
      <h1>DeliveryPlan (demo — synthetic launch, no live data)</h1>
      {msg && <p><b>{msg}</b></p>}
      <h2>Board</h2>
      {Object.entries(groups).map(([s, ids]) => (
        <div key={s}>
          <h3>{s} ({ids.length})</h3>
          <ul>
            {ids.map((id) => (
              <li key={id}>#{id} {tasks[id].title} [{tasks[id].team}/{tasks[id].owner}]</li>
            ))}
          </ul>
        </div>
      ))}
      <h2>Milestones</h2>
      <ul>
        {Object.entries(drift).map(([id, d]: [string, any]) => (
          <li key={id}>
            {id}: drift <b>{driftLabel(d.drift_days)}</b> (planned {d.planned})
          </li>
        ))}
      </ul>
      <h2>RAID</h2>
      <ul>
        {raid.map((r) => (
          <li key={r.id}>[{r.type}/{r.rating}] {r.text} — {r.owner}</li>
        ))}
      </ul>
      <h2>Weekly</h2>
      {weekly && <p>{weekly.narrative}</p>}
    </div>
  );
}
