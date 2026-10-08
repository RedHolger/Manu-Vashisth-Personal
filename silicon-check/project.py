"""FIFO cycle reference. RTL simulation is a separate, explicitly required check."""
import argparse,json,random
from collections import deque
class FIFO:
 def __init__(self,depth=4):
  if depth<1:raise ValueError('positive depth')
  self.depth=depth;self.q=deque()
 def step(self,write=False,read=False,value=0,reset=False):
  if reset:self.q.clear();return {'write_accepted':False,'read_accepted':False,'read_value':None,'count':0}
  # Acceptance uses pre-edge occupancy: full+read does not accept a write this cycle.
  wa=write and len(self.q)<self.depth;ra=read and bool(self.q);v=self.q.popleft() if ra else None
  if wa:self.q.append(value&255)
  return {'write_accepted':bool(wa),'read_accepted':bool(ra),'read_value':v,'count':len(self.q)}
def demo(directory):
 q=FIFO();rng=random.Random(7);events=[]
 for i in range(40):events.append(q.step(bool(rng.randrange(2)),bool(rng.randrange(2)),i,reset=i in [0,20]))
 print(json.dumps({'kind':'Python reference only; not RTL simulation','events':events},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
