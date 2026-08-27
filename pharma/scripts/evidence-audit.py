#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evidence-audit.py — 证据等级自动打标 + 审计报告

为 Obsidian 情报库每个节点按来源类型自动标注置信度等级：
    VERIFIED  / SUPPORTED / INFERRED / UNKNOWN / NA

用法:
    python3 evidence-audit.py <vault>              # 打标 + 写审计报告
    python3 evidence-audit.py <vault> --report-only  # 只重写审计报告，不改节点

置信度规则（按 frontmatter source_url + 正文 URL 域名判定）:
    VERIFIED   东财 F10/巨潮/公告等一手官方接口
    SUPPORTED  权威媒体（新浪/和讯/每经/腾讯/凤凰/同花顺）+ 公司官网 + 行业垂直媒体
    INFERRED   自媒体（雪球/财富号/头条/百家号/公众号）
    UNKNOWN    无来源或仅"待核实"
    NA         非实体（索引/日志/模板）
"""

import argparse
import os
import re
import sys
from collections import Counter

VERIFIED_DOMAINS = ['emweb.securities.eastmoney.com', 'push2.eastmoney.com',
                    'datacenter', 'cninfo', 'PC_HSF10',
                    'clinicaltrials.gov', 'fda.gov', 'nmpa.gov.cn', 'cde.org.cn',
                    'drugbank', 'who.int', 'ema.europa.eu']
SUPPORTED_DOMAINS = ['sina', 'hexun', '163.com', 'sohu', 'qq.com', 'ifeng', '10jqka',
                     'dramx', 'nbd', 'stockstar', 'tsmc', 'umc', 'hikvision',
                     'iotworld', 'allwinnertech', 'fullhan',
                     'ncbi.nlm.nih.gov', 'pubmed', 'fiercepharma', 'endpts',
                     'biospace', 'pharmaphorum', 'drugs.com', 'dxy',
                     'medicalnewstoday', 'evaluate', 'nature.com', 'lancet.com',
                     'nejm.org', 'cell.com', 'science.org', 'ashp',
                     'lilly.com', 'novonordisk.com', 'pfizer.com', 'legendbiotech.com',
                     'jnj.com', 'hengrui.com', 'beigene.com', 'innoventbio.com',
                     'junshi.com', 'fosunpharma.com', 'wuxiapptec.com',
                     'wuxibiologics.com', 'tigermed.net', 'mindray.com',
                     'zhifeishengwu.com', 'hillhousecap.com', 'lillyasia.com',
                     'qimingvc.com', 'hongshan.com', 'prnewswire.com',
                     'novartis.com', 'coherus.com', 'reuters.com', 'lilly.com']
INFERRED_DOMAINS = ['xueqiu', 'caifuhao', 'toutiao', 'baijiahao', 'mp.weixin',
                    'lanjinger', 'vzkoo', 'zhihu', 'xiaohongshu', 'meihua']
SKIP_TYPES = ('index', 'changelog')


def classify(urls, body):
    hv = hs = hi = False
    for u in urls:
        if any(d in u for d in VERIFIED_DOMAINS):
            hv = True
        elif any(d in u for d in SUPPORTED_DOMAINS):
            hs = True
        elif any(d in u for d in INFERRED_DOMAINS):
            hi = True
    if hv:
        return 'VERIFIED'
    if hs:
        return 'SUPPORTED'
    if hi:
        return 'INFERRED'
    return 'UNKNOWN'


def main():
    ap = argparse.ArgumentParser(description='证据等级打标 + 审计报告')
    ap.add_argument('vault', help='Obsidian vault 路径')
    ap.add_argument('--report-only', action='store_true', help='只重写审计报告')
    ap.add_argument('--audit-dir', default='08-证据审计',
                    help='审计报告输出目录（v1 库默认 08-证据审计；v2 压测库用 05-证据审计）')
    args = ap.parse_args()

    if not os.path.isdir(args.vault):
        print(f'❌ vault 不存在: {args.vault}', file=sys.stderr)
        sys.exit(1)

    stats = Counter()
    rows = []
    for root, dirs, fnames in os.walk(args.vault):
        if '.obsidian' in root:
            continue
        for f in fnames:
            if not f.endswith('.md'):
                continue
            fp = os.path.join(root, f)
            content = open(fp, encoding='utf-8').read()
            m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not m:
                continue
            fm = m.group(1)
            em = re.search(r'^type:\s*(.+)$', fm, re.M)
            etype = em.group(1).strip() if em else '?'
            base = os.path.splitext(f)[0]
            if etype in SKIP_TYPES or '_模板' in fp:
                level = 'NA'
            elif args.report_only:
                ev = re.search(r'^evidence: (\w+)', fm, re.M)
                level = ev.group(1) if ev else 'NA'
            else:
                urls = re.findall(r'https?://[^\s)\]]+', content)
                level = classify([u.rstrip('。，；') for u in urls], content)
                fm_new = re.sub(r'evidence: \w+', f'evidence: {level}', fm) if 'evidence:' in fm else fm + f'\nevidence: {level}'
                open(fp, 'w', encoding='utf-8').write(content[:m.start(1)] + fm_new + content[m.end(1):])
            stats[level] += 1
            rows.append((base, etype, level, len(re.findall(r'https?://', content))))

    # 审计报告
    out = os.path.join(args.vault, args.audit_dir, 'evidence-audit.md')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    lines = ['# 证据审计报告（Evidence Audit）', '',
             f'> 生成：{__import__("datetime").date.today().isoformat()} · 按来源类型自动定级 · 待核实事项见各节点正文', '',
             '## 置信度等级', '',
             '| 等级 | 含义 | 判定规则 |',
             '|------|------|---------|',
             '| VERIFIED | 一手官方 | 来源含东财 F10（交易所数据转译）/巨潮/公告 |',
             '| SUPPORTED | 权威媒体/官网/行业媒体 | 新浪/和讯/每经/腾讯/凤凰/公司官网/垂直媒体 |',
             '| INFERRED | 自媒体/讨论 | 雪球/财富号/头条/百家号/公众号 |',
             '| UNKNOWN | 无来源/待核实 | 无 source_url 或仅待核实 |',
             '| NA | 非实体 | 索引/日志/模板 |', '',
             '## 分布', '',
             f'- VERIFIED: {stats["VERIFIED"]} · SUPPORTED: {stats["SUPPORTED"]} · INFERRED: {stats["INFERRED"]} · UNKNOWN: {stats["UNKNOWN"]} · NA: {stats["NA"]}',
             '', '## 非 VERIFIED 明细（重点复核）', '',
             '| 节点 | 类型 | 等级 | 来源数 |', '|------|------|------|--------|']
    for base, etype, level, nurl in sorted(rows):
        if level in ('UNKNOWN', 'INFERRED'):
            lines.append(f'| [[{base}]] | {etype} | {level} | {nurl} |')
    lines.append('')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))

    print(f'✅ 打标完成（{"只报告" if args.report_only else "写入"}）: {dict(stats)}')
    print(f'   审计报告: {out}')


if __name__ == '__main__':
    main()
