"""Atomic resumable import over a fixed mock source snapshot. SQLite v0 adapter."""
import argparse,csv,hashlib,io,json,sqlite3
from decimal import Decimal, InvalidOperation
class TransientError(Exception):pass
class IntegrityError(Exception):pass

def digest(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class Source:
 def __init__(self,rows,page_size=2,snapshot='synthetic-v1'):
  if page_size<1:raise ValueError('positive page size')
  self.rows=rows;self.page_size=page_size;self.snapshot=snapshot;self.calls=0;self.fail_once=set()
 def fetch(self,cursor):
  self.calls+=1
  if cursor in self.fail_once:self.fail_once.remove(cursor);raise TransientError('mock 429/500')
  start=int(cursor or 0);rows=self.rows[start:start+self.page_size];end=start+len(rows)
  return {'snapshot':self.snapshot,'start':start,'rows':rows,'next':str(end) if end<len(self.rows) else None,'total':len(self.rows),'checksum':digest(self.rows)}

def normalize(row,schema):
 if not isinstance(row,dict):raise ValueError('row must be object')
 if schema=='a':
  if set(row)!={'id','customer','amount'}:raise ValueError('schema drift')
  ident,customer,amount=row['id'],row['customer'],row['amount']
 elif schema=='b':
  if set(row)!={'order_id','buyer','total_cents'}:raise ValueError('schema drift')
  ident,customer=row['order_id'],row['buyer'];cents=row['total_cents']
  if type(cents) is not int:raise ValueError('integer cents required')
  amount=str(Decimal(cents)/100)
 else:raise ValueError('unknown schema')
 if not isinstance(ident,str) or not ident or not isinstance(customer,str) or not customer:raise ValueError('invalid identity')
 try:a=Decimal(str(amount))
 except InvalidOperation:raise ValueError('invalid amount')
 if not a.is_finite() or a<0 or a*100!=(a*100).to_integral_value():raise ValueError('nonnegative 2-decimal amount required')
 return {'id':ident,'customer':customer,'cents':int(a*100)}
class Importer:
 def __init__(self,path):
  self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row
  self.db.executescript("""
  CREATE TABLE IF NOT EXISTS runs(source TEXT PRIMARY KEY,snapshot TEXT,cursor TEXT,done INTEGER DEFAULT 0,seen INTEGER DEFAULT 0,checksum TEXT);
  CREATE TABLE IF NOT EXISTS raw(source TEXT,position INTEGER,payload TEXT,PRIMARY KEY(source,position));
  CREATE TABLE IF NOT EXISTS orders(source TEXT,id TEXT,customer TEXT,cents INTEGER,PRIMARY KEY(source,id));
  CREATE TABLE IF NOT EXISTS quarantine(source TEXT,position INTEGER,reason TEXT,payload TEXT,PRIMARY KEY(source,position));
  """)
 def step(self,name,source,schema,crash_before_commit=False):
  r=self.db.execute('SELECT * FROM runs WHERE source=?',(name,)).fetchone()
  if r and r['done']:return False
  cursor=r['cursor'] if r else '0';page=source.fetch(cursor)
  expected=r['seen'] if r else 0
  if page['start']!=expected or (r and (page['snapshot']!=r['snapshot'] or page['checksum']!=r['checksum'])):raise IntegrityError('snapshot changed or missing page')
  end=expected+len(page['rows'])
  if page['next'] is not None and (not page['rows'] or int(page['next'])!=end):raise IntegrityError('non-advancing or skipped cursor')
  if page['next'] is None and end!=page['total']:raise IntegrityError('truncated source')
  with self.db:
   for offset,row in enumerate(page['rows']):
    pos=expected+offset;payload=json.dumps(row,sort_keys=True)
    self.db.execute('INSERT INTO raw VALUES(?,?,?)',(name,pos,payload))
    try:
     n=normalize(row,schema)
     old=self.db.execute('SELECT customer,cents FROM orders WHERE source=? AND id=?',(name,n['id'])).fetchone()
     if old and (old['customer'],old['cents'])!=(n['customer'],n['cents']):raise ValueError('conflicting duplicate ID in immutable snapshot')
     self.db.execute('INSERT OR IGNORE INTO orders VALUES(?,?,?,?)',(name,n['id'],n['customer'],n['cents']))
    except (ValueError,TypeError,KeyError) as e:self.db.execute('INSERT INTO quarantine VALUES(?,?,?,?)',(name,pos,str(e),payload))
   self.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET cursor=excluded.cursor,done=excluded.done,seen=excluded.seen',(name,page['snapshot'],page['next'],int(page['next'] is None),end,page['checksum']))
   if page['next'] is None:
    allrows=[json.loads(x[0]) for x in self.db.execute('SELECT payload FROM raw WHERE source=? ORDER BY position',(name,))]
    if digest(allrows)!=page['checksum']:raise IntegrityError('content manifest mismatch')
   if crash_before_commit:raise RuntimeError('injected rollback boundary')
  return page['next'] is not None
 def report(self,name):
  r=self.db.execute('SELECT * FROM runs WHERE source=?',(name,)).fetchone()
  return {'source':name,'checkpoint':dict(r) if r else None,'valid_unique_orders':self.db.execute('SELECT COUNT(*) FROM orders WHERE source=?',(name,)).fetchone()[0],'quarantine':[dict(x) for x in self.db.execute('SELECT position,reason FROM quarantine WHERE source=?',(name,))]}
 def close(self):self.db.close()
def parse_csv(text):return list(csv.DictReader(io.StringIO(text)))
def demo(directory):
 from pathlib import Path
 p=Path(directory);p.mkdir(parents=True,exist_ok=True);db=Importer(p/'import.sqlite')
 a=Source(parse_csv('id,customer,amount\na,Alice,10.25\nb,Bob,2.00\n'));a.fail_once.add('0')
 try:db.step('csv',a,'a')
 except TransientError:pass
 while db.step('csv',a,'a'):pass
 b=Source([{'order_id':'x','buyer':'Cara','total_cents':900},{'bad':'row'}])
 while db.step('json',b,'b'):pass
 print(json.dumps({'kind':'synthetic immutable snapshots','reports':[db.report('csv'),db.report('json')]},indent=2));db.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
