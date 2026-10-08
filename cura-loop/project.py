"""Active-learning budget simulation with held-out test set and hidden oracle labels."""
import argparse,json,math,random

def probability(x,labeled):
 if not labeled:return .5
 chosen=sorted(labeled,key=lambda row:sum((a-b)**2 for a,b in zip(x,row['x'])))[:5]
 return (sum(r['y'] for r in chosen)+1)/(len(chosen)+2)
def select(pool,labeled,method,rng):
 if not pool:raise ValueError('empty pool')
 if method=='random':return rng.randrange(len(pool))
 if method=='uncertainty':return min(range(len(pool)),key=lambda i:abs(probability(pool[i]['x'],labeled)-.5))
 if method=='diversity':
  if not labeled:return 0
  return max(range(len(pool)),key=lambda i:min(sum((a-b)**2 for a,b in zip(pool[i]['x'],r['x'])) for r in labeled))
 raise ValueError('unknown method')
def run(method,seed=7,budget=30):
 if budget<1 or budget>100:raise ValueError('budget 1..100')
 rng=random.Random(seed);allrows=[{'id':str(i),'x':[rng.uniform(-1,1),rng.uniform(-1,1)]} for i in range(150)]
 oracle={r['id']:int(sum(r['x'])>0) for r in allrows};pool=allrows[:100];test=allrows[100:];labeled=[];history=[]
 # All strategies share the same first five randomly selected examples.
 init=random.Random(seed+1);initial=init.sample([r['id'] for r in pool],min(5,budget))
 selection_rng=random.Random(seed+2)
 for step in range(budget):
  i=next(i for i,r in enumerate(pool) if r['id']==initial[step]) if step<len(initial) else select(pool,labeled,method,selection_rng)
  item=pool.pop(i);labeled.append(dict(item,y=oracle[item['id']]))
  score=sum((probability(r['x'],labeled)>=.5)==oracle[r['id']] for r in test)/len(test)
  history.append({'round':step+1,'selected_id':item['id'],'labels_acquired':len(labeled),'test_accuracy':score})
 return {'kind':'synthetic hidden-label simulation; no measured annotator time','method':method,'seed':seed,'history':history}
def demo(directory):print(json.dumps([run(m) for m in ['random','uncertainty','diversity']],indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
