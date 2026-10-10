"""Isolated real FRR control-plane lab. No host routes or exposed ports.
Two ephemeral Docker peers; bounded peer-down and incorrect-prefix tests.
Docker NET_ADMIN is used only inside these containers for packet-loss injection.
"""
from pathlib import Path
import subprocess,json,time,uuid,datetime
OUT=Path(__file__).resolve().parent/'results';OUT.mkdir(exist_ok=True)
prefix='manu-packetlab-'+uuid.uuid4().hex[:8];net=prefix+'-net';nodes=[];events=[]
def run(*args,check=True):
 p=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=60)
 if check and p.returncode:raise RuntimeError(' '.join(args)+'\n'+p.stderr+p.stdout)
 return p.stdout.strip()
def record(kind,**kw):events.append(dict(event=kind,monotonic=time.monotonic(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**kw))
def vty(node,*commands):
 args=['exec',node,'vtysh','-d','bgpd']
 for cmd in commands:args+=['-c',cmd]
 return run(*args)
def routes():return json.loads(vty(nodes[0],'show bgp ipv4 unicast json')).get('routes',{})
def wait(predicate,timeout=30):
 until=time.monotonic()+timeout
 while time.monotonic()<until:
  if predicate():return
  time.sleep(.25)
 raise AssertionError('convergence timeout')
def config(*cmd):return vty(nodes[1],'configure terminal','router bgp 65002',*cmd)
try:
 run('network','create',net)
 for i in range(2):
  name=prefix+f'-r{i+1}'
  run('run','-d','--name',name,'--network',net,'--cap-add=NET_ADMIN','--entrypoint','sleep','quay.io/frrouting/frr:10.2.1','600');nodes.append(name)
 ips=[run('inspect','-f','{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}',n) for n in nodes]
 for i,n in enumerate(nodes):
  conf=f'''hostname r{i+1}
router bgp {65001+i}
 bgp router-id {ips[i]}
 no bgp ebgp-requires-policy
 no bgp network import-check
 neighbor {ips[1-i]} remote-as {65002-i}
 neighbor {ips[1-i]} timers 1 3
 address-family ipv4 unicast
  network 10.20.{i+1}.0/24
 exit-address-family
'''
  p=subprocess.run(['docker','exec','-i',n,'sh','-c','cat > /tmp/bgpd.conf'],input=conf,text=True,capture_output=True);p.check_returncode()
  run('exec',n,'/usr/lib/frr/bgpd','-d','-S','-Z','-f','/tmp/bgpd.conf','-i','/tmp/bgpd.pid')
 wait(lambda:'10.20.2.0/24' in routes());record('baseline',routes=routes(),summary=json.loads(vty(nodes[0],'show bgp summary json')))
 config(f'neighbor {ips[0]} shutdown');wait(lambda:'10.20.2.0/24' not in routes());record('peer_down',routes=routes())
 config(f'no neighbor {ips[0]} shutdown');wait(lambda:'10.20.2.0/24' in routes());record('peer_recovered',routes=routes())
 config('address-family ipv4 unicast','no network 10.20.2.0/24','network 10.99.99.0/24')
 wait(lambda:'10.99.99.0/24' in routes() and '10.20.2.0/24' not in routes());record('incorrect_prefix',routes=routes())
 config('address-family ipv4 unicast','no network 10.99.99.0/24','network 10.20.2.0/24')
 wait(lambda:'10.20.2.0/24' in routes() and '10.99.99.0/24' not in routes());record('prefix_recovered',routes=routes())
 # tc may not be packaged in the minimal image; mark explicitly if unavailable.
 available=run('exec',nodes[1],'sh','-c','command -v tc',check=False)
 if available:
  try:
   run('exec',nodes[1],'tc','qdisc','add','dev','eth0','root','netem','loss','100%')
   wait(lambda:'10.20.2.0/24' not in routes(),12);record('packet_loss_peer_timeout',routes=routes())
  finally:run('exec',nodes[1],'tc','qdisc','del','dev','eth0','root',check=False)
  wait(lambda:'10.20.2.0/24' in routes());record('packet_loss_recovered',routes=routes())
 else:record('packet_loss_skipped',reason='tc absent from image')
 record('passed',scope='FRR BGP control plane; no kernel forwarding or containerlab claim')
finally:
 for n in nodes:run('rm','-f',n,check=False)
 run('network','rm',net,check=False)
 (OUT/'live_frr.json').write_text(json.dumps({'image':'quay.io/frrouting/frr:10.2.1','events':events},indent=2))
print(json.dumps({'events':[e['event'] for e in events],'evidence':str(OUT/'live_frr.json')}))
