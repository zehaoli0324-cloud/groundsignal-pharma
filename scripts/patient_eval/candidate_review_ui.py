"""Offline human review workspace; contains source text and must stay private."""
from __future__ import annotations

import json
from collections.abc import Mapping


def render_review_workspace(packet: dict) -> str:
    """Render a private review packet without altering its immutable source fields.

    This editor checks JSON syntax only. Downloads still require the review
    validator; selecting a decision here never grants case admission.
    """
    if not isinstance(packet, Mapping) or not isinstance(packet.get("items"), list):
        raise ValueError("review packet must contain an items list")
    ids = [item.get("candidate_id") for item in packet["items"]]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("candidate IDs must be nonempty and unique")
    if not isinstance(packet.get("packet_sha256"), str) or not packet["packet_sha256"]:
        raise ValueError("packet_sha256 is required")
    # An HTML parser recognises </script> even inside application/json. Never put
    # source '<' in the embedded payload, including reviewer-authored fields.
    payload = json.dumps(packet, ensure_ascii=False, allow_nan=False)
    for char, escaped in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                          ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        payload = payload.replace(char, escaped)
    return _PAGE.replace("__PACKET_DATA__", payload)


_PAGE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>患者资料候选审阅</title><style>
*{box-sizing:border-box}body{font-family:system-ui,sans-serif;background:#f6f7fa;color:#202b3c;margin:0}
header{padding:20px 24px;background:#17334a;color:white}h1{font-size:24px;margin:0 0 8px}p{line-height:1.6}
header p{margin:5px 0;font-size:14px}.bar{display:flex;gap:16px;align-items:end;flex-wrap:wrap;padding:16px 24px;background:white}
label{display:block;font-size:14px;margin:10px 0 5px}input,select,textarea,button{font:inherit;border:1px solid #b8c4d1;border-radius:5px;padding:8px}
input,select{max-width:100%}textarea{width:100%;min-height:72px;resize:vertical}button{background:#17654f;color:white;cursor:pointer}
main{display:grid;grid-template-columns:1fr 1.1fr;gap:18px;padding:18px 24px}section{background:white;padding:18px;border-radius:8px;min-width:0}
h2{font-size:19px;margin-top:0}h3{font-size:16px;margin-bottom:8px}.turn{border-left:3px solid #c5d9e7;padding:10px 12px;margin:10px 0;background:#f5f8fb}
pre,.content{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65}.turn strong{font-size:13px;color:#47647b}
.hint{font-size:13px;color:#526173}.json{font-family:ui-monospace,monospace;font-size:13px;min-height:220px}.smalljson{min-height:100px}
#error{color:#b52030;font-weight:600;padding:0 24px}#status{font-size:13px}details{margin:14px 0}summary{cursor:pointer}
@media(max-width:850px){main{grid-template-columns:1fr;padding:12px}.bar{padding:12px}header{padding:16px}}
</style></head><body>
<header><h1>患者资料候选审阅</h1>
<p>原始咨询仅供本地复核。先检查残余身份信息和材料完整性，再审阅事实与评分规则。</p>
<p>来源标注和医生历史回复都是候选依据；页面不自动确认医学正确性，也不批准案例准入。</p></header>
<div class="bar"><div><label for="reviewer">审阅者编号</label><input id="reviewer" autocomplete="off"></div>
<div><label for="candidate">选择候选</label><select id="candidate"></select></div>
<button id="save" type="button">下载审阅 JSON</button><span id="status" role="status"></span></div>
<p id="error" role="alert"></p>
<main><section><h2 id="case-title">原始对话</h2><p id="identity" class="hint"></p><div id="conversation"></div>
<details open><summary>自动隐私提示（需要逐条确认）</summary><pre id="privacy-cues"></pre></details>
<details><summary>上游事实草稿（未经独立确认）</summary><pre id="source-facts"></pre></details></section>
<section id="editor"><h2>人工复核</h2><p class="hint">所有结论初始均为未审阅。证据应引用左侧实际轮次；复杂字段使用 JSON（JavaScript Object Notation，结构化数据文本）。保存时仅检查格式，正式校验由导入程序完成。</p>
<h3>1. 隐私</h3><label for="privacy-decision">决策</label><select id="privacy-decision">
<option value="unreviewed">未审阅</option><option value="reviewed_no_identifiers">已复核，未发现身份信息</option>
<option value="needs_redaction">需要脱敏处理</option><option value="excluded">排除候选</option></select>
<label for="privacy-reason">理由</label><textarea id="privacy-reason"></textarea>
<label for="privacy-turns">已逐条检查的轮次编号（逗号分隔）</label><input id="privacy-turns" style="width:100%">
<label for="privacy-spans">补充发现的身份信息片段（JSON 数组）</label><textarea id="privacy-spans" class="json smalljson"></textarea>
<h3>2. 完整性</h3><label for="complete-decision">决策</label><select id="complete-decision">
<option value="unreviewed">未审阅</option><option value="usable">材料可用</option>
<option value="insufficient">材料不足</option><option value="excluded">排除候选</option></select>
<label for="complete-reason">理由</label><textarea id="complete-reason"></textarea>
<label for="complete-turns">证据轮次编号（逗号分隔）</label><input id="complete-turns" style="width:100%">
<h3>3. 患者事实</h3><p class="hint">逐条确认事实的肯定、否定或未知状态，事实所属人物、时间、纠正关系、披露条件及证据片段。保留 fact_id，用 reason 解释判断；不得凭空补全缺失事实。</p>
<label for="facts">事实复核行（JSON 数组）</label><textarea id="facts" class="json" spellcheck="false"></textarea>
<h3>4. 病例评分规则</h3><p class="hint">检查是否适用，分别制定 0 / 1 / 2 分标准、严重错误定义、评分机会触发与截止条件。保留 criterion_id，不把历史医生回复直接当作标准答案。</p>
<label for="rubrics">评分规则复核行（JSON 数组）</label><textarea id="rubrics" class="json" spellcheck="false"></textarea>
<p class="hint">下载内容保留全部原始材料与当前审阅结果，仍属于待复核材料。不会联网、自动保存或上传；关闭页面前请下载。未下载的修改会丢失。</p></section></main>
<script id="packet-data" type="application/json">__PACKET_DATA__</script>
<script>
'use strict';
const source = JSON.parse(document.getElementById('packet-data').textContent);
const clone = value => JSON.parse(JSON.stringify(value));
const drafts = source.items.map(item => clone(item.review));
const el = id => document.getElementById(id);
const pretty = value => JSON.stringify(value, null, 2);
let selected = 0;
el('reviewer').value = source.reviewer_id || '';
for (const [index, item] of source.items.entries()) {
  const option = document.createElement('option');
  option.value = String(index); option.textContent = item.candidate_id;
  el('candidate').appendChild(option);
}
function field(id, value) { el(id).value = value == null ? '' : value; }
function show() {
  el('error').textContent = '';
  if (!source.items.length) {
    el('case-title').textContent = '没有候选'; el('editor').hidden = true; return;
  }
  const item = source.items[selected], review = drafts[selected];
  el('case-title').textContent = item.candidate_id + ' · 原始对话';
  el('identity').textContent = '资料包校验值：' + source.packet_sha256;
  el('conversation').replaceChildren();
  for (const turn of item.turns) {
    const box = document.createElement('div'); box.className = 'turn';
    const label = document.createElement('strong');
    label.textContent = turn.turn_id + ' · ' + ({patient:'患者',doctor:'医生'}[turn.role] || turn.role);
    const content = document.createElement('div'); content.className = 'content'; content.textContent = turn.content;
    box.append(label, content); el('conversation').appendChild(box);
  }
  el('privacy-cues').textContent = pretty(item.privacy_findings || []);
  el('source-facts').textContent = pretty(item.fact_draft || {});
  field('privacy-decision', review.privacy.decision); field('privacy-reason', review.privacy.reason);
  field('privacy-turns', review.privacy.checked_turn_ids.join(', '));
  field('privacy-spans', pretty(review.privacy.additional_spans));
  field('complete-decision', review.completeness.decision); field('complete-reason', review.completeness.reason);
  field('complete-turns', review.completeness.evidence_turn_ids.join(', '));
  field('facts', pretty(review.facts)); field('rubrics', pretty(review.rubrics));
  el('status').textContent = '第 ' + (selected + 1) + ' / ' + source.items.length + ' 个候选';
}
function arrayFrom(id, label) {
  let value;
  try { value = JSON.parse(el(id).value); } catch (_) { throw new Error(label + '不是合法 JSON，请修正后再切换或下载。'); }
  if (!Array.isArray(value)) throw new Error(label + '必须是 JSON 数组。');
  return value;
}
function turnsFrom(id) { return el(id).value.split(/[,，\s]+/u).filter(Boolean); }
function capture() {
  if (!source.items.length) return true;
  try {
    const review = clone(drafts[selected]);
    review.privacy = {...review.privacy, decision:el('privacy-decision').value, reason:el('privacy-reason').value,
      checked_turn_ids:turnsFrom('privacy-turns'), additional_spans:arrayFrom('privacy-spans', '身份信息片段')};
    review.completeness = {...review.completeness, decision:el('complete-decision').value,
      reason:el('complete-reason').value, evidence_turn_ids:turnsFrom('complete-turns')};
    review.facts = arrayFrom('facts', '事实复核行'); review.rubrics = arrayFrom('rubrics', '评分规则复核行');
    drafts[selected] = review; el('error').textContent = ''; return true;
  } catch (error) { el('error').textContent = error.message; return false; }
}
el('candidate').addEventListener('change', () => {
  const next = Number(el('candidate').value);
  if (!capture()) { el('candidate').value = String(selected); return; }
  selected = next; show();
});
el('save').addEventListener('click', () => {
  if (!capture()) return;
  const reviewer = el('reviewer').value.trim();
  if (!reviewer) { el('error').textContent = '请填写审阅者编号。'; return; }
  const output = clone(source); output.reviewer_id = reviewer;
  output.items.forEach((item, index) => { item.review = clone(drafts[index]); });
  const blob = new Blob([pretty(output) + '\n'], {type:'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = 'candidate-review-' + reviewer.replace(/[^a-zA-Z0-9_-]/g, '_') + '.json';
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  el('status').textContent = '已请求下载。请保管本地文件；仍需正式校验和复核。';
});
window.addEventListener('beforeunload', event => { event.preventDefault(); event.returnValue = ''; });
show();
</script></body></html>'''
