// Minimal DOM harness: tests handlers and exported data, not browser rendering.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const {spawnSync}=require('child_process');
const root=path.resolve(__dirname,'../..');
class Element {
 constructor(tag){this.tag=tag;this.value='';this.textContent='';this.children=[];this.checked=false;this.disabled=false;this.hidden=false;}
 append(...items){this.children.push(...items)} replaceChildren(...items){this.children=items}
 querySelectorAll(selector){return this.children.flatMap(x=>x instanceof Element?[x,...x.querySelectorAll(selector)]:[]).filter(x=>x.tag==='input'&&(selector!=='input:checked'||x.checked))}
 click(){if(this.onclick)this.onclick()}
}
function page(file){
 const html=fs.readFileSync(file,'utf8'),data=html.match(/<script type="application\/json" id="payload">([\s\S]*?)<\/script>/)[1];
 const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]),elements={},downloads=[];
 const document={getElementById(id){return elements[id]??=new Element('div')},createElement(tag){return new Element(tag)},createTextNode(s){return s}};
 document.getElementById('payload').textContent=data;
 const context=vm.createContext({document,console,structuredClone,Date,Set,JSON,Error,Blob,URL:{createObjectURL(blob){downloads.push(blob);return 'blob:test'},revokeObjectURL(){}},setTimeout(fn){fn()}});
 scripts.forEach(s=>vm.runInContext(s,context));
 return {$:id=>document.getElementById(id),context,downloads};
}
async function main(){
 const p=page(path.join(root,'medical/patient-eval/app-pilot-v1/START_HERE.html')),$=p.$;
 const slots=JSON.parse($('payload').textContent).plan.slots;
 $('slot').value=slots.find(s=>s.scenario_id==='AP05-base').slot_id;
 for(const id of ['operator','mode','version','device','memory','network','note'])$(id).value='synthetic-ui-test';
 $('reset').checked=true;$('start').click();assert($('title').textContent.includes('因果'));
 const opening=$('prompt').value;assert(opening.includes('保健品'));assert($('saveAnswer').disabled);
 $('sent').click();assert.equal(vm.runInContext('s.turns.length',p.context),1);
 $('answer').value='请问时间线是什么？';$('saveAnswer').click();assert.equal(vm.runInContext('s.turns.length',p.context),2);
 $('facts').querySelectorAll('input').find(x=>x.value==='F1').checked=true;
 $('quote').value='请问时间线是什么？';$('action').value='facts';$('next').click();assert($('prompt').value.includes('周三'));
 $('sent').click();$('answer').value='还需要核对其他信息。';$('saveAnswer').click();
 $('action').value='unknown';$('next').click();assert.equal(vm.runInContext('pending.action',p.context),'event');
 $('action').value='event';$('next').click();assert($('prompt').value.includes('周一'));
 $('sent').click();$('answer').value='已采用更正后的时间线。';$('saveAnswer').click();
 $('action').value='probe';$('next').click();$('sent').click();$('answer').value='仍不能证明因果关系。';$('saveAnswer').click();
 $('status').value='completed';$('stop').value='synthetic UI fixture only';$('export').click();
 assert.equal(p.downloads.length,1);const exported=JSON.parse(await p.downloads[0].text());
 assert.equal(exported[0].turns.length,8);assert.equal(exported[0].disclosure_log[3].phase,'probe');
 assert.equal(exported[0].observations.length,0);
 const out=path.join(root,'medical/patient-eval/local/app-ui-test');fs.mkdirSync(out,{recursive:true});
 fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify(exported));
 const validation=spawnSync('python',['-c',
  'import json,sys; from scripts.patient_eval import app_pilot as a; s,h=a.get_suite(); p=json.load(open(sys.argv[2])); v=a.validate_records(json.load(open(sys.argv[1])),s,h,p); packet=a.make_review(v,s,h,"ui-test"); print(a.render_page("review.html",dict(packet=packet,sessions=v,suite=s)))',
  path.join(out,'capture.json'),path.join(root,'medical/patient-eval/app-pilot-v1/smoke-plan.json')],{cwd:root,encoding:'utf8'});
 assert.equal(validation.status,0,validation.stderr);fs.writeFileSync(path.join(out,'review.html'),validation.stdout);
 const q=page(path.join(out,'review.html'));q.$('export').click();
 const review=JSON.parse(await q.downloads[0].text());assert(review.rows.every(r=>r.outcome==='unassessed'));
 assert.equal(review.rows.length,11);
 const timeout=page(path.join(root,'medical/patient-eval/app-pilot-v1/START_HERE.html'));const t=timeout.$;
 t('slot').value=slots[0].slot_id;for(const id of ['operator','mode','version','device','memory','network','note'])t(id).value='synthetic-ui-test';t('reset').checked=true;t('start').click();
 t('status').value='target_error';t('stop').value='120秒无响应';t('error').value='120秒无响应';t('export').click();assert.equal(timeout.downloads.length,0);
 t('sent').click();t('export').click();const failed=JSON.parse(await timeout.downloads[0].text());assert.equal(failed[0].turns.length,1);assert.equal(failed[0].status,'target_error');
 console.log('PASS: collector correction/probe/export, Python import, blank review export, submitted versus unsent outage. Minimal DOM harness; browser rendering NOT tested.');
}
main().catch(e=>{console.error(e);process.exitCode=1});
