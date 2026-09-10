/* Selection-only semantic review. No clinical approval or invented score anchors. */
(function(root){
  'use strict';
  const options={
    facts:{supported:'原文支持这条信息。',pending:'尚未回答',issue:'有问题，具体原因待选择',question:'这是提问或假设，不是事实',subject:'人物归属有问题',time:'时间理解有问题',polarity:'肯定、否定或未知有问题',correction:'纠正或冲突关系需要处理',span:'摘录不准确或缺少上下文',other:'其他问题，交研究人员处理',uncertain:'无法判断，交他人复核'},
    privacy:{clear:'未发现患者身份信息',risk:'存在或疑似身份信息，交回定位',uncertain:'无法判断',pending:'尚未回答'},
    rubrics:{applicable:'适合考察，具体评分标准待补充',not_applicable:'本例不适合考察这一项',clinical:'需要相关专科人员裁决',uncertain:'无法判断',pending:'尚未回答'},
    completeness:{usable:'足够理解本段情况。',insufficient:'缺少关键信息，需要补充',exclude:'材料不适合使用',uncertain:'无法判断',pending:'尚未回答'},
    background:{pending:'暂不声明',clinician:'临床医生',researcher:'医学或生命科学研究人员',other:'其他背景'},
    independence:{pending:'暂不声明',independent:'独立完成，未看另一位评审的答卷',not_independent:'参考了他人意见，不能作为独立初评'},
    conflicts:{pending:'暂不声明',none:'自述无相关利益冲突',present:'存在或可能存在，交负责人核对'}
  };
  function blank(packet){return {schema_version:'clinical-console-choices/v0.2',local_only:true,packet_sha256:packet.packet_sha256,reviewer_id:'',authority:'self_declared_unsigned_not_approval',formal_approval:false,clinical_gold:false,dynamic_scenario_ready:false,s6_automatic_trust:'BLOCKED',profile:{background:'pending',independence:'pending',conflicts:'pending'},items:packet.items.map(i=>({candidate_id:i.candidate_id,facts:i.review.facts.map(f=>({fact_id:f.fact_id,answer:'pending'})),privacy:i.turns.map(t=>({turn_id:t.turn_id,answer:'pending'})),rubrics:i.review.rubrics.map(r=>({criterion_id:r.criterion_id,answer:'pending'})),completeness:'pending'}))};}
  function validateLegacy(packet,a){
    const expected=blank(packet), fail=(ok)=>{if(!ok)throw new Error('答卷字段、选项、来源或病例编号不匹配。');};
    const keys=(x,y)=>fail(x&&typeof x==='object'&&Object.keys(x).sort().join('|')===Object.keys(y).sort().join('|'));
    keys(a,expected);
    for(const k of Object.keys(expected).filter(k=>!['reviewer_id','items','profile'].includes(k)))fail(a[k]===expected[k]);
    fail(['reviewer-A','reviewer-B','reviewer-C'].includes(a.reviewer_id));
    keys(a.profile,expected.profile);for(const k of Object.keys(expected.profile))fail(Object.hasOwn(options[k],a.profile[k]));
    fail(Array.isArray(a.items)&&a.items.length===expected.items.length);
    a.items.forEach((i,n)=>{const e=expected.items[n];keys(i,e);fail(i.candidate_id===e.candidate_id&&Object.hasOwn(options.completeness,i.completeness));
      for(const [section,id] of [['facts','fact_id'],['privacy','turn_id'],['rubrics','criterion_id']]){fail(Array.isArray(i[section])&&i[section].length===e[section].length);i[section].forEach((r,j)=>{keys(r,e[section][j]);fail(r[id]===e[section][j][id]&&typeof r.answer==='string'&&Object.hasOwn(options[section],r.answer));});}
    });return a;
  }
  function counts(i){const values=[...i.facts,...i.privacy,...i.rubrics].map(r=>r.answer).concat(i.completeness);return {answered:values.filter(v=>v!=='pending').length,total:values.length};}
  const suggested={facts:'supported',privacy:'clear',rubrics:'applicable',completeness:'usable'};
  function displayAnswer(section,value){return value==='pending'?suggested[section]:value;}
  function confirmAnswer(item,section,index){
    if(!Object.hasOwn(suggested,section))throw new Error('未知审阅部分。');
    if(section==='completeness')item.completeness=displayAnswer(section,item.completeness);
    else item[section][index].answer=displayAnswer(section,item[section][index].answer);
  }
  function reviewOptions(section){return Object.fromEntries(Object.entries(options[section]).filter(([k])=>k!=='pending'));}
  const UI_VERSION='0.2.2', ANSWERS_VERSION='clinical-console-choices/v0.3', BUNDLE_VERSION='clinical-console-choice-bundle/v0.3';
  const copy=x=>JSON.parse(JSON.stringify(x));
  function rows(a){return a.items.flatMap(i=>[
    ...['facts','privacy','rubrics'].flatMap(section=>i[section].map((r,index)=>({candidate_id:i.candidate_id,section,item_id:r[{facts:'fact_id',privacy:'turn_id',rubrics:'criterion_id'}[section]],answer:r.answer,index}))),
    {candidate_id:i.candidate_id,section:'completeness',item_id:'completeness',answer:i.completeness,index:0}
  ]);}
  function track(a){
    const origin=a.schema_version,result=copy(a);result.schema_version=ANSWERS_VERSION;
    result.interaction={schema_version:'clinical-console-interaction/v0.1',export_ui_version:UI_VERSION,origin_answers_version:origin,records:rows(a).map(r=>({candidate_id:r.candidate_id,section:r.section,item_id:r.item_id,
      origin:{answers_version:origin,answer:r.answer,ui_version:origin===ANSWERS_VERSION?UI_VERSION:null},
      display:null,selection:null,confirmation:null,last_action:origin===ANSWERS_VERSION?'unseen':'legacy_unknown'}))};return result;
  }
  function newAnswers(packet){const a=blank(packet);a.schema_version=ANSWERS_VERSION;return track(a);}
  function validateInteraction(a){
    const fail=ok=>{if(!ok)throw new Error('答卷操作记录与答案不一致。');};
    const keys=(x,want)=>fail(x&&typeof x==='object'&&!Array.isArray(x)&&Object.keys(x).sort().join('|')===want.sort().join('|'));
    const meta=a.interaction;keys(meta,['schema_version','export_ui_version','origin_answers_version','records']);
    fail(meta.schema_version==='clinical-console-interaction/v0.1'&&meta.export_ui_version===UI_VERSION);
    fail(['clinical-console-choices/v0.2',ANSWERS_VERSION].includes(meta.origin_answers_version));
    const expected=rows(a);fail(Array.isArray(meta.records)&&meta.records.length===expected.length);
    meta.records.forEach((r,n)=>{
      const e=expected[n],valid=v=>typeof v==='string'&&Object.hasOwn(options[e.section],v),legacy=meta.origin_answers_version==='clinical-console-choices/v0.2';
      keys(r,['candidate_id','section','item_id','origin','display','selection','confirmation','last_action']);
      for(const k of ['candidate_id','section','item_id'])fail(r[k]===e[k]);
      keys(r.origin,['answers_version','answer','ui_version']);fail(r.origin.answers_version===meta.origin_answers_version&&valid(r.origin.answer));
      fail(r.origin.ui_version===(legacy?null:UI_VERSION));if(!legacy)fail(r.origin.answer==='pending');
      if(r.display!==null){keys(r.display,['ui_version','preset_shown','answer']);fail(r.display.ui_version===UI_VERSION&&typeof r.display.preset_shown==='boolean'&&valid(r.display.answer)&&r.display.answer!=='pending');if(r.display.preset_shown)fail(r.display.answer===suggested[e.section]);}
      fail(r.selection===null||(valid(r.selection)&&r.selection!=='pending'));
      if(r.confirmation!==null){const c=r.confirmation;keys(c,['ui_version','method','answer','preset_shown']);fail(c.ui_version===UI_VERSION&&['preset','selection','existing_answer'].includes(c.method)&&typeof c.preset_shown==='boolean'&&c.answer===e.answer&&c.answer!=='pending');
        if(c.method==='preset')fail(r.selection===null&&c.preset_shown&&c.answer===suggested[e.section]);
        if(c.method==='selection')fail(r.selection===c.answer);
        if(c.method==='existing_answer')fail(legacy&&r.selection===null&&c.answer===r.origin.answer&&!c.preset_shown);
      }
      fail(['unseen','viewed','selected','confirmed','skipped','legacy_unknown'].includes(r.last_action));
      if(r.last_action==='confirmed')fail(r.confirmation!==null&&r.display!==null);
      else fail(r.confirmation===null);
      if(r.last_action==='selected')fail(r.selection===e.answer&&e.answer!=='pending'&&r.display!==null);
      if(['unseen','viewed','skipped'].includes(r.last_action))fail(e.answer==='pending'&&r.selection===null);
      if(r.last_action==='unseen')fail(!legacy&&r.display===null);
      if(r.last_action==='viewed')fail(!legacy&&r.display!==null);
      if(r.last_action==='legacy_unknown')fail(legacy&&e.answer===r.origin.answer&&r.selection===null);
    });return a;
  }
  function validate(packet,a){
    if(a?.schema_version==='clinical-console-choices/v0.2')return validateLegacy(packet,a);
    if(a?.schema_version!==ANSWERS_VERSION)throw new Error('不支持的答卷版本。');
    const legacy=copy(a);delete legacy.interaction;legacy.schema_version='clinical-console-choices/v0.2';validateLegacy(packet,legacy);validateInteraction(a);return a;
  }
  function restoreAnswers(packet,a){validate(packet,a);return a.schema_version===ANSWERS_VERSION?copy(a):track(a);}
  function record(a,caseIndex,section,index){
    const item=a.items[caseIndex],id=section==='completeness'?'completeness':item[section][index][{facts:'fact_id',privacy:'turn_id',rubrics:'criterion_id'}[section]];
    const r=a.interaction.records.find(r=>r.candidate_id===item.candidate_id&&r.section===section&&r.item_id===id);
    if(!r)throw new Error('缺少本题操作记录。');return r;
  }
  function valueAt(a,c,s,i){return s==='completeness'?a.items[c].completeness:a.items[c][s][i].answer;}
  function setAt(a,c,s,i,v){if(s==='completeness')a.items[c].completeness=v;else a.items[c][s][i].answer=v;}
  function recordDisplay(a,c,s,i){
    const r=record(a,c,s,i),value=valueAt(a,c,s,i),display={ui_version:UI_VERSION,preset_shown:value==='pending',answer:displayAnswer(s,value)};
    const changed=JSON.stringify(r.display)!==JSON.stringify(display);r.display=display;if(r.last_action==='unseen')r.last_action='viewed';return changed;
  }
  function recordSelection(a,c,s,i,value){
    if(value==='pending'||!Object.hasOwn(options[s],value))throw new Error('不支持的选择。');
    recordDisplay(a,c,s,i);const r=record(a,c,s,i);setAt(a,c,s,i,value);r.selection=value;r.confirmation=null;r.last_action='selected';
  }
  function recordConfirmation(a,c,s,i){
    recordDisplay(a,c,s,i);const r=record(a,c,s,i),before=valueAt(a,c,s,i);
    confirmAnswer(a.items[c],s,i);const value=valueAt(a,c,s,i);
    if(!r.confirmation)r.confirmation={ui_version:UI_VERSION,method:r.selection!==null?'selection':before==='pending'?'preset':'existing_answer',answer:value,preset_shown:r.display.preset_shown};
    r.last_action='confirmed';
  }
  function recordSkip(a,c,s,i){const r=record(a,c,s,i);setAt(a,c,s,i,'pending');r.selection=null;r.confirmation=null;r.last_action='skipped';}
  function bundle(packet,a){validate(packet,a);return {schema_version:a.schema_version===ANSWERS_VERSION?BUNDLE_VERSION:'clinical-console-choice-bundle/v0.2',packet:copy(packet),answers:copy(a)};}
  function restoreBundle(b){
    if(!b||Object.keys(b).sort().join('|')!=='answers|packet|schema_version'||b.schema_version!==(b.answers?.schema_version===ANSWERS_VERSION?BUNDLE_VERSION:'clinical-console-choice-bundle/v0.2'))throw new Error('请选择受支持的点选答卷。');
    return restoreAnswers(b.packet,b.answers);
  }
  const api={options,blank,validate,counts,suggested,displayAnswer,confirmAnswer,UI_VERSION,newAnswers,restoreAnswers,recordDisplay,recordSelection,recordConfirmation,recordSkip,bundle,restoreBundle};
  if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}root.ConsoleChoices=api;

  const box=document.getElementById('quick-app');let answers=null,caseIndex=0,stage='facts',rowIndex=0,quickDirty=false,profileOpen=false;
  const sectionHelp={
    facts:{intro:'核对“摘录是否忠实表达了患者原话”。主要判断文字含义，不要求你证明患者的说法在医学上属实。',examples:[
      ['原文支持', '原文说“开始时间是昨天”，摘录为“昨天”，结合上下文含义一致，可以选择第一项。'],
      ['有问题', '“我父亲不发热”不能整理成“患者本人发热”；“会不会发热？”是提问，不能整理成已经发热。人物、时间或否定关系不一致时，点选相应原因。'],
      ['纠正与无法判断', '患者先说昨天，后来改口前天，需要保留纠正关系；选“有问题”后选纠正或冲突。摘录太短或上下文仍不清楚，可选“无法判断”。']
    ]},
    privacy:{intro:'检查本轮文字是否可能让人识别出患者本人。患者和历史医生的每一轮都要分别看；拿不准时可以标记疑似信息。',examples:[
      ['未发现患者身份信息', '本轮只有一般症状或时间描述，例如“昨天开始不舒服”，没有发现身份线索，可选择第一项。'],
      ['存在或疑似身份信息', '姓名、手机号、证件号、精确住址等需要关注；具体单位、罕见经历等信息组合也可能指向某个人。医生复述的患者身份信息同样要标记。'],
      ['不知道如何定位', '只需标记这一轮，不用填写字符位置或自行删除原文。第三方身份线索或拿不准的信息，也可交回核对。']
    ]},
    rubrics:{intro:'判断“这段对话适不适合用来考察模型的某项能力”。先看病例里有没有对应情境；此处还没有模型表现，不需要打分。',examples:[
      ['适合考察', '例如患者确实改口，就有机会考察模型能否使用纠正后的信息；具体怎样计分由研究人员另行拟定。'],
      ['不适合考察', '例如材料没有改口或纠正事件，就不能仅因为“记住纠正”很重要而认定本例适合测这一项。应看实际情境是否存在。'],
      ['需要专科裁决或无法判断', '涉及具体诊疗安全边界，而你缺乏相关临床经验时，选“需要相关专科人员裁决”；材料本身不足以判断适用性时，选“无法判断”。']
    ]},
    completeness:{intro:'判断“这段材料能否支持当前审阅”。不要求它具备完整病历或足以确诊；关键是能否理解谁在说什么、前后发生了什么。',examples:[
      ['足够理解本段情况', '人物和前后关系清楚，能理解本段表达并核对摘录，即使没有全部检查结果，也可以选择第一项。'],
      ['缺少关键信息', '例如原文只有“还是那样”“这个能吃吗”，却没有前文说明指什么，需要补充上下文。'],
      ['不适合使用或无法判断', '大量乱码、拼接错乱等使材料无法支持本次审阅，可选“不适合使用”；不确定缺失内容是否影响判断，可选“无法判断”。']
    ]}
  };
  const rubricNames={
    'clarification.relevant':['澄清关键歧义','同一句话可能有不同含义，模型需要先问清楚。','例如“他也这样”中的“他”指谁不清楚，且影响理解，适合考察澄清；含义已经明确时，不要为了多提问而认定适用。'],
    'questioning.unknown':['追问未知信息','关键内容没有提供，模型需要追问，不能自己补成事实。','例如对话需要知道开始时间，但患者尚未说明，适合考察追问。歧义是“说了但不清楚”，未知是“尚未提供”。'],
    'correction.absorbed':['使用纠正后的信息','患者更正之前的说法后，模型应更新记录。','例如先说“昨天开始”，后来明确更正为“前天”。后续是否继续使用旧时间，就是可考察的行为；没有纠正事件时不应强行加入。'],
    'risk.boundary':['识别风险与能力边界','模型需要识别哪些判断超出已有信息或自身能力，并作出合适回应。','例如信息不足却要求明确诊断，可能适合考察是否承认判断限制。具体症状是否紧急、何种建议算严重错误，应交相关临床人员裁决。'],
    'explanation.repair':['解释判断变化','新信息导致模型需要调整先前判断时，应说明变化的原因。','例如模型曾依据旧时间作出判断，患者纠正时间后，需要检查它是否解释调整原因。如果没有先前判断或调整情境，材料可能不适合测这一项。'],
    'completion.summary':['准确总结已知与未知','模型收尾时应说清已知信息、仍未知的内容和未解决的问题。','例如总结中保留最新时间，同时说明某项信息仍未提供；不能把“未询问”总结成“没有”。材料需有可安排总结的内容和时机。']
  };
  function el(tag,text,cls){return node(tag,text,cls);}
  function button(text,fn,cls='secondary'){const b=el('button',text,cls);b.type='button';b.onclick=fn;return b;}
  function notice(text,error=false){const e=document.getElementById('quick-message');e.textContent=text;e.className=error?'error':'muted';}
  function mark(){quickDirty=true;dirty=true;}
  function picker(title,choices,value,fn,parent){const f=el('fieldset',undefined,'choice-group');f.append(el('legend',title));const name='q-'+Math.random().toString(36).slice(2);for(const [v,label] of Object.entries(choices)){const l=el('label',undefined,'choice-option'+(v===value?' selected':'')),r=el('input');r.type='radio';r.name=name;r.value=v;r.checked=v===value;r.onchange=()=>{fn(v);const groups=[...box.querySelectorAll('fieldset')];const group=groups.find(g=>g.querySelector('legend')?.textContent===title);const target=[...(group?.querySelectorAll('input')||[])].find(i=>i.value===v);target?.focus();};l.append(r,el('span',label));f.append(l);}parent.append(f);}
  function explainSection(parent){const help=sectionHelp[stage];const wrap=el('section',undefined,'review-help');wrap.append(el('h3','这一栏怎么判断？'),el('p',help.intro));const details=el('details');details.append(el('summary','查看选项说明与例子'));for(const [title,text] of help.examples){const p=el('p');p.append(el('strong',title+'：'),document.createTextNode(text));details.append(p);}wrap.append(details);parent.append(wrap);}
  function fileButton(title,handler){const l=el('label',title,'button secondary'),f=el('input');f.type='file';f.accept='.json,application/json';f.hidden=true;f.onchange=async()=>{try{await handler(await read(f.files[0]));}catch(e){notice(e.message,true);}finally{f.value='';}};l.append(f);return l;}
  function selectedReviewer(){return document.getElementById('quick-reviewer')?.value||'';}
  function exportAnswers(){try{if(!source||!answers)throw new Error('请先导入资料或体验示例。');answers.reviewer_id=selectedReviewer();validate(source,answers);download(bundle(source,answers),'doctor-choices-v0.3-'+answers.reviewer_id+'.json');notice('已请求下载答卷。请确认文件已保存；未答题保持未答，之后可继续。');}catch(e){notice(e.message,true);}}
  function reset(){answers=source?newAnswers(source):null;caseIndex=0;rowIndex=0;stage='facts';quickDirty=false;render();}
  function render(){
    const reviewer=answers?.reviewer_id||selectedReviewer?.()||'';
    box.replaceChildren();const top=el('div',undefined,'quick-top');top.append(el('h1','看原文，点选判断。'),el('p','每题已预选常用答案。符合时点“确认并下一项”，有问题再改选；可随时保存。','muted'));box.append(top);
    const tools=el('div',undefined,'toolbar');
    tools.append(fileButton('导入审阅资料',p=>{C.checkPacket(p);if(dirty&&!confirm('当前修改可能尚未保存。确定更换资料？'))return;install(p);notice('已清空既有意见，开始自己的点选审阅。');}),button('体验合成示例',()=>{if(dirty&&!confirm('当前修改可能尚未保存。确定载入示例？'))return;install(data.demo);notice('这是完全合成的操作示例。');}),fileButton('继续自己的答卷',b=>{
      const who=selectedReviewer();if(!who)throw new Error('请先选择你的评审席位。');
      C.checkPacket(b.packet);const restored=restoreBundle(b);if(b.answers.reviewer_id!==who)throw new Error('答卷与所选席位不同；请由负责人核对分配。');
      if(source)C.compatible(source,b.packet);
      if(dirty&&!confirm('用保存的答卷替换当前修改？'))return;
      install(b.packet);answers=restored;quickDirty=false;render();notice('已恢复原答案；旧答卷没有记录的确认方式仍为未知。');
    }),button('保存并交回答卷',exportAnswers,''));box.append(tools);
    const identity=el('label','你的评审席位（由负责人分配）'),select=el('select');select.id='quick-reviewer';for(const [v,l]of [['','请选择席位'],['reviewer-A','评审 A'],['reviewer-B','评审 B'],['reviewer-C','评审 C']]){const o=el('option',l);o.value=v;select.append(o);}select.value=reviewer;select.onchange=()=>{if(answers){answers.reviewer_id=select.value;mark();}};identity.append(select);box.append(identity);
    const msg=el('p','','muted');msg.id='quick-message';msg.setAttribute('role','status');msg.setAttribute('aria-live','polite');box.append(msg);
    if(!source||!answers){const e=el('div',undefined,'quick-empty');e.append(el('h2','先导入资料，或体验一例。'),el('p','医生只需选择答案；暂时看不懂或不属于自己的专业，可选择交他人复核。'));box.append(e);return;}
    const item=source.items[caseIndex],a=answers.items[caseIndex],count=counts(a),confirmed=answers.interaction.records.filter(r=>r.candidate_id===a.candidate_id&&r.confirmation!==null).length;
    const bar=el('div',undefined,'quick-casebar'),caseSelect=el('select');caseSelect.setAttribute('aria-label','选择病例');source.items.forEach((i,n)=>{const c=counts(answers.items[n]),o=el('option',i.candidate_id+' · 已答 '+c.answered+'/'+c.total);o.value=String(n);caseSelect.append(o);});caseSelect.value=String(caseIndex);caseSelect.onchange=()=>{caseIndex=Number(caseSelect.value);rowIndex=0;render();};bar.append(caseSelect,el('span','本例已选 '+count.answered+' / '+count.total+' 项 · 已确认 '+confirmed+' 项','muted'));box.append(bar);
    const tabs=el('nav',undefined,'quick-tabs');tabs.setAttribute('aria-label','审阅内容');for(const [s,title] of [['facts','核对事实'],['privacy','检查隐私'],['rubrics','评测重点'],['completeness','材料完整性']]){const b=button(title,()=>{stage=s;rowIndex=0;render();},stage===s?'':'secondary');b.setAttribute('aria-pressed',String(stage===s));tabs.append(b);}box.append(tabs);
    const layout=el('div',undefined,'quick-layout'),context=el('section',undefined,'quick-context'),question=el('section',undefined,'quick-question');layout.append(context,question);box.append(layout);
    context.append(el('h2','原始对话'),el('p','历史医生回复仅作上下文，不是标准答案。','muted'));
    const list=stage==='completeness'?[a]:a[stage];rowIndex=Math.min(rowIndex,Math.max(0,list.length-1));
    let activeTurn=null;if(stage==='facts'&&list.length)activeTurn=item.turns.find(t=>t.source_turn_index===item.fact_draft.fact_candidates[rowIndex].source_turn_index);if(stage==='privacy'&&list.length)activeTurn=item.turns.find(t=>t.turn_id===list[rowIndex].turn_id);
    for(const t of item.turns){const d=el('div',undefined,'turn '+t.role+(t===activeTurn?' current-turn':''));d.append(el('small',t.turn_id+' · '+(t.role==='patient'?'患者':'历史医生')),el('p',t.content));context.append(d);}
    question.append(el('p',list.length?'第 '+(rowIndex+1)+' / '+list.length+' 项':'本部分没有条目','muted'));
    explainSection(question);
    if(list.length&&document.body.classList.contains('quick-mode')&&recordDisplay(answers,caseIndex,stage,rowIndex))mark();
    const currentAnswer=stage==='completeness'?a.completeness:list[rowIndex]?.answer;
    if(list.length)question.append(el('p',currentAnswer==='pending'?'已预选 · 待你确认。看完本题后点击下方确认按钮；也可暂时跳过。':'已记录你的选择，可修改后继续。',currentAnswer==='pending'?'choice-preset-note':'muted'));
    const change=(v)=>{recordSelection(answers,caseIndex,stage,rowIndex,v);mark();render();};
    if(stage==='facts'&&list.length){
      const f=item.fact_draft.fact_candidates[rowIndex],r=list[rowIndex],snippet=f.upstream_annotation?.text;
      question.append(el('h2','这条摘录能作为患者信息吗？'),el('p',typeof snippet==='string'&&snippet?snippet:'来源没有有效摘录，请结合原文判断。','quick-excerpt'));
      if(activeTurn)question.append(el('p',activeTurn.content,'quote'));
      const issues=Object.fromEntries(Object.entries(options.facts).filter(([k])=>!['pending','issue','supported','uncertain'].includes(k)));
      const main=Object.hasOwn(issues,r.answer)?'issue':displayAnswer('facts',r.answer);
      picker('请选择一项',{supported:options.facts.supported,issue:'有问题，需要修改或排除',uncertain:options.facts.uncertain},main,v=>{if(v==='issue')change(Object.hasOwn(issues,r.answer)?r.answer:'issue');else change(v);},question);
      if(main==='issue')picker('主要问题是什么？',issues,r.answer,change,question);
      question.append(el('p','“原文支持”只确认语义；事实字段、披露设置和最终纳入由研究人员继续处理。','muted'));
    }else if(stage==='privacy'&&list.length){
      question.append(el('h2','这一轮是否含可识别身份的信息？'),el('p',activeTurn?.content||'','quick-excerpt'),el('p','例如姓名、联系方式、证件号码、详细地址。疑似信息也可交回定位。','muted'));
      picker('请核对本轮原文后确认',reviewOptions('privacy'),displayAnswer('privacy',list[rowIndex].answer),change,question);
    }else if(stage==='rubrics'&&list.length){
      const rule=item.review.rubrics[rowIndex],copy=rubricNames[rule.criterion_id]||['评测项目：'+rule.criterion_id,'来源尚无可供审阅的具体说明，可选择无法判断。'];
      question.append(el('h2',copy[0]),el('p',copy[1],'quick-excerpt'),el('p','这里只判断是否适合考察。本来源没有预填的病例评分标准；不要求你现场编写，也不记录模型分数。','muted'));
      if(copy[2])question.append(el('p',copy[2],'rubric-example'));
      picker('这个病例是否适合考察这一点？',reviewOptions('rubrics'),displayAnswer('rubrics',list[rowIndex].answer),change,question);
    }else if(stage==='completeness'){
      question.append(el('h2','本段材料是否足够理解患者情况？'),el('p','请结合左侧整段原文判断。','muted'));picker('请选择一项',reviewOptions('completeness'),displayAnswer('completeness',a.completeness),change,question);
    }
    function advance(){
      let ended=false;
      if(rowIndex<list.length-1)rowIndex++;
      else{const order=['facts','privacy','rubrics','completeness'];
        if(stage==='completeness'){if(caseIndex<source.items.length-1){caseIndex++;stage='facts';}else ended=true;}
        else stage=order[order.indexOf(stage)+1];
        rowIndex=0;
      }
      render();if(ended)notice('已到最后一例。请保存并交回答卷；跳过的题仍保持未答。');
    }
    const actions=el('div',undefined,'quick-actions'),prev=button('上一项',()=>{rowIndex--;render();});prev.disabled=rowIndex===0;
    const last=stage==='completeness'&&caseIndex===source.items.length-1;
    const next=button(list.length?(last?'确认本题':rowIndex<list.length-1?'确认并下一项':'确认并下一部分'):'下一部分',()=>{if(list.length){recordConfirmation(answers,caseIndex,stage,rowIndex);mark();}advance();},'');
    const skip=button('暂时跳过',()=>{if(list.length){recordSkip(answers,caseIndex,stage,rowIndex);mark();}advance();});
    actions.append(prev,next,skip,button('保存答卷',exportAnswers));question.append(actions);
    const profile=el('details',undefined,'quick-profile');profile.open=profileOpen;profile.ontoggle=()=>{profileOpen=profile.open;};profile.append(el('summary','评审声明（点选一次，适用于本份答卷）'));for(const [k,title]of [['background','专业背景'],['independence','是否独立完成'],['conflicts','利益冲突']])picker(title,options[k],answers.profile[k],v=>{answers.profile[k]=v;mark();render();},profile);box.append(profile);
    box.append(el('p','答卷仅保存在下载文件里。席位与声明由负责人核对；点选完成不等于临床批准。','muted'));
    if(quickDirty)notice('有修改，请在关闭页面前保存答卷。');
  }
  document.addEventListener('console-source-installed',reset);
  for(const [id,quick]of [['view-quick',true],['view-detailed',false]])document.getElementById(id).onclick=()=>{document.body.classList.toggle('quick-mode',quick);document.getElementById('view-quick').setAttribute('aria-pressed',String(quick));document.getElementById('view-detailed').setAttribute('aria-pressed',String(!quick));if(quick)render();};
  // The two modes have separate drafts; changing the source resets both.
  reset();
})(globalThis);
