"""Synthetic auth-log investigation: burst failures followed by success, with provenance."""
import argparse,datetime as dt,hashlib,json

def analyze(events,window=300,minimum=3):
 if window<=0 or minimum<1:raise ValueError('invalid detector config')
 parsed=[];seen={}
 for e in events:
  if set(e)!={'id','at','user','ip','kind'} or e['kind'] not in ['failure','success']:raise ValueError('invalid event')
  if e['id'] in seen:
   if seen[e['id']]!=e:raise ValueError('conflicting event id')
   continue
  seen[e['id']]=e;t=dt.datetime.fromisoformat(e['at'].replace('Z','+00:00'))
  if t.tzinfo is None:raise ValueError('timezone missing')
  parsed.append((t.timestamp(),e))
 failures={};findings=[]
 for timestamp,e in sorted(parsed,key=lambda x:(x[0],x[1]['id'])):
  key=(e['user'],e['ip']);prior=[(t,i) for t,i in failures.get(key,[]) if timestamp-window<=t<=timestamp]
  if e['kind']=='failure':prior.append((timestamp,e['id']))
  elif len(prior)>=minimum:
   findings.append({'rule':'failures_then_success','user':e['user'],'ip':e['ip'],'evidence_ids':[i for _,i in prior]+[e['id']],'severity':'review','confidence':'pattern only; benign retries possible'})
   prior=[]
  failures[key]=prior
 return {'input_sha256':hashlib.sha256(json.dumps(events,sort_keys=True).encode()).hexdigest(),'findings':findings,'uncertainty':['missing logs unknown','clock synchronization not established'],'timeline':[e for _,e in sorted(parsed,key=lambda x:(x[0],x[1]['id']))]}
def demo(directory):
 rows=[{'id':str(i),'at':f'2026-01-01T00:00:0{i}Z','user':'synthetic-user','ip':'192.0.2.1','kind':'failure' if i<3 else 'success'} for i in range(4)];print(json.dumps(analyze(list(reversed(rows))),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
