"""Permission-aware lexical retrieval and extractive answers. No embeddings or LLM claims."""
import argparse,hashlib,json,re,sqlite3
from collections import Counter
class Unauthorized(PermissionError):pass
class Store:
 def __init__(self,path):
  self.db=sqlite3.connect(path,isolation_level=None);self.db.row_factory=sqlite3.Row
  self.db.executescript("""
  CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT,tenant TEXT);
  CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,tenant TEXT,version INTEGER,text TEXT,checksum TEXT,deleted INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS grants(user_id TEXT,document_id TEXT,PRIMARY KEY(user_id,document_id));
  CREATE TABLE IF NOT EXISTS records(tenant TEXT,id TEXT,value TEXT,PRIMARY KEY(tenant,id));
  CREATE TABLE IF NOT EXISTS query_runs(id INTEGER PRIMARY KEY,user_id TEXT,tenant TEXT,question TEXT,answer TEXT);
  """)
 def session(self,token,user,tenant):
  if not token or not user or not tenant:raise ValueError('nonempty identity')
  self.db.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user,tenant))
 def identity(self,token):
  r=self.db.execute('SELECT user_id,tenant FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
  if not r:raise Unauthorized('unknown session')
  return r['user_id'],r['tenant']
 def put(self,token,ident,text):
  user,tenant=self.identity(token)
  if not isinstance(text,str) or not text.strip():raise ValueError('document text required')
  self.db.execute('BEGIN IMMEDIATE')
  try:
   old=self.db.execute('SELECT * FROM documents WHERE id=?',(ident,)).fetchone()
   if old and (old['tenant']!=tenant or not self._allowed(user,tenant,ident)):raise Unauthorized('not a document member')
   v=old['version']+1 if old else 1
   self.db.execute('INSERT INTO documents VALUES(?,?,?,?,?,0) ON CONFLICT(id) DO UPDATE SET version=excluded.version,text=excluded.text,checksum=excluded.checksum,deleted=0',(ident,tenant,v,text,hashlib.sha256(text.encode()).hexdigest()))
   self.db.execute('INSERT OR IGNORE INTO grants VALUES(?,?)',(user,ident));self.db.commit()
  except BaseException:self.db.rollback();raise
 def _allowed(self,user,tenant,ident):
  return bool(self.db.execute('SELECT 1 FROM documents d JOIN grants g ON d.id=g.document_id WHERE d.id=? AND d.tenant=? AND g.user_id=? AND d.deleted=0',(ident,tenant,user)).fetchone())
 def revoke(self,token,document):
  user,tenant=self.identity(token)
  if not self._allowed(user,tenant,document):raise Unauthorized('not allowed')
  self.db.execute('DELETE FROM grants WHERE user_id=? AND document_id=?',(user,document))
 def delete(self,token,document):
  user,tenant=self.identity(token)
  if not self._allowed(user,tenant,document):raise Unauthorized('not allowed')
  self.db.execute('UPDATE documents SET deleted=1 WHERE id=?',(document,))
 def candidates(self,token,question,k=3):
  if k<1 or k>20:raise ValueError('invalid k')
  user,tenant=self.identity(token);terms=set(re.findall(r'\w+',question.lower()))
  hits=[]
  for d in self.db.execute('SELECT d.* FROM documents d JOIN grants g ON d.id=g.document_id WHERE d.tenant=? AND g.user_id=? AND d.deleted=0',(tenant,user)):
   for index,chunk in enumerate(re.split(r'(?<=[.!?])\s+|\n+',d['text'])):
    words=Counter(re.findall(r'\w+',chunk.lower()));score=sum(min(words[t],1) for t in terms)
    if score:hits.append({'document':d['id'],'version':d['version'],'chunk':index,'quote':chunk,'score':score})
  return sorted(hits,key=lambda h:(-h['score'],h['document'],h['chunk']))[:k]
 def finalize(self,token,question,hits):
  # Serialize authorization/version recheck against writes within this SQLite service.
  user,tenant=self.identity(token);self.db.execute('BEGIN IMMEDIATE')
  try:
   safe=[]
   for h in hits:
    if self._allowed(user,tenant,h['document']):
     r=self.db.execute('SELECT version,text FROM documents WHERE id=?',(h['document'],)).fetchone()
     chunks=re.split(r'(?<=[.!?])\s+|\n+',r['text'])
     if r['version']==h['version'] and 0<=h['chunk']<len(chunks) and chunks[h['chunk']]==h['quote']:safe.append(h)
   answer={'abstained':not safe,'mode':'extractive lexical baseline','citations':safe,'text':'\n'.join(h['quote'] for h in safe) if safe else 'No authorized supporting passage found.'}
   self.db.execute('INSERT INTO query_runs(user_id,tenant,question,answer) VALUES(?,?,?,?)',(user,tenant,question,json.dumps(answer)))
   self.db.commit();return answer
  except BaseException:self.db.rollback();raise
 def query(self,token,question):return self.finalize(token,question,self.candidates(token,question))
 def read_record(self,token,record_id):
  _,tenant=self.identity(token)
  r=self.db.execute('SELECT value FROM records WHERE tenant=? AND id=?',(tenant,record_id)).fetchone()
  return json.loads(r[0]) if r else None
 def history(self,token):
  # Re-authorize every historical answer; never return persisted answer text blindly.
  user,tenant=self.identity(token);result=[]
  for r in self.db.execute('SELECT id,answer FROM query_runs WHERE user_id=? AND tenant=?',(user,tenant)):
   a=json.loads(r['answer']);permitted=[]
   for h in a['citations']:
    if self._allowed(user,tenant,h['document']):
     v=self.db.execute('SELECT version FROM documents WHERE id=?',(h['document'],)).fetchone()[0]
     if v==h['version']:permitted.append(h)
   result.append({'id':r['id'],'citations':permitted})
  return result
 def close(self):self.db.close()
def demo(directory):
 from pathlib import Path
 p=Path(directory);p.mkdir(parents=True,exist_ok=True);s=Store(p/'rag.sqlite')
 s.session('local-demo-a','alice','A');s.session('local-demo-b','bob','B')
 s.put('local-demo-a','a','Refunds take five working days. Support is open Monday.');s.put('local-demo-b','b','Secret invoice is 999.')
 print(json.dumps({'public':s.query('local-demo-a','refunds'),'unauthorized_query':s.query('local-demo-a','secret invoice')},indent=2));s.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
