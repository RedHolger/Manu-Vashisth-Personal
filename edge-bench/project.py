"""Measured CPU edge-filter benchmark on synthetic frames; not a board/power benchmark."""
import argparse,json,random,statistics,time,tracemalloc

def edges(frame):
 if len(frame)<3 or len(frame[0])<3 or any(len(r)!=len(frame[0]) for r in frame):raise ValueError('rectangular frame >=3x3')
 out=[]
 for y in range(1,len(frame)-1):
  row=[]
  for x in range(1,len(frame[0])-1):
   gx=frame[y-1][x+1]+2*frame[y][x+1]+frame[y+1][x+1]-frame[y-1][x-1]-2*frame[y][x-1]-frame[y+1][x-1]
   gy=frame[y+1][x-1]+2*frame[y+1][x]+frame[y+1][x+1]-frame[y-1][x-1]-2*frame[y-1][x]-frame[y-1][x+1]
   row.append(abs(gx)+abs(gy))
  out.append(row)
 return out
def benchmark(n=12,size=64,seed=7):
 if n<1 or size<3:raise ValueError('invalid benchmark dimensions')
 rng=random.Random(seed);frames=[[[rng.randrange(256) for _ in range(size)] for _ in range(size)] for _ in range(n)];edges(frames[0]);times=[];checksum=0
 tracemalloc.start()
 for f in frames:
  start=time.perf_counter_ns();out=edges(f);times.append((time.perf_counter_ns()-start)/1e6);checksum+=sum(map(sum,out))
 _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
 return {'kind':'actual CPU timings on synthetic frames; tracing overhead included','frames':n,'size':size,'seed':seed,'milliseconds':times,'median_ms':statistics.median(times),'min_ms':min(times),'max_ms':max(times),'peak_traced_python_bytes':peak,'output_checksum':checksum,'power_watts':None,'board_tested':False}
def demo(directory):print(json.dumps(benchmark(),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
