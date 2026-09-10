/* Pure state helpers; browser checks are not source authentication. */
(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  const flags = {formal_approval:false, clinical_gold:false, dynamic_scenario_ready:false};
  const frozen = ['C0042','C0039','C0032','C0047','C0046','C0017','C0031','C0040','C0022','C0015','C0029','C0038'];
  const fail = (ok, message) => { if (!ok) throw new Error(message); };
  const canonical = x => JSON.stringify(sort(x));
  function sort(x) { if (Array.isArray(x)) return x.map(sort); if (x && typeof x === 'object') return Object.fromEntries(Object.keys(x).sort().map(k => [k,sort(x[k])])); return x; }
  function immutable(packet) { const x=clone(packet); delete x.reviewer_id; delete x.packet_sha256; x.items.forEach(i=>delete i.review); return canonical(x); }
  function checkPacket(p) {
    fail(p && p.schema_version==='candidate-review/v0.1' && p.local_only===true,'需要本地 candidate-review/v0.1 来源包。');
    fail(Object.keys(flags).every(k=>p[k]===false),'来源包不得包含已批准状态。');
    fail(typeof p.packet_sha256==='string' && /^[a-f0-9]{64}$/.test(p.packet_sha256),'缺少有效格式的来源摘要；仍需官方验证。');
    fail(Array.isArray(p.items) && p.items.length>0 && p.items.length<=500,'候选必须为1至500项。');
    const seen=new Set();
    p.items.forEach(i=>{
      fail(typeof i.candidate_id==='string' && !seen.has(i.candidate_id),'候选编号缺失或重复。'); seen.add(i.candidate_id);
      fail(Array.isArray(i.turns) && i.turns.length>0 && i.turns.every(t=>typeof t.turn_id==='string' && typeof t.content==='string' && ['patient','doctor'].includes(t.role)),'原文轮次格式错误。');
      fail(new Set(i.turns.map(t=>t.turn_id)).size===i.turns.length,'轮次编号重复。');
      fail(i.fact_draft && Array.isArray(i.fact_draft.fact_candidates) && i.review && Array.isArray(i.review.facts) && Array.isArray(i.review.rubrics),'缺少事实或规则结构。');
      fail(i.review.facts.length===i.fact_draft.fact_candidates.length,'事实行数不一致。');
    }); return p;
  }
  function blank(p) {
    checkPacket(p); const out=clone(p); out.reviewer_id='';
    for (const item of out.items) {
      item.review.privacy={decision:'unreviewed',checked_turn_ids:[],reason:'',additional_spans:[]};
      item.review.completeness={decision:'unreviewed',reason:'',evidence_turn_ids:[]};
      item.review.facts=item.fact_draft.fact_candidates.map(f=>{
        const r=clone(f.review); delete r.reviewer_id;
        return {...r,decision:'unreviewed',polarity:null,is_patient_assertion:null,subject:null,time:null,manual_groundsignal_slot:null,correction_of_candidate_id:null,evidence_spans:[],disclosure_policy:null,reason:'',fact_id:f.candidate_id,ask_patterns:[],disclosure_condition:''};
      });
      item.review.rubrics=item.review.rubrics.map(r=>({...r,decision:'unreviewed',applicability:'unreviewed',description:'',anchors:{'0':'','1':'','2':''},serious_error_definition:'',opportunity:{trigger:'',deadline:''},reason:''}));
    } return out;
  }
  function compatible(source, review) {
    checkPacket(review); fail(immutable(source)===immutable(review) && source.packet_sha256===review.packet_sha256,'来源、版本或原文不匹配；拒绝覆盖。');
    fail(canonical(Object.keys(source).sort())===canonical(Object.keys(review).sort()),'资料包字段发生变化。');
    source.items.forEach((i,n)=>{
      const r=review.items[n].review;
      fail(canonical(Object.keys(i.review).sort())===canonical(Object.keys(r).sort()),'审核分区字段变化。');
      ['privacy','completeness'].forEach(k=>fail(canonical(Object.keys(i.review[k]).sort())===canonical(Object.keys(r[k]).sort()),'审核字段变化。'));
      ['facts','rubrics'].forEach(k=>{
        fail(r[k].length===i.review[k].length,'审核行数变化。');
        r[k].forEach((x,j)=>{
          const old=i.review[k][j]; fail(canonical(Object.keys(old).sort())===canonical(Object.keys(x).sort()),'审核行字段变化。');
          (k==='facts'?['fact_id']:['criterion_id','capability','kind','critical','required']).forEach(f=>fail(canonical(x[f])===canonical(old[f]),'审核标识或静态字段变化。'));
        });
      });
    }); return review;
  }
  function preflight(p) {
    checkPacket(p); const errors=[]; const add=(ok,msg)=>{if(!ok)errors.push(msg);}; const nonempty=x=>typeof x==='string'&&x.trim().length>0;
    add(nonempty(p.reviewer_id),'请填写评审者编号。');
    for(const i of p.items){
      const r=i.review, turns=Object.fromEntries(i.turns.map(t=>[t.turn_id,t])); const prefix=i.candidate_id+'：';
      function decision(v,allowed,label){add(allowed.includes(v),prefix+label+'的状态不合法。');}
      function spans(rows,patient,index){add(Array.isArray(rows),prefix+'证据片段需为数组。');if(!Array.isArray(rows))return; for(const s of rows){const t=turns[s.turn_id];const chars=t?Array.from(t.content):[];add(!!t&&Number.isInteger(s.start)&&Number.isInteger(s.end)&&s.start>=0&&s.end>s.start&&s.end<=chars.length&&chars.slice(s.start,s.end).join('')===s.text,prefix+'证据片段与原文字符不一致。');if(patient)add(!!t&&t.role==='patient'&&t.source_turn_index===index,prefix+'事实证据必须来自对应的患者话轮。');}}
      function ids(arr){add(Array.isArray(arr)&&new Set(arr).size===arr.length&&arr.every(t=>turns[t]),prefix+'包含未知或重复轮次。');}
      decision(r.privacy.decision,['unreviewed','reviewed_no_identifiers','needs_redaction','excluded'],'隐私');
      decision(r.completeness.decision,['unreviewed','usable','insufficient','excluded'],'完整性');
      ids(r.privacy.checked_turn_ids);ids(r.completeness.evidence_turn_ids);spans(r.privacy.additional_spans,false);
      for(const k of ['privacy','completeness'])if(r[k].decision!=='unreviewed')add(nonempty(r[k].reason),prefix+k+'需要判断理由。');
      if(['reviewed_no_identifiers','needs_redaction'].includes(r.privacy.decision))add(r.privacy.checked_turn_ids.length===i.turns.length,prefix+'隐私审核需逐轮确认。');
      if(r.privacy.decision==='reviewed_no_identifiers')add(r.privacy.additional_spans.length===0,prefix+'无身份信息与所填敏感片段冲突。');
      if(r.privacy.decision==='needs_redaction')add(r.privacy.additional_spans.length>0,prefix+'请记录需脱敏片段。');
      if(r.completeness.decision!=='unreviewed')add(r.completeness.evidence_turn_ids.length>0,prefix+'完整性判断需要证据轮次。');
      r.facts.forEach((f,j)=>{
        const proposal=i.fact_draft.fact_candidates[j];decision(f.decision,['unreviewed','include','exclude','uncertain'],'事实');
        add([null,'present','absent','unknown','conflict'].includes(f.polarity),prefix+'事实极性无效。');add([null,true,false].includes(f.is_patient_assertion),prefix+'患者陈述状态无效。');
        add([null,'initial','on_question','scheduled','never'].includes(f.disclosure_policy),prefix+'披露方式无效。');
        if(f.decision!=='unreviewed')add(nonempty(f.reason),prefix+f.fact_id+'需要判断理由。');
        spans(f.evidence_spans,true,proposal.source_turn_index);
        if(f.disclosure_policy==='initial')add(proposal.in_opening_prefix===true,prefix+f.fact_id+'未来事实不能作为初始信息。');
        if(f.correction_of_candidate_id){const prev=i.fact_draft.fact_candidates.find(x=>x.candidate_id===f.correction_of_candidate_id);add(!!prev&&prev.source_turn_index<proposal.source_turn_index,prefix+'纠正必须指向更早的事实。');}
        if(f.decision==='include'){
          add(f.is_patient_assertion===true&&f.polarity!==null&&[f.subject,f.time,f.manual_groundsignal_slot].every(nonempty)&&f.evidence_spans.length>0&&f.disclosure_policy!==null,prefix+f.fact_id+'纳入所需信息不完整。');
          if(f.disclosure_policy==='on_question')add(Array.isArray(f.ask_patterns)&&f.ask_patterns.some(nonempty),prefix+'问询披露需要问询表达。');
          if(f.disclosure_policy==='scheduled')add(nonempty(f.disclosure_condition),prefix+'定时披露需要条件。');
        }
      });
      r.rubrics.forEach(q=>{
        decision(q.decision,['unreviewed','drafted','excluded'],'规则');decision(q.applicability,['unreviewed','applicable','not_applicable'],'适用性');
        if(q.decision!=='unreviewed'||q.applicability!=='unreviewed')add(nonempty(q.reason),prefix+q.criterion_id+'需要理由。');
        if(q.decision==='drafted')add(q.applicability==='applicable'&&[q.description,q.anchors['0'],q.anchors['1'],q.anchors['2'],q.opportunity.trigger,q.opportunity.deadline].every(nonempty)&&(!q.critical||nonempty(q.serious_error_definition)),prefix+q.criterion_id+'评分草案、分档标准或严重错误定义不完整。');
        if(q.decision==='excluded')add(q.applicability==='not_applicable',prefix+'排除规则需明确不适用。');
      });
    }return errors;
  }
  function compare(source,a,b){
    compatible(source,a);compatible(source,b);fail(a.reviewer_id&&b.reviewer_id&&a.reviewer_id.trim().toLowerCase()!==b.reviewer_id.trim().toLowerCase(),'需要两个不同的评审编号。');
    const differences=[],missing=[];
    function visit(x,y,path){if(x==='unreviewed'||y==='unreviewed'||x===null||y===null||x===''||y===''){missing.push(path);return;}if(Array.isArray(x)&&Array.isArray(y)&&x.length===y.length){x.forEach((v,n)=>visit(v,y[n],path+'.'+(v?.fact_id||v?.criterion_id||n)));return;}if(x&&y&&typeof x==='object'&&typeof y==='object'&&!Array.isArray(x)&&!Array.isArray(y)){for(const key of new Set([...Object.keys(x),...Object.keys(y)]))visit(x[key],y[key],path+'.'+key);return;}if(canonical(x)!==canonical(y))differences.push({path,a:clone(x),b:clone(y),decision:'unresolved',reason:''});}
    source.items.forEach((i,n)=>visit(a.items[n].review,b.items[n].review,i.candidate_id));
    return {schema_version:'clinical-console-comparison/v0.1',local_only:true,packet_sha256:source.packet_sha256,reviewer_ids:[a.reviewer_id,b.reviewer_id],comparison_kind:'literal_difference_not_clinical_agreement',differences,missing,...flags,s6_automatic_trust:'BLOCKED'};
  }
  function plans(p){return p.items.flatMap(i=>i.review.rubrics.map(r=>({candidate_id:i.candidate_id,criterion_id:r.criterion_id,status:'unreviewed',trigger:'',response:'',deadline:'',reason:''})));}
  const api={clone,canonical,flags,frozen,checkPacket,blank,compatible,preflight,compare,plans};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ConsoleCore=api;
})(globalThis);
