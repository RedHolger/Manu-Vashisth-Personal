"""Calibration/evaluation kernel on saved logits; no model training or clinical claims."""
import argparse,json,math,random

def softmax(logits,temperature=1):
 if temperature<=0 or not math.isfinite(temperature) or len(logits)<2 or not all(math.isfinite(v) for v in logits):raise ValueError('invalid logits/temperature')
 vals=[v/temperature for v in logits];m=max(vals);ex=[math.exp(v-m) for v in vals];return [v/sum(ex) for v in ex]
def metrics(rows,temperature=1,bins=10):
 if not rows or bins<1:raise ValueError('empty data or bins')
 correct=[];conf=[];loss=0;bucket=[[] for _ in range(bins)]
 for r in rows:
  p=softmax(r['logits'],temperature);label=r['label']
  if type(label) is not int or not 0<=label<len(p):raise ValueError('invalid label')
  pred=max(range(len(p)),key=p.__getitem__);hit=int(pred==label);c=p[pred]
  correct.append(hit);conf.append(c);loss-=math.log(max(p[label],1e-15));bucket[min(int(c*bins),bins-1)].append((c,hit))
 ece=sum(len(b)/len(rows)*abs(sum(c for c,h in b)/len(b)-sum(h for c,h in b)/len(b)) for b in bucket if b)
 order=sorted(range(len(rows)),key=lambda i:(-conf[i],i));risk=[]
 for k in sorted(set([1,max(1,len(rows)//4),max(1,len(rows)//2),len(rows)])):
  risk.append({'coverage':k/len(rows),'risk':1-sum(correct[i] for i in order[:k])/k})
 return {'n':len(rows),'accuracy':sum(correct)/len(rows),'nll':loss/len(rows),'ece':ece,'risk_coverage':risk}
def choose_temperature(validation):return min([.5,1,1.5,2,3,5],key=lambda t:metrics(validation,t)['nll'])
def validate_splits(train,validation,test):
 ids=[{r['id'] for r in rows} for rows in [train,validation,test]]
 if any(len(s)!=len(rows) for s,rows in zip(ids,[train,validation,test])) or ids[0]&ids[1] or ids[0]&ids[2] or ids[1]&ids[2]:raise ValueError('overlapping/duplicate sample IDs')
 groups=[{r.get('group',r['id']) for r in rows} for rows in [train,validation,test]]
 if groups[0]&groups[1] or groups[0]&groups[2] or groups[1]&groups[2]:raise ValueError('group leakage')
def synthetic(seed,prefix,n=80):
 rng=random.Random(seed);return [{'id':prefix+str(i),'logits':[rng.gauss(0,2),rng.gauss(0,2)],'label':rng.randrange(2)} for i in range(n)]
def demo(directory):
 v=synthetic(7,'v');t=synthetic(9,'t');validate_splits([],v,t);temp=choose_temperature(v)
 print(json.dumps({'kind':'synthetic logits ONLY','temperature_chosen_on_validation':temp,'test_before':metrics(t),'test_after':metrics(t,temp)},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
