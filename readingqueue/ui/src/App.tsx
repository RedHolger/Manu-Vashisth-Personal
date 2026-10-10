import { useEffect, useState } from 'react';
import type { JSX } from 'react';
import { api, getUser, setUser } from './api';
import { canEdit } from './rules';
import type { Item } from './rules';

export default function App(): JSX.Element {
  const [user, setUserState] = useState('alice');
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [title, setTitle] = useState('');
  const [msg, setMsg] = useState('');

  async function load(): Promise<void> {
    try {
      const r = await api.list(search, 1);
      setItems(r.items);
      setTotal(r.total);
    } catch (e) {
      setMsg(String(e));
    }
  }

  useEffect(() => {
    setUser(user);
    load().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  return (
    <div style={{ fontFamily: 'sans-serif', maxWidth: 800, margin: '0 auto', padding: 16 }}>
      <h1>ReadingQueue (demo — local Java backend)</h1>
      <label>
        User:{' '}
        <select value={user} onChange={(e) => setUserState(e.target.value)}>
          <option value="alice">alice</option>
          <option value="bob">bob</option>
        </select>
      </label>{' '}
      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="search titles" />{' '}
      <button onClick={() => load()}>Search</button>
      {msg && <p><b>{msg}</b></p>}
      <p>{total} item(s). You can edit only your own (backend returns 403 otherwise).</p>
      <ul>
        {items.map((it) => (
          <li key={it.id}>
            [{it.status}] <b>{it.title}</b> <i>({it.owner})</i>{' '}
            {canEdit(it.owner, getUser()) && (
              <>
                <button onClick={() => api.setStatus(it.id, 'done').then(load).catch((e) => setMsg(String(e)))}>done</button>{' '}
                <button onClick={() => api.remove(it.id).then(load).catch((e) => setMsg(String(e)))}>delete</button>
              </>
            )}
          </li>
        ))}
      </ul>
      <h2>Add</h2>
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="title" />{' '}
      <button onClick={() => api.add(title, '').then(() => { setTitle(''); load(); }).catch((e) => setMsg(String(e)))}>Add</button>
    </div>
  );
}
