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
  function validate(packet,a){
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
  const api={options,blank,validate,counts,suggested,displayAnswer,confirmAnswer};
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
  function exportAnswers(){try{if(!source||!answers)throw new Error('请先导入资料或体验示例。');answers.reviewer_id=selectedReviewer();validate(source,answers);download({schema_version:'clinical-console-choice-bundle/v0.2',packet:C.clone(source),answers:C.clone(answers)},'doctor-choices-'+answers.reviewer_id+'.json');notice('已请求下载答卷。请确认文件已保存；未答题保持未答，之后可继续。');}catch(e){notice(e.message,true);}}
  function reset(){answers=source?blank(source):null;caseIndex=0;rowIndex=0;stage='facts';quickDirty=false;render();}
  function render(){
    const reviewer=answers?.reviewer_id||selectedReviewer?.()||'';
    box.replaceChildren();const top=el('div',undefined,'quick-top');top.append(el('h1','看原文，点选判断。'),el('p','每题已预选常用答案。符合时点“确认并下一项”，有问题再改选；可随时保存。','muted'));box.append(top);
    const tools=el('div',undefined,'toolbar');
    tools.append(fileButton('导入审阅资料',p=>{C.checkPacket(p);if(dirty&&!confirm('当前修改可能尚未保存。确定更换资料？'))return;install(p);notice('已清空既有意见，开始自己的点选审阅。');}),button('体验合成示例',()=>{if(dirty&&!confirm('当前修改可能尚未保存。确定载入示例？'))return;install(data.demo);notice('这是完全合成的操作示例。');}),fileButton('继续自己的答卷',b=>{
      const who=selectedReviewer();if(!who)throw new Error('请先选择你的评审席位。');
      if(b.schema_version!=='clinical-console-choice-bundle/v0.2')throw new Error('请选择点选版导出的答卷。');
      C.checkPacket(b.packet);validate(b.packet,b.answers);if(b.answers.reviewer_id!==who)throw new Error('答卷与所选席位不同；请由负责人核对分配。');
      if(source)C.compatible(source,b.packet);
      if(dirty&&!confirm('用保存的答卷替换当前修改？'))return;
      install(b.packet);answers=C.clone(b.answers);quickDirty=false;render();notice('已恢复原答卷，未回答的题仍留空。');
    }),button('保存并交回答卷',exportAnswers,''));box.append(tools);
    const identity=el('label','你的评审席位（由负责人分配）'),select=el('select');select.id='quick-reviewer';for(const [v,l]of [['','请选择席位'],['reviewer-A','评审 A'],['reviewer-B','评审 B'],['reviewer-C','评审 C']]){const o=el('option',l);o.value=v;select.append(o);}select.value=reviewer;select.onchange=()=>{if(answers){answers.reviewer_id=select.value;mark();}};identity.append(select);box.append(identity);
    const msg=el('p','','muted');msg.id='quick-message';msg.setAttribute('role','status');msg.setAttribute('aria-live','polite');box.append(msg);
    if(!source||!answers){const e=el('div',undefined,'quick-empty');e.append(el('h2','先导入资料，或体验一例。'),el('p','医生只需选择答案；暂时看不懂或不属于自己的专业，可选择交他人复核。'));box.append(e);return;}
    const item=source.items[caseIndex],a=answers.items[caseIndex],count=counts(a);
    const bar=el('div',undefined,'quick-casebar'),caseSelect=el('select');caseSelect.setAttribute('aria-label','选择病例');source.items.forEach((i,n)=>{const c=counts(answers.items[n]),o=el('option',i.candidate_id+' · 已答 '+c.answered+'/'+c.total);o.value=String(n);caseSelect.append(o);});caseSelect.value=String(caseIndex);caseSelect.onchange=()=>{caseIndex=Number(caseSelect.value);rowIndex=0;render();};bar.append(caseSelect,el('span','本例已答 '+count.answered+' / '+count.total+' 项','muted'));box.append(bar);
    const tabs=el('nav',undefined,'quick-tabs');tabs.setAttribute('aria-label','审阅内容');for(const [s,title] of [['facts','核对事实'],['privacy','检查隐私'],['rubrics','评测重点'],['completeness','材料完整性']]){const b=button(title,()=>{stage=s;rowIndex=0;render();},stage===s?'':'secondary');b.setAttribute('aria-pressed',String(stage===s));tabs.append(b);}box.append(tabs);
    const layout=el('div',undefined,'quick-layout'),context=el('section',undefined,'quick-context'),question=el('section',undefined,'quick-question');layout.append(context,question);box.append(layout);
    context.append(el('h2','原始对话'),el('p','历史医生回复仅作上下文，不是标准答案。','muted'));
    const list=stage==='completeness'?[a]:a[stage];rowIndex=Math.min(rowIndex,Math.max(0,list.length-1));
    let activeTurn=null;if(stage==='facts'&&list.length)activeTurn=item.turns.find(t=>t.source_turn_index===item.fact_draft.fact_candidates[rowIndex].source_turn_index);if(stage==='privacy'&&list.length)activeTurn=item.turns.find(t=>t.turn_id===list[rowIndex].turn_id);
    for(const t of item.turns){const d=el('div',undefined,'turn '+t.role+(t===activeTurn?' current-turn':''));d.append(el('small',t.turn_id+' · '+(t.role==='patient'?'患者':'历史医生')),el('p',t.content));context.append(d);}
    question.append(el('p',list.length?'第 '+(rowIndex+1)+' / '+list.length+' 项':'本部分没有条目','muted'));
    explainSection(question);
    const currentAnswer=stage==='completeness'?a.completeness:list[rowIndex]?.answer;
    if(list.length)question.append(el('p',currentAnswer==='pending'?'已预选 · 待你确认。看完本题后点击下方确认按钮；也可暂时跳过。':'已记录你的选择，可修改后继续。',currentAnswer==='pending'?'choice-preset-note':'muted'));
    const change=(v)=>{if(stage==='completeness')a.completeness=v;else list[rowIndex].answer=v;mark();render();};
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
    const next=button(list.length?(last?'确认本题':rowIndex<list.length-1?'确认并下一项':'确认并下一部分'):'下一部分',()=>{if(list.length){confirmAnswer(a,stage,rowIndex);mark();}advance();},'');
    const skip=button('暂时跳过',()=>{if(list.length){if(stage==='completeness')a.completeness='pending';else list[rowIndex].answer='pending';mark();}advance();});
    actions.append(prev,next,skip,button('保存答卷',exportAnswers));question.append(actions);
    const profile=el('details',undefined,'quick-profile');profile.open=profileOpen;profile.ontoggle=()=>{profileOpen=profile.open;};profile.append(el('summary','评审声明（点选一次，适用于本份答卷）'));for(const [k,title]of [['background','专业背景'],['independence','是否独立完成'],['conflicts','利益冲突']])picker(title,options[k],answers.profile[k],v=>{answers.profile[k]=v;mark();render();},profile);box.append(profile);
    box.append(el('p','答卷仅保存在下载文件里。席位与声明由负责人核对；点选完成不等于临床批准。','muted'));
    if(quickDirty)notice('有修改，请在关闭页面前保存答卷。');
  }
  document.addEventListener('console-source-installed',reset);
  for(const [id,quick]of [['view-quick',true],['view-detailed',false]])document.getElementById(id).onclick=()=>{document.body.classList.toggle('quick-mode',quick);document.getElementById('view-quick').setAttribute('aria-pressed',String(quick));document.getElementById('view-detailed').setAttribute('aria-pressed',String(!quick));};
  // The two modes have separate drafts; changing the source resets both.
  reset();
})(globalThis);
