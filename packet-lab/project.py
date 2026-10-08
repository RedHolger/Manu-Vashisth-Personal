"""Offline packet-summary and layered diagnosis kernel. No live network probing."""
import argparse,ipaddress,json

def diagnose(evidence):
 findings=[]
 for layer in ['dns','route','tcp','application']:
  state=evidence.get(layer)
  if state not in [True,False,None]:raise ValueError('evidence must be bool/null')
  if state is None:findings.append({'layer':layer,'status':'UNKNOWN'})
  elif state:findings.append({'layer':layer,'status':'PASS'})
  else:
   findings.append({'layer':layer,'status':'FAIL','next':'collect evidence at this layer; downstream failure may be a consequence'})
 return findings
def flows(rows):
 result={}
 for r in rows:
  src=str(ipaddress.ip_address(r['src']));dst=str(ipaddress.ip_address(r['dst']))
  if type(r['bytes']) is not int or r['bytes']<0 or r['protocol'] not in ['TCP','UDP','ICMP']:raise ValueError('invalid packet record')
  key=(src,dst,r['protocol']);result[key]=result.get(key,0)+r['bytes']
 return [{'src':s,'dst':d,'protocol':p,'bytes':b} for (s,d,p),b in sorted(result.items())]
def demo(directory):print(json.dumps({'kind':'synthetic offline fixture','diagnosis':diagnose({'dns':True,'route':True,'tcp':False}),'flows':flows([{'src':'192.0.2.1','dst':'192.0.2.2','protocol':'TCP','bytes':64}])},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);demo(p.parse_args().output)
