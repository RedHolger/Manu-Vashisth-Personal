"""Anonymized formative-study summarizer, not a substitute for actual participants."""
import argparse,json,statistics

def summarize(rows):
 seen=set();tasks={};themes={}
 for r in rows:
  if set(r)!={'participant','task','success','seconds','observation','codes','synthetic'}:raise ValueError('invalid study row')
  key=(r['participant'],r['task'])
  if key in seen:raise ValueError('duplicate participant/task')
  seen.add(key)
  if type(r['success']) is not bool or type(r['synthetic']) is not bool or not isinstance(r['seconds'],(int,float)) or not 0<=r['seconds']<86400:raise ValueError('invalid measurement')
  if not isinstance(r['codes'],list) or any(not isinstance(c,str) for c in r['codes']):raise ValueError('codes must be strings')
  t=tasks.setdefault(r['task'],[]);t.append(r)
  for code in set(r['codes']):themes.setdefault(code,[]).append({'participant':r['participant'],'task':r['task'],'observation':r['observation']})
 return {'synthetic_rows':sum(r['synthetic'] for r in rows),'tasks':{k:{'n':len(v),'completed':sum(r['success'] for r in v),'median_seconds':statistics.median(r['seconds'] for r in v)} for k,v in tasks.items()},'themes':themes,'limitation':'formative convenience sample; no population or causal claim'}
def demo(directory):
 rows=[{'participant':'synthetic-01','task':'find stale incident','success':False,'seconds':80,'observation':'Fixture: missed stale label','codes':['visibility'],'synthetic':True},{'participant':'synthetic-02','task':'find stale incident','success':True,'seconds':34,'observation':'Fixture: found label','codes':[],'synthetic':True}];print(json.dumps(summarize(rows),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--input');a=p.parse_args();print(json.dumps(summarize(json.load(open(a.input))),indent=2)) if a.input else demo(a.output)
