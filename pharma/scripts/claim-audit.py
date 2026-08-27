#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
claim-audit.py — Claim-level Evidence Audit（原子 claim 级审计）

节点级 audit（evidence-audit.py）只回答"文件里有没有可追溯来源"；
本脚本把每个关系行（"- [[X]]（描述）（来源: URL）"）当作一条原子 claim，
逐条打标：VERIFIED / SUPPORTED / INFERRED / UNSUPPORTED，并统计
Unsupported Claim Rate 等 claim 级指标。

用法:
    python3 claim-audit.py <vault> [--audit-dir 05-证据审计]
"""
import argparse
import datetime
import os
import re
import sys
from collections import Counter, defaultdict

VERIFIED_DOMAINS = ['clinicaltrials.gov', 'fda.gov', 'nmpa.gov.cn', 'cde.org.cn',
                    'drugbank', 'who.int', 'ema.europa.eu', 'emweb.securities.eastmoney.com',
                    'cninfo']
SUPPORTED_DOMAINS = ['ncbi.nlm.nih.gov', 'pubmed', 'fiercepharma', 'endpts', 'biospace',
                     'pharmaphorum', 'drugs.com', 'dxy', 'reuters.com', 'nature.com',
                     'lancet.com', 'nejm.org', 'cell.com', 'science.org',
                     'lilly.com', 'novonordisk.com', 'pfizer.com', 'legendbiotech.com',
                     'jnj.com', 'hengrui.com', 'beigene.com', 'innoventbio.com',
                     'junshi.com', 'fosunpharma.com', 'wuxiapptec.com', 'wuxibiologics.com',
                     'tigermed.net', 'mindray.com', 'zhifeishengwu.com', 'prnewswire.com',
                     'novartis.com', 'coherus.com', 'sina', '163.com', 'sohu', 'qq.com',
                     'ifeng', '10jqka']
INFERRED_DOMAINS = ['xueqiu', 'caifuhao', 'toutiao', 'baijiahao', 'mp.weixin', 'zhihu']


def classify_url(url):
    for d in VERIFIED_DOMAINS:
        if d in url:
            return 'VERIFIED'
    for d in SUPPORTED_DOMAINS:
        if d in url:
            return 'SUPPORTED'
    for d in INFERRED_DOMAINS:
        if d in url:
            return 'INFERRED'
    return 'UNSUPPORTED'


CLAIM_RE = re.compile(r'^- (.+)$')
URL_RE = re.compile(r'（?来源[:：]\s*(https?://[^\s）)]+)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vault')
    ap.add_argument('--audit-dir', default='05-证据审计')
    args = ap.parse_args()
    if not os.path.isdir(args.vault):
        print(f'❌ vault 不存在: {args.vault}', file=sys.stderr)
        sys.exit(1)

    SKIP_DIRS = ('_模板', '08-智能发现', '08-证据审计', '07-变更日志', args.audit_dir)
    claims = []          # (file, claim_id, text, level, url)
    per_file = defaultdict(Counter)
    for root, dirs, files in os.walk(args.vault):
        if '.obsidian' in root:
            continue
        if any(skip in root for skip in SKIP_DIRS):
            continue
        for f in files:
            if not f.endswith('.md'):
                continue
            path = os.path.join(root, f)
            base = os.path.splitext(f)[0]
            text = open(path, encoding='utf-8').read()
            fm_end = 0
            m = re.match(r'^---\n.*?\n---', text, re.DOTALL)
            if m:
                fm_end = m.end()
            body = text[fm_end:]
            in_rel = False
            idx = 0
            for line in body.splitlines():
                ls = line.strip()
                if ls.startswith('## 关系') or ls.startswith('## 相关药物') or ls.startswith('## 相关公司'):
                    in_rel = True
                    continue
                if in_rel and ls.startswith('## '):
                    in_rel = False
                if not in_rel:
                    continue
                mm = CLAIM_RE.match(ls)
                if not mm:
                    continue
                idx += 1
                claim_text = mm.group(1)[:80]
                um = URL_RE.search(ls)
                url = um.group(1) if um else ''
                level = classify_url(url) if url else 'UNSUPPORTED'
                cid = f"C-{base[:8]}-{idx:04d}"
                claims.append((base, cid, claim_text, level, url))
                per_file[base][level] += 1

    total = len(claims)
    dist = Counter(c for _, _, _, c, _ in claims)
    unsupported = dist.get('UNSUPPORTED', 0)
    rate = unsupported / total if total else 0
    supported_rate = 1 - rate

    print(f'📊 claim-audit: {total} 条原子 claim')
    for k in ['VERIFIED', 'SUPPORTED', 'INFERRED', 'UNSUPPORTED']:
        print(f'   {k}: {dist.get(k, 0)}')
    print(f'   Unsupported Claim Rate: {rate:.1%} | Supported Claim Rate: {supported_rate:.1%}')

    out_dir = os.path.join(args.vault, args.audit_dir)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'claim-audit.md')
    today = datetime.date.today().isoformat()
    lines = [f'# Claim-level Evidence Audit', '', f'> 生成：{today} · 原子 claim 逐条打标', '',
             f'**总 claim 数：{total}** | Unsupported Rate: **{rate:.1%}** | Supported Rate: **{supported_rate:.1%}**', '',
             '## 分布', '', '| 等级 | 数量 | 占比 |', '|------|------|------|']
    for k in ['VERIFIED', 'SUPPORTED', 'INFERRED', 'UNSUPPORTED']:
        n = dist.get(k, 0)
        lines.append(f'| {k} | {n} | {n/total:.1%} |' if total else f'| {k} | {n} | - |')
    lines += ['', '## 按文件', '', '| 文件 | VERIFIED | SUPPORTED | INFERRED | UNSUPPORTED |', '|------|----------|-----------|----------|-------------|']
    for base in sorted(per_file):
        c = per_file[base]
        lines.append(f'| {base} | {c.get("VERIFIED",0)} | {c.get("SUPPORTED",0)} | {c.get("INFERRED",0)} | {c.get("UNSUPPORTED",0)} |')
    lines += ['', '## UNSUPPORTED claim 清单（复核重点）', '']
    for base, cid, ct, level, url in claims:
        if level == 'UNSUPPORTED':
            lines.append(f'- `{cid}` [[{base}]]: {ct}（无来源）')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))
    print(f'📄 报告: {out}')


if __name__ == '__main__':
    main()
