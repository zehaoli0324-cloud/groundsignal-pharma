(function(){
'use strict';
const OPTIONS={facts:{supported:'原文支持这条信息。',issue:'有问题，原因待补充',question:'这是提问或假设',subject:'人物归属有问题',time:'时间理解有问题',polarity:'肯定、否定或未知有问题',correction:'纠正或冲突关系有问题',span:'摘录或上下文有问题',other:'其他问题',uncertain:'无法判断'},privacy:{clear:'未发现患者身份信息',risk:'存在或疑似身份信息',uncertain:'无法判断'},rubrics:{applicable:'适合考察，具体评分标准待补充',not_applicable:'不适合考察',clinical:'需要相关专科人员裁决',uncertain:'无法判断'},completeness:{usable:'足够理解本段情况。',insufficient:'缺少关键信息',exclude:'不适合使用',uncertain:'无法判断'}};
const STATUS={disagreement:'已确认分歧',agreed:'已确认一致',missing_answer:'缺少回答',confirmation_required:'需要原评审确认'};
const SECTION={facts:'核对事实',privacy:'检查隐私',rubrics:'评测重点',completeness:'材料完整性'};
const REASONS=['原文直接支持所选判断。','另一项判断超出了原文提供的信息。','应保留未知或不确定性。','需要相关专科人员进一步判断。','其他理由'];
function insist(ok,msg){if(!ok)throw Error(msg);}
function validateDraft(data,draft){
 const t=data.template;insist(draft&&typeof draft==='object'&&JSON.stringify(Object.keys(draft).sort())===JSON.stringify(Object.keys(t).sort()),'裁决文件字段不匹配');
 for(const k of Object.keys(t).filter(k=>!['adjudicator_id','decisions'].includes(k)))insist(draft[k]===t[k],'文件对应的答卷或版本已改变');
 insist(typeof draft.adjudicator_id==='string'&&draft.adjudicator_id.trim(),'请填写协调者姓名或编号');
 insist(Array.isArray(draft.decisions),'裁决列表格式不正确');const seen=new Set();
 for(const d of draft.decisions){insist(d&&JSON.stringify(Object.keys(d).sort())===JSON.stringify(['answer','reason','row_id']),'裁决字段不正确');const row=data.queue.rows.find(r=>r.row_id===d.row_id);
 insist(row&&row.status==='disagreement'&&!seen.has(d.row_id),'包含重复项或不能裁决的题目');seen.add(d.row_id);
 insist(typeof d.answer==='string'&&Object.hasOwn(OPTIONS[row.section],d.answer),'选项不正确');insist(typeof d.reason==='string'&&d.reason.trim(),'请补充裁决理由');}
 return JSON.parse(JSON.stringify(draft));
}
function exportDraft(data,actor,decisions){return validateDraft(data,{...data.template,adjudicator_id:actor,decisions:Object.values(decisions)});}
if(typeof module!=='undefined')module.exports={validateDraft,exportDraft,OPTIONS};
if(typeof document==='undefined')return;
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);
if(data.original.source_binding?.synthetic===true)document.querySelector('h1').textContent='分歧裁决 · 合成示例';
let decisions={},filter='disagreement',index=0;
function el(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
function label(s,v){return v==='pending'?'尚未作答':OPTIONS[s][v];}
function selectedRows(){return data.queue.rows.filter(r=>r.status===filter);}
function message(t){$('message').textContent=t;}
function render(){
 const rows=selectedRows();index=Math.max(0,Math.min(index,rows.length-1));
 $('counts').textContent='已确认裁决 '+Object.keys(decisions).length+' / '+(data.queue.counts.disagreement||0);
 $('nav').replaceChildren();for(const [status,name] of Object.entries(STATUS)){const b=el('button',name+' · '+(data.queue.counts[status]||0));b.className=status===filter?'active':'';b.onclick=()=>{filter=status;index=0;render();};$('nav').append(b);}
 $('controls').replaceChildren();$('source').replaceChildren();$('left').textContent='';$('right').textContent='';
 $('prev').disabled=!rows.length||index===0;$('next').disabled=!rows.length||index===rows.length-1;
 if(!rows.length){$('title').textContent='这一类暂无题目';$('position').textContent='请选择左侧其他状态查看。';return;}
 const row=rows[index],item=data.original.items.find(i=>i.candidate_id===row.candidate_id),saved=decisions[row.row_id];
 $('position').textContent=(index+1)+' / '+rows.length+' · '+row.candidate_id;
 $('title').textContent=SECTION[row.section]+' · '+(saved?'已确认裁决':STATUS[row.status]);
 const source=el('details');source.open=true;source.append(el('summary','查看原文与待核对内容'));
 source.append(el('p',data.subjects[row.row_id]));
 source.append(el('pre',item.turns.map(t=>t.turn_id+' · '+t.role+'：'+t.content).join('\n\n')));
 $('source').append(source);
 for(const side of ['left','right']){$(side).append(el('strong',side==='left'?'评审 A':'评审 B'),el('p',label(row.section,row[side].answer)),el('div',row[side].confirmation==='confirmed'?'该意见已确认':'该意见尚缺确认或回答'));}
 if(row.status!=='disagreement'){$('controls').append(el('p',row.status==='agreed'?'两份已确认意见一致，将保留共同意见。':'请原评审补充回答或确认后，重新生成页面。'));return;}
 let answer=saved?.answer||'',reason=saved?.reason||'';
 function dirty(){if(decisions[row.row_id]){delete decisions[row.row_id];$('counts').textContent='已确认裁决 '+Object.keys(decisions).length+' / '+data.queue.counts.disagreement;$('title').textContent=SECTION[row.section]+' · 修改后待确认';}}
 const choices=el('fieldset');choices.append(el('legend','最终选择（请明确点选）'));
 for(const [v,text] of Object.entries(OPTIONS[row.section])){const l=el('label'),r=el('input');r.type='radio';r.name='answer';r.value=v;r.checked=v===answer;r.onchange=()=>{dirty();answer=v;};l.append(r,document.createTextNode(text));choices.append(l);}
 const reasons=el('fieldset');reasons.append(el('legend','裁决依据'));
 const custom=el('textarea');custom.setAttribute('aria-label','补充裁决理由');custom.placeholder='选择其他理由时填写';custom.hidden=!reason||REASONS.includes(reason);if(!custom.hidden)custom.value=reason;
 for(const text of REASONS){const l=el('label'),r=el('input');r.type='radio';r.name='reason';r.checked=text===reason||(text==='其他理由'&&!!reason&&!REASONS.includes(reason));r.onchange=()=>{dirty();custom.hidden=text!=='其他理由';reason=text==='其他理由'?custom.value:text;};l.append(r,document.createTextNode(text));reasons.append(l);}custom.oninput=()=>{dirty();reason=custom.value;};reasons.append(custom);
 const confirm=el('button','确认这一项');confirm.className='primary';confirm.onclick=()=>{try{const d={row_id:row.row_id,answer,reason};exportDraft(data,$('actor').value,{...decisions,[row.row_id]:d});decisions[row.row_id]=d;message('已确认，可保存裁决文件。');render();}catch(e){message(e.message);}};
 const undo=el('button','撤销本项裁决');undo.onclick=()=>{delete decisions[row.row_id];render();message('本项恢复为待裁决。');};$('controls').append(choices,reasons,confirm,undo);
}
$('prev').onclick=()=>{index--;render();};$('next').onclick=()=>{index++;render();};
$('save').onclick=()=>{try{const draft=exportDraft(data,$('actor').value,decisions);const blob=new Blob([JSON.stringify(draft,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='groundsignal-adjudication.json';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);message('已保存确认过的裁决，未确认改选不会导出。');}catch(e){message(e.message);}};
$('restore').onchange=async()=>{try{const f=$('restore').files[0];if(!f)return;const d=validateDraft(data,JSON.parse(await f.text()));decisions=Object.fromEntries(d.decisions.map(r=>[r.row_id,r]));$('actor').value=d.adjudicator_id;render();message('已恢复裁决；原始答卷保持不变。');}catch(e){message('恢复失败：'+e.message);}};
render();
})();
