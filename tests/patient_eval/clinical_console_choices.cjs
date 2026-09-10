const fs=require('node:fs'), assert=require('node:assert/strict');
const Q=require('../../scripts/patient_eval/clinical_console_assets/choices.js');
const C=require('../../scripts/patient_eval/clinical_console_assets/core.js');
const packet=C.blank(JSON.parse(fs.readFileSync(0,'utf8'))), a=Q.blank(packet);
a.reviewer_id='reviewer-A';
assert.equal(Q.counts(a.items[0]).answered,0);Q.validate(packet,a);
// Showing suggested radio values must not complete unseen work or overwrite saved choices.
const preview=Q.blank(packet), before=JSON.stringify(preview);
for(const [section,value] of Object.entries({facts:'supported',privacy:'clear',rubrics:'applicable',completeness:'usable'})){
 assert.equal(Q.displayAnswer(section,'pending'),value);
 assert.equal(JSON.stringify(preview),before);
 Q.confirmAnswer(preview.items[0],section,0);
 assert.equal(section==='completeness'?preview.items[0].completeness:preview.items[0][section][0].answer,value);
 // Restore the untouched draft between sections.
 if(section==='completeness')preview.items[0].completeness='pending';else preview.items[0][section][0].answer='pending';
}
assert.equal(Q.counts(preview.items[0]).answered,0);
preview.items[0].facts[0].answer='uncertain';Q.confirmAnswer(preview.items[0],'facts',0);
assert.equal(preview.items[0].facts[0].answer,'uncertain');
assert.equal(Q.counts(preview.items[0]).answered,1);
assert.equal(Q.displayAnswer('facts',JSON.parse(JSON.stringify(preview)).items[0].facts[0].answer),'uncertain');
assert.equal(preview.profile.independence,'pending');

a.items[0].facts[0].answer='supported';a.items[0].facts[1].answer='correction';
a.items[0].rubrics[0].answer='applicable';a.items[0].rubrics[1].answer='not_applicable';
a.items[0].privacy.forEach(r=>r.answer='clear');a.items[0].completeness='usable';
Q.validate(packet,a);assert.equal(Q.counts(a.items[0]).answered,8);
for(const mutate of [x=>x.clinical_gold=true,x=>x.items[0].facts[0].answer='approved',x=>x.items[0].facts[0].fact_id='fake',x=>x.items[0].privacy.pop(),x=>x.packet_sha256='0'.repeat(64),x=>x.profile.background='verified_doctor']){
 const bad=C.clone(a);mutate(bad);assert.throws(()=>Q.validate(packet,bad));
}
const restored=JSON.parse(JSON.stringify(a));Q.validate(packet,restored);assert.deepEqual(restored,a);
process.stdout.write(JSON.stringify({options:Q.options,bundle:{schema_version:'clinical-console-choice-bundle/v0.2',packet,answers:a}}));
