"""Evidence-linked prioritization and a descriptive pilot funnel."""
import argparse,json,math

def prioritize(features,evidence_ids):
 output=[]
 for f in features:
  if not f['evidence'] or any(e not in evidence_ids for e in f['evidence']):raise ValueError('missing evidence reference')
  if not all(isinstance(f[k],(int,float)) and math.isfinite(f[k]) for k in ['effort','confidence','reach','impact']):raise ValueError('finite scores required')
  if f['effort']<=0 or not 0<=f['confidence']<=1 or f['reach']<0 or f['impact']<0:raise ValueError('invalid score inputs')
  output.append(dict(f,score=f['reach']*f['impact']*f['confidence']/f['effort']))
 return sorted(output,key=lambda f:(-f['score'],f['id']))
def funnel(events):
 users={};seen=set()
 for e in events:
  if e['id'] in seen:continue
  seen.add(e['id'])
  if e.get('test_account'):continue
  if e['type'] not in ['visit','signup','activate']:raise ValueError('unknown funnel event')
  users.setdefault(e['user'],set()).add(e['type'])
 visitors={u for u,v in users.items() if 'visit' in v};signup={u for u in visitors if 'signup' in users[u]};active={u for u in signup if 'activate' in users[u]}
 return {'visitors':len(visitors),'signups':len(signup),'activated':len(active),'activation_per_visitor':len(active)/len(visitors) if visitors else None,'note':'set-membership descriptive funnel; ordering/time-window model pending'}
def demo(directory):
 f=[{'id':'export','reach':10,'impact':2,'confidence':.6,'effort':3,'evidence':['synthetic-interview-1']}]
 print(json.dumps({'kind':'synthetic discovery example','ranking':prioritize(f,{'synthetic-interview-1'}),'funnel':funnel([])},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
