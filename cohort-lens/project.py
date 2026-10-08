"""UTC cohort retention with late-event deduplication and right-censoring."""
import argparse,datetime as dt,json
UTC=dt.timezone.utc

def parse(s):
 d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('timezone required')
 return d.astimezone(UTC)
def cohorts(events,as_of):
 cutoff=parse(as_of);seen={};users={}
 for e in events:
  if set(e)!={'id','user','type','at','ingested_at'}:raise ValueError('invalid event schema')
  at=parse(e['at']);ingested=parse(e['ingested_at'])
  if ingested>cutoff or at>cutoff:continue
  if e['id'] in seen:
   old=seen[e['id']]
   if any(old[k]!=e[k] for k in ['user','type','at']):raise ValueError('conflicting duplicate event')
   continue
  seen[e['id']]=e;users.setdefault(e['user'],[]).append((at,e['type']))
 groups={}
 for user,items in users.items():
  signs=[t for t,kind in items if kind=='signup']
  if not signs:continue
  signup=min(signs);monday=(signup-dt.timedelta(days=signup.weekday())).date().isoformat()
  g=groups.setdefault(monday,{'users':0,'activated':0,'week1_eligible':0,'week1_retained':0});g['users']+=1
  g['activated']+=any(kind=='activate' and signup<=t<signup+dt.timedelta(days=7) for t,kind in items)
  if cutoff>=signup+dt.timedelta(days=14):
   g['week1_eligible']+=1;g['week1_retained']+=any(kind=='active' and signup+dt.timedelta(days=7)<=t<signup+dt.timedelta(days=14) for t,kind in items)
 for g in groups.values():g['week1_retention']=g['week1_retained']/g['week1_eligible'] if g['week1_eligible'] else None
 return {'as_of':cutoff.isoformat(),'definition':'week1 = days [7,14) since signup; only complete windows in denominator','cohorts':groups}
def demo(directory):
 rows=[{'id':str(i),'user':'u','type':kind,'at':date,'ingested_at':date} for i,(kind,date) in enumerate([('signup','2026-01-01T00:00:00Z'),('activate','2026-01-02T00:00:00Z'),('active','2026-01-09T00:00:00Z')])]
 print(json.dumps(cohorts(rows,'2026-01-20T00:00:00Z'),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
