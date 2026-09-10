const fs=require('node:fs'),assert=require('node:assert/strict');
const Q=require('../../scripts/patient_eval/clinical_console_assets/choices.js');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
if(process.argv.includes('--validate')){
 process.stdout.write(JSON.stringify(input.map(b=>{try{Q.restoreBundle(b);return true;}catch{return false;}})));
}else{
 const packet=input,clone=x=>JSON.parse(JSON.stringify(x)),fixtures={};let checks=0;
 const fresh=()=>{const a=Q.newAnswers(packet);a.reviewer_id='reviewer-A';return a;};
 const save=(name,a)=>{Q.validate(packet,a);fixtures[name]=Q.bundle(packet,a);};
 let a=fresh();Q.recordDisplay(a,0,'facts',0);
 assert.equal(a.items[0].facts[0].answer,'pending');assert.equal(Q.counts(a.items[0]).answered,0);
 assert.deepEqual(a.interaction.records[0].display,{ui_version:'0.2.2',preset_shown:true,answer:'supported'});save('viewed',a);checks++;
 a=fresh();for(const [s,v]of Object.entries(Q.suggested)){
  Q.recordDisplay(a,0,s,0);assert.equal(Q.displayAnswer(s,'pending'),v);Q.recordConfirmation(a,0,s,0);
  const r=a.interaction.records.find(r=>r.section===s);assert.equal(r.confirmation.method,'preset');assert.equal(r.confirmation.answer,v);
 }
 save('four_defaults',a);checks++;
 a=fresh();Q.recordSelection(a,0,'facts',0,'uncertain');save('selected',a);
 assert.equal(a.interaction.records[0].confirmation,null);checks++;
 Q.recordConfirmation(a,0,'facts',0);save('selection_confirmed',a);assert.equal(a.interaction.records[0].confirmation.method,'selection');checks++;
 Q.recordSelection(a,0,'facts',0,'supported');Q.recordConfirmation(a,0,'facts',0);save('changed_back_to_default',a);
 assert.equal(a.interaction.records[0].confirmation.method,'selection');checks++;
 Q.recordSkip(a,0,'facts',0);save('skipped',a);assert.equal(a.interaction.records[0].confirmation,null);assert.equal(a.items[0].facts[0].answer,'pending');checks++;
 const old=Q.blank(packet);old.reviewer_id='reviewer-A';old.items[0].facts[0].answer='uncertain';old.items[0].privacy[0].answer='clear';
 const original=JSON.stringify(old);a=Q.restoreAnswers(packet,old);assert.equal(JSON.stringify(old),original);
 assert.equal(a.items[0].facts[0].answer,'uncertain');assert.equal(a.interaction.records[0].origin.ui_version,null);
 assert.equal(a.interaction.records[0].confirmation,null);assert.equal(a.interaction.records[0].last_action,'legacy_unknown');save('legacy_migrated',a);checks++;
 Q.recordDisplay(a,0,'facts',0);assert.equal(a.interaction.records[0].display.preset_shown,false);
 Q.recordConfirmation(a,0,'facts',0);assert.equal(a.interaction.records[0].confirmation.method,'existing_answer');
 assert.equal(a.interaction.records[0].origin.ui_version,null);save('legacy_reconfirmed',a);checks++;
 const snapshot=JSON.stringify(a),b=Q.restoreBundle(Q.bundle(packet,a));assert.deepEqual(b,a);assert.equal(JSON.stringify(a),snapshot);
 Q.recordDisplay(b,0,'facts',0);Q.recordConfirmation(b,0,'facts',0);assert.deepEqual(b.interaction.records[0].confirmation,a.interaction.records[0].confirmation);checks++;
 a=fresh();Q.recordConfirmation(a,0,'facts',0);Q.recordSelection(a,0,'facts',0,'uncertain');assert.equal(a.interaction.records[0].confirmation,null);save('edited_after_confirm',a);checks++;
 process.stdout.write(JSON.stringify({checks,fixtures,legacy:Q.bundle(packet,old)}));
}
