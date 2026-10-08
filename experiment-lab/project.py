"""Fixed-horizon randomized difference-in-means with assignment-level randomization test."""
import argparse,json,math,random,statistics

def analyze(rows,seed=7,permutations=1999):
 if len(rows)<4 or permutations<1:raise ValueError('insufficient rows or permutations')
 ids=[r['user'] for r in rows]
 if len(set(ids))!=len(ids):raise ValueError('one outcome per randomized user required')
 if any(r['arm'] not in ('A','B') or not isinstance(r['outcome'],(int,float)) or not math.isfinite(r['outcome']) for r in rows):raise ValueError('invalid arm/outcome')
 a=[r['outcome'] for r in rows if r['arm']=='A'];b=[r['outcome'] for r in rows if r['arm']=='B']
 if min(len(a),len(b))<2:raise ValueError('two observations per arm required')
 effect=statistics.mean(b)-statistics.mean(a)
 se=math.sqrt(statistics.variance(a)/len(a)+statistics.variance(b)/len(b))
 rng=random.Random(seed);values=a+b;extreme=0
 for _ in range(permutations):
  v=values.copy();rng.shuffle(v);e=statistics.mean(v[len(a):])-statistics.mean(v[:len(a)])
  extreme+=abs(e)>=abs(effect)-1e-12
 # Allocation check assumes planned Bernoulli 50/50 assignment; no other allocation supported.
 z=(len(a)-len(rows)/2)/math.sqrt(len(rows)*.25)
 return {'n_A':len(a),'n_B':len(b),'effect_B_minus_A':effect,'normal_approx_95_interval':[effect-1.96*se,effect+1.96*se],'randomization_p':(extreme+1)/(permutations+1),'allocation_p_normal_approx':math.erfc(abs(z)/math.sqrt(2)),'assumptions':['random assignment','fixed horizon','one independent outcome per user','50/50 planned allocation'],'seed':seed,'permutations':permutations}

def simulate(seed=7,n=200,effect=.2):
 rng=random.Random(seed);return [{'user':str(i),'arm':arm,'outcome':rng.gauss(0,1)+(effect if arm=='B' else 0)} for i in range(n) for arm in [rng.choice(['A','B'])]]
def aa_audit(repetitions=100,seed=7):
 values=[analyze(simulate(seed+i,effect=0),seed+i,199)['randomization_p'] for i in range(repetitions)]
 n=sum(p<.05 for p in values);return {'kind':'synthetic A/A audit','runs':repetitions,'rejections_at_0_05':n,'rate':n/repetitions,'p_values':values,'note':'199 permutations; increase for final evaluation; no tuning on audit seeds'}
def demo(directory):
 from pathlib import Path
 p=Path(directory);p.mkdir(parents=True,exist_ok=True);rows=simulate();(p/'events.json').write_text(json.dumps(rows));print(json.dumps(analyze(rows),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--aa-runs',type=int,default=0);a=p.parse_args();print(json.dumps(aa_audit(a.aa_runs),indent=2)) if a.aa_runs else demo(a.output)
