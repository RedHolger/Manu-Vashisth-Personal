(function(root){'use strict';
function validate(data){
 if(!data||data.version!==1||!Array.isArray(data.topics))throw new Error('Expected version 1 topics');
 const map=new Map();for(const t of data.topics){if(!t||typeof t.id!=='string'||!t.id||typeof t.title!=='string'||!Array.isArray(t.requires)||typeof t.done!=='boolean'||map.has(t.id))throw new Error('Invalid topic');map.set(t.id,t);}
 const active=new Set(),seen=new Set(),order=[];
 function visit(id){if(!map.has(id))throw new Error('Unknown prerequisite '+id);if(active.has(id))throw new Error('Prerequisite cycle');if(seen.has(id))return;active.add(id);for(const p of map.get(id).requires)visit(p);active.delete(id);seen.add(id);order.push(id);}
 for(const id of map.keys())visit(id);
 for(const t of map.values())if(t.done&&t.requires.some(id=>!map.get(id).done))throw new Error('Completed topic has unfinished prerequisites');
 return {version:1,topics:order.map(id=>({...map.get(id),requires:[...map.get(id).requires]}))};
}
function toggle(data,id){const d=validate(data),map=new Map(d.topics.map(t=>[t.id,t])),t=map.get(id);if(!t)throw new Error('Unknown topic');
 if(!t.done&&t.requires.some(p=>!map.get(p).done))throw new Error('Complete prerequisites first');
 if(t.done&&d.topics.some(x=>x.done&&x.requires.includes(id)))throw new Error('Undo completed dependants first');
 t.done=!t.done;return d;
}
const api={validate,toggle};if(typeof module!=='undefined')module.exports=api;else root.StudyModel=api;
})(globalThis);
