"""Authorization policy matrix with a seeded vulnerable implementation. Pure local calls."""
import argparse,itertools,json

def policy(subject,resource,action):
 if not subject.get('active') or action not in ['read','write','delete']:return False
 if subject['tenant']!=resource['tenant']:return False
 return subject['role']=='admin' or subject['id']==resource['owner'] and action in ['read','write']
def implementation(subject,resource,action,bug=False):
 if bug:return subject.get('active',False) and (subject['role']=='admin' or subject['id']==resource['owner'])
 return policy(subject,resource,action)
def cases():
 subjects=[{'id':i,'tenant':t,'role':r,'active':active} for i,t,r,active in itertools.product(['alice','bob'],['A','B'],['member','admin'],[True,False])]
 resources=[{'id':t+'-doc','tenant':t,'owner':o} for t,o in itertools.product(['A','B'],['alice','bob'])]
 return [(s,r,a) for s,r,a in itertools.product(subjects,resources,['read','write','delete','unknown'])]
def evaluate(bug=False):
 results=[]
 for s,r,a in cases():
  expected=policy(s,r,a);actual=implementation(s,r,a,bug)
  if actual!=expected:results.append({'subject':s,'resource':r,'action':a,'expected':expected,'actual':actual})
 return {'cases':len(cases()),'mismatches':len(results),'violations':results,'adapter':'in-process reference; HTTP regression adapter pending'}
def demo(directory):print(json.dumps({'fixed':evaluate(),'seeded_bug':evaluate(True)},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
