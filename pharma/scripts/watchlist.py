#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
watchlist.py — Watchlist 事件流看板（Change Detection，不是新闻汇总）

从 Obsidian 情报库读取事件节点（type: event）+ 产能追踪，生成
"过去 N 天与关注公司相关的变化" HTML 推送。

用法:
    python3 watchlist.py <vault> -o watchlist.html
    python3 watchlist.py <vault> --watch NVIDIA,SK海力士,台积电 -o watchlist.html
    python3 watchlist.py <vault> --days 30 -o watchlist.html

事件按 event_date 倒序；产能追踪速览从 06-产能追踪/ 读取。
"""

import argparse
import datetime
import html
import os
import re
import sys

EVENT_STYLE = {
    'NEW_PRODUCT': ('新产品', '#3b82f6'),
    'NEW_CUSTOMER': ('新客户', '#10b981'),
    'SUPPLIER_CHANGED': ('供应商变更', '#f59e0b'),
    'CAPACITY_EXPANSION': ('产能扩张', '#8b5cf6'),
    'EXECUTIVE_LEFT': ('高管变动', '#ef4444'),
    'PRICE_CUT': ('降价', '#f97316'),
    'FUNDING': ('融资', '#ec4899'),
    'PATENT_CLUSTER_SURGE': ('专利激增', '#14b8a6'),
    'TENDER': ('招标', '#6366f1'),
    'REGULATION': ('监管', '#64748b'),
    'PRICE_UP': ('涨价', '#ef4444'),
    'PHASE_TRANSITION': ('临床阶段推进', '#10b981'),
    'FDA_APPROVAL': ('获批上市', '#22c55e'),
    'LICENSING_DEAL': ('授权交易', '#8b5cf6'),
    'IND_SUBMISSION': ('IND申报', '#3b82f6'),
    'SAFETY_SIGNAL': ('安全性信号', '#ef4444'),
    'CLINICAL_START': ('临床启动', '#14b8a6'),
    'M_A': ('并购', '#6366f1'),
}
CONF_COLOR = lambda c: '#10b981' if c >= 0.85 else ('#f59e0b' if c >= 0.7 else '#ef4444')


def parse_note(path):
    content = open(path, encoding='utf-8').read()
    fm = {}
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    body = content
    if m:
        body = content[m.end():]
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip().strip('"')
    return fm, body


def scan_events(vault, days=None, watch=None):
    events = []
    cap_nodes = []
    cutoff = None
    if days:
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
    for root, dirs, fnames in os.walk(vault):
        if '.obsidian' in root: continue
        for f in fnames:
            if not f.endswith('.md'): continue
            fp = os.path.join(root, f)
            fm, body = parse_note(fp)
            t = fm.get('type', '')
            if t == 'event':
                # days 过滤：event_date（YYYY 或 YYYY-MM）与 cutoff 比较
                if cutoff:
                    d = fm.get('event_date', '')
                    try:
                        if re.match(r'^\d{4}-\d{2}$', d):
                            ed = datetime.date(int(d[:4]), int(d[5:7]), 1)
                            if ed < cutoff: continue
                        elif re.match(r'^\d{4}$', d):
                            ed = datetime.date(int(d), 1, 1)
                            if ed < cutoff: continue
                    except ValueError:
                        pass  # 无法解析的日期不过滤
                events.append((fp, fm, body))
            elif '产能' in f or 'capacity' in f.lower():
                cap_nodes.append((fp, fm, body))
    return events, cap_nodes


def render(vault, out, watch=None, days=None):
    events, cap_nodes = scan_events(vault, days, watch)
    # 过滤 watch
    if watch:
        wl = [w.strip() for w in watch.split(',') if w.strip()]
        events = [e for e in events if any(w in (e[1].get('entity', '') + e[0]) for w in wl)]

    # 排序（按 event_date，倒序）
    def date_key(e):
        d = e[1].get('event_date', '')
        return d
    events.sort(key=date_key, reverse=True)

    cards = []
    for fp, fm, body in events:
        etype = fm.get('event_type', 'EVENT')
        label, color = EVENT_STYLE.get(etype, (etype, '#64748b'))
        entity = fm.get('entity', '')
        date = fm.get('event_date', '')
        conf = fm.get('confidence', '')
        src = fm.get('source_url', '')
        impact = fm.get('impact', '')
        # 从 body 取内容行
        content = body.strip().replace('\n', ' ')[:160]
        conf_html = ''
        if conf:
            try:
                cv = float(conf)
                conf_html = f'<span class="conf" style="color:{CONF_COLOR(cv)}">置信度 {conf}</span>'
            except ValueError:
                conf_html = f'<span class="conf">置信度 {conf}</span>'
        src_html = f'<a href="{html.escape(src)}" target="_blank">来源</a>' if src else ''
        cards.append(f'''
        <div class="ev-card">
          <div class="ev-head">
            <span class="ev-type" style="background:{color}">{html.escape(label)}</span>
            <span class="ev-date">{html.escape(date)}</span>
            {conf_html}
            <span class="ev-src">{src_html}</span>
          </div>
          <div class="ev-entity">{html.escape(entity)}</div>
          <div class="ev-body">{html.escape(content)}</div>
          <div class="ev-impact">影响：{html.escape(impact)}</div>
        </div>''')

    # 产能追踪速览
    cap_cards = []
    for fp, fm, body in cap_nodes:
        name = os.path.splitext(os.path.basename(fp))[0]
        cap_cards.append(f'<div class="cap-card"><b>{html.escape(name)}</b><div class="cap-body">{html.escape(body.strip()[:200])}</div></div>')

    today = datetime.date.today().isoformat()
    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Watchlist · 变化摘要</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; background:#eef2f7; color:#1e293b; padding:24px; }}
  .wrap {{ max-width:960px; margin:0 auto; }}
  .hero {{ background:linear-gradient(135deg,#0f172a,#334155); color:#fff; border-radius:16px; padding:24px 32px; margin-bottom:20px; }}
  .hero h1 {{ font-size:24px; }}
  .hero .sub {{ opacity:.85; font-size:13px; margin-top:6px; }}
  .stat {{ display:flex; gap:16px; margin:12px 0 20px; }}
  .stat .box {{ background:#fff; border-radius:12px; padding:14px 20px; flex:1; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .stat .num {{ font-size:22px; font-weight:700; }}
  .stat .lbl {{ font-size:12px; color:#64748b; }}
  .ev-card {{ background:#fff; border-radius:12px; padding:16px 20px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,.08); border-left:4px solid #cbd5e1; }}
  .ev-head {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; flex-wrap:wrap; }}
  .ev-type {{ color:#fff; border-radius:12px; padding:2px 10px; font-size:12px; }}
  .ev-date {{ font-size:12px; color:#64748b; }}
  .conf {{ font-size:12px; font-weight:600; }}
  .ev-src a {{ font-size:12px; color:#3b82f6; text-decoration:none; }}
  .ev-entity {{ font-size:15px; font-weight:600; margin-bottom:4px; }}
  .ev-body {{ font-size:13px; color:#475569; line-height:1.6; }}
  .ev-impact {{ font-size:12px; color:#64748b; margin-top:6px; }}
  .cap-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
  @media (max-width:720px) {{ .cap-grid {{ grid-template-columns:1fr; }} }}
  .cap-card {{ background:#fff; border-radius:12px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .cap-body {{ font-size:12px; color:#64748b; line-height:1.5; margin-top:6px; }}
  .empty {{ color:#94a3b8; text-align:center; padding:40px; }}
  .foot {{ text-align:center; color:#94a3b8; font-size:12px; margin-top:24px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>Watchlist · 变化摘要</h1>
    <div class="sub">Change Detection（非新闻汇总）· 生成 {today} · 来源：Obsidian 情报库事件层</div>
  </div>
  <div class="stat">
    <div class="box"><div class="num">{len(events)}</div><div class="lbl">事件</div></div>
    <div class="box"><div class="num">{len(cap_nodes)}</div><div class="lbl">产能追踪项</div></div>
    <div class="box"><div class="num">{"全部" if not watch else watch}</div><div class="lbl">关注范围</div></div>
  </div>
  <h2 style="font-size:16px;margin:20px 0 12px;">最近事件</h2>
  {''.join(cards) if cards else '<div class="empty">暂无事件（等待采集）</div>'}
  <h2 style="font-size:16px;margin:20px 0 12px;">产能追踪速览</h2>
  <div class="cap-grid">{''.join(cap_cards) if cap_cards else '<div class="empty">暂无产能数据</div>'}</div>
  <div class="foot">由 watchlist.py 生成 · 每条事件带置信度与来源（claim-evidence 模型）</div>
</div>
</body>
</html>'''

    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f'✅ Watchlist 已生成: {out}')
    print(f'   事件 {len(events)} 条 | 产能追踪 {len(cap_nodes)} 项')


def main():
    ap = argparse.ArgumentParser(description='Watchlist 事件流看板')
    ap.add_argument('vault', help='Obsidian vault 路径')
    ap.add_argument('-o', '--output', default='watchlist.html', help='输出 HTML')
    ap.add_argument('--watch', default=None, help='关注公司（逗号分隔，如 NVIDIA,SK海力士）')
    ap.add_argument('--days', type=int, default=None, help='只看最近 N 天')
    args = ap.parse_args()
    render(args.vault, args.output, args.watch, args.days)


if __name__ == '__main__':
    main()
