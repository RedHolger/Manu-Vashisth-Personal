"""Critical-path analysis and evidence-based readiness for a finite DAG."""
import argparse,json,math

def plan(tasks):
 by={t['id']:t for t in tasks}
 if len(by)!=len(tasks):raise ValueError('duplicate task ID')
 visiting=set();order=[];visited=set()
 def visit(i):
  if i not in by:raise ValueError('missing prerequisite '+i)
  if i in visiting:raise ValueError('dependency cycle')
  if i in visited:return
  visiting.add(i)
  for d in by[i]['depends']:visit(d)
  visiting.remove(i);visited.add(i);order.append(i)
 for i in by:visit(i)
 finish={};path={};readiness={}
 for i in order:
  t=by[i];duration=t['hours']
  if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<0:raise ValueError('invalid duration')
  prev=max(t['depends'],key=lambda d:finish[d]) if t['depends'] else None
  finish[i]=(finish[prev] if prev else 0)+duration;path[i]=(path[prev] if prev else [])+[i]
  readiness[i]=bool(t.get('owner') and t.get('evidence') and t.get('done') and all(readiness[d] for d in t['depends']))
 end=max(order,key=lambda i:finish[i]) if order else None
 return {'order':order,'critical_path':path[end] if end else [],'estimated_hours':finish[end] if end else 0,'ready':readiness,'note':'Unlimited parallel workers assumed for critical path; estimates are not measured delivery. Evidence references are declared, not content-verified.'}
def demo(directory):
 t=[{'id':'spec','depends':[],'hours':2,'owner':'solo','done':True,'evidence':['SPEC.md']},{'id':'core','depends':['spec'],'hours':8,'owner':'solo','done':False,'evidence':[]},{'id':'demo','depends':['core'],'hours':2,'owner':'solo','done':False,'evidence':[]}];print(json.dumps(plan(t),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--input');a=p.parse_args();print(json.dumps(plan(json.load(open(a.input))),indent=2)) if a.input else demo(a.output)
