"""Bounded read-only local checks; unavailable evidence is UNKNOWN."""
import argparse,json,os,platform,shutil,subprocess,time

def classify_free(total,free):
 if total<=0 or free<0 or free>total:return 'UNKNOWN'
 return 'FAIL' if free/total<.05 else 'WARN' if free/total<.15 else 'PASS'
def command(argv,timeout=2):
 try:
  r=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,check=False)
  return {'status':'PASS' if r.returncode==0 else 'WARN','exit_code':r.returncode,'output':r.stdout[:4000],'error':r.stderr[:500]}
 except (OSError,subprocess.TimeoutExpired) as e:return {'status':'UNKNOWN','reason':type(e).__name__}
def collect(path='.'):
 checks={}
 try:d=shutil.disk_usage(path);checks['disk']={'status':classify_free(d.total,d.free),'total_bytes':d.total,'free_bytes':d.free}
 except OSError as e:checks['disk']={'status':'UNKNOWN','reason':type(e).__name__}
 checks['os']={'status':'PASS','system':platform.system(),'release':platform.release(),'python':platform.python_version()}
 checks['load']={'status':'PASS','load_average':os.getloadavg()} if hasattr(os,'getloadavg') else {'status':'UNKNOWN','reason':'load average unavailable'}
 checks['uptime']=command(['uptime'])
 return {'kind':'actual read-only host observations; not fault localization validation','at_unix':time.time(),'checks':checks}
def demo(directory):print(json.dumps(collect(directory),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();os.makedirs(a.output,exist_ok=True);demo(a.output)
