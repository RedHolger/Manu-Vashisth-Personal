'use strict';let rows=[];const $=id=>document.getElementById(id);
function render(){const list=$('list');list.replaceChildren();const hits=OpsModel.select(rows,$('q').value,$('state').value);$('status').textContent=hits.length+' incidents shown';
 for(const r of hits){const a=document.createElement('article');const h=document.createElement('h2');h.textContent=r.service+' · '+r.id;a.append(h);
 const p=document.createElement('p');p.textContent=r.state+' | Evidence: '+OpsModel.freshness(r,Date.now())+' | '+r.updated;a.append(p);
 const ol=document.createElement('ol');for(const ev of r.events){const li=document.createElement('li');li.textContent=ev.at+' — '+ev.text;ol.append(li);}a.append(ol);list.append(a);}
 const u=new URL(location.href);u.searchParams.set('q',$('q').value);u.searchParams.set('state',$('state').value);history.replaceState(null,'',u);
}
const params=new URL(location.href).searchParams;$('q').value=params.get('q')||'';if([...$('state').options].some(o=>o.value===params.get('state')))$('state').value=params.get('state');
$('q').addEventListener('input',render);$('state').addEventListener('change',render);
$('file').addEventListener('change',async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>2000000)throw new Error('Maximum file size is 2 MB');rows=OpsModel.validate(JSON.parse(await f.text()));render();}catch(err){$('status').textContent='Import failed: '+err.message;}});
$('demo').addEventListener('click',()=>{rows=OpsModel.validate([{id:'synthetic-1',service:'reservations',state:'VERIFYING',updated:new Date().toISOString(),events:[{at:new Date().toISOString(),text:'Synthetic fixture: waiting for three healthy windows.'}]}]);render();});
