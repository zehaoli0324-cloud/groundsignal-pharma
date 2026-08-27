#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cross-entity-scan.py — 新实体入库后自动扫描全库，发现交叉关系（Cross-Entity Intelligence）

用法:
    python3 cross-entity-scan.py <vault> <新实体名>              # 扫描 + CLI alert
    python3 cross-entity-scan.py <vault> <新实体名> --report     # 额外生成 Discovery Report 到 08-智能发现/
    python3 cross-entity-scan.py <vault> <新实体名> --all        # 显示所有旧实体（不过滤低分）

原理:
    neighbors(C) ∩ neighbors(old) → 共享节点 → 关系分类 → overlap score → alert

三层输出（防 overclaim）:
    OBSERVED     直接关系行（C ↔ old 已有边），事实级
    DERIVED      由共享节点推断（shared customers/suppliers/products），分析级
    HYPOTHESIS   仅行业/生态重叠，需人工验证

关系分类（v1 启发式，不默认竞争）:
    DIRECT_COMPETITOR / INDIRECT_COMPETITOR / SHARED_CUSTOMER / SHARED_SUPPLIER
    / SUPPLY_CHAIN_LINK / COMMON_ECOSYSTEM / SHARED_INVESTOR
"""

import argparse
import datetime
import os
import re
import sys

TYPE_LABEL = {'company': '公司', 'person': '人物', 'product': '产品', 'investor': '投资人',
              'facility': '设施', 'event': '事件', 'capacity': '产能', 'deal': '交易',
              'target': '靶点', 'modality': '治疗模式', 'analysis': '分析',
              'index': '索引', 'changelog': '日志'}

# 半导体版权重（v1 兼容）
SCORE_W_SEMI = {'product': 0.25, 'customer': 0.20, 'supplier': 0.15, 'industry': 0.15,
                'investor': 0.10, 'ecosystem': 0.05, 'direct': 0.10}
# 医药版权重：shared target / indication / modality 是核心竞争信号
SCORE_W_PHARMA = {'target': 0.30, 'indication': 0.25, 'modality': 0.15,
                  'investor': 0.10, 'ecosystem': 0.05, 'direct': 0.10,
                  'licensing': 0.15, 'trial': 0.10}


def parse_note(path):
    c = open(path, encoding='utf-8').read()
    fm = {}
    m = re.match(r'^---\n(.*?)\n---', c, re.DOTALL)
    body = c
    if m:
        body = c[m.end():]
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip().strip('"')
    links = set()
    for mm in re.findall(r'\[\[([^\]|]+)', c):
        links.add(os.path.basename(mm.strip()))
    return fm, body, links


def scan_vault(vault):
    notes = {}
    SKIP_DIRS = ('08-智能发现', '08-证据审计', '07-监控日志', '07-变更日志', '_模板')
    for root, dirs, files in os.walk(vault):
        if '.obsidian' in root:
            continue
        if any(skip in root for skip in SKIP_DIRS):
            continue
        for f in files:
            if not f.endswith('.md'):
                continue
            base = os.path.splitext(f)[0]
            fm, body, links = parse_note(os.path.join(root, f))
            notes[base] = {'fm': fm, 'body': body, 'links': links, 'backlinks': set()}
    for base, n in notes.items():
        for t in n['links']:
            if t in notes:
                notes[t]['backlinks'].add(base)
    return notes


def neighbors(note, notes):
    return (note['links'] | note['backlinks']) - {'00-总目录'}


def rel_desc(note, target):
    """在 note 的关系行里找 target 的描述"""
    for line in note['body'].splitlines():
        ls = line.strip()
        if ls.startswith('- ') and f'[[{target}]]' in ls:
            return ls[:100]
    return ''


def classify(mode, new_base, old_base, shared, new_note, old_note, notes, direct):
    """启发式关系分类（不默认竞争）。mode: 'pharma' | 'semi'"""
    types = []
    shared_products = [s for s in shared if notes[s]['fm'].get('type') == 'product']
    shared_targets = [s for s in shared if notes[s]['fm'].get('type') == 'target']
    shared_analysis = [s for s in shared if notes[s]['fm'].get('type') == 'analysis']
    shared_customers, shared_suppliers, shared_investors = [], [], []
    for s in shared:
        d1 = rel_desc(new_note, s) + ' ' + rel_desc(old_note, s)
        if notes[s]['fm'].get('type') == 'investor':
            shared_investors.append(s)
        elif '客户' in d1 or '供货' in d1 or '采购' in d1 or '供应' in d1:
            if '客户' in d1 or '供货' in d1:
                shared_customers.append(s)
            else:
                shared_suppliers.append(s)

    new_ind = new_note['fm'].get('industry', '')
    old_ind = old_note['fm'].get('industry', '')
    same_ind = bool(new_ind and old_ind and (new_ind.split('（')[0][:6] in old_ind or old_ind.split('（')[0][:6] in new_ind))

    # modality overlap（产品 frontmatter modality 相同）
    shared_modalities = []
    new_mod = new_note['fm'].get('modality', '')
    if new_mod:
        for s in shared_products:
            if notes[s]['fm'].get('modality', '') == new_mod:
                shared_modalities.append(s)

    # 直接关系行描述（授权/合作/试验/竞争）
    d_new = rel_desc(new_note, old_base) + rel_desc(old_note, new_base)
    licensing = ('授权' in d_new or '许可' in d_new or '引进' in d_new or 'LICENS' in d_new.upper())
    collab = ('合作' in d_new or '联合' in d_new or '共同' in d_new or 'COLLABORAT' in d_new.upper())
    trial_overlap = bool(re.search(r'NCT\d+', d_new))

    if direct and '竞争' in d_new:
        types.append('DIRECT_COMPETITOR（关系行标注）')
    elif direct:
        types.append('SUPPLY_CHAIN_LINK（已有关联）')

    if mode == 'pharma':
        # 医药核心：共享靶点 ≠ 直接竞争（需叠加适应症/模式/阶段判断）
        if shared_targets:
            types.append('SHARED_TARGET' + ('+直接竞争' if (direct and '竞争' in d_new) else ''))
        if shared_modalities:
            types.append('SHARED_MODALITY')
        if shared_products and same_ind and not any('DIRECT_COMPETITOR' in t for t in types):
            types.append('DIRECT_COMPETITOR')
        elif shared_products:
            types.append('PRODUCT_OVERLAP')
        if licensing:
            types.append('LICENSING_LINK')
        if collab:
            types.append('COLLABORATION_LINK')
        if trial_overlap:
            types.append('TRIAL_OVERLAP')
        if shared_customers:
            types.append('SHARED_CUSTOMER')
        if shared_suppliers:
            types.append('SHARED_SUPPLIER')
        if shared_investors:
            types.append('SHARED_INVESTOR')
        if not types and same_ind:
            types.append('INDIRECT_COMPETITOR/COMMON_ECOSYSTEM（同行业）')
        if not types and shared:
            types.append('COMMON_ECOSYSTEM')
    else:
        if shared_products and same_ind and not any('DIRECT_COMPETITOR' in t for t in types):
            types.append('DIRECT_COMPETITOR')
        elif shared_products:
            types.append('PRODUCT_OVERLAP')
        if shared_customers:
            types.append('SHARED_CUSTOMER' + ('+间接竞争' if shared_products else ''))
        if shared_suppliers:
            types.append('SHARED_SUPPLIER')
        if shared_investors:
            types.append('SHARED_INVESTOR')
        if not types and same_ind:
            types.append('INDIRECT_COMPETITOR/COMMON_ECOSYSTEM（同行业）')
        if not types and shared:
            types.append('COMMON_ECOSYSTEM')

    # overlap score
    if mode == 'pharma':
        comp = {
            'target': min(1.0, len(shared_targets) / 1.5),
            'indication': min(1.0, len(shared_products) / 1.5),
            'modality': min(1.0, len(shared_modalities) / 1.5),
            'investor': min(1.0, len(shared_investors) / 1.5),
            'ecosystem': min(1.0, len(shared_analysis) / 2),
            'direct': 1.0 if direct else 0.0,
            'licensing': 1.0 if licensing else 0.0,
            'trial': 1.0 if trial_overlap else 0.0,
        }
        score = sum(SCORE_W_PHARMA[k] * v for k, v in comp.items())
    else:
        comp = {
            'product': min(1.0, len(shared_products) / 1.5),
            'customer': min(1.0, len(shared_customers) / 2),
            'supplier': min(1.0, len(shared_suppliers) / 2),
            'industry': 1.0 if same_ind else 0.0,
            'investor': min(1.0, len(shared_investors) / 1.5),
            'ecosystem': min(1.0, len(shared_analysis) / 2),
            'direct': 1.0 if direct else 0.0,
        }
        score = sum(SCORE_W_SEMI[k] * v for k, v in comp.items())
    if direct and any('DIRECT_COMPETITOR' in t for t in types):
        score = max(score, 0.75)
    return types, score, shared_products, shared_customers, shared_suppliers, shared_investors


def main():
    ap = argparse.ArgumentParser(description='新实体交叉关系扫描')
    ap.add_argument('vault', help='Obsidian vault 路径')
    ap.add_argument('entity', help='新实体名')
    ap.add_argument('--report', action='store_true', help='生成 Discovery Report 到 08-智能发现/')
    ap.add_argument('--all', action='store_true', help='显示所有旧实体（不过滤低分）')
    args = ap.parse_args()

    if not os.path.isdir(args.vault):
        print(f'❌ vault 不存在: {args.vault}', file=sys.stderr)
        sys.exit(1)

    notes = scan_vault(args.vault)
    if args.entity not in notes:
        print(f'❌ 实体不存在: {args.entity}', file=sys.stderr)
        sys.exit(1)

    # 模式检测：vault 含 03-靶点（或 03-targets）→ pharma；否则 semi 兼容
    mode = ('pharma' if (os.path.isdir(os.path.join(args.vault, '03-靶点'))
                         or os.path.isdir(os.path.join(args.vault, '03-targets')))
            else 'semi')

    new_note = notes[args.entity]
    new_nei = neighbors(new_note, notes)
    results = []
    for old_base, old_note in notes.items():
        if old_base == args.entity or old_base == '00-总目录':
            continue
        if old_note['fm'].get('type') in ('index', 'changelog', 'analysis'):
            continue
        old_nei = neighbors(old_note, notes)
        shared = new_nei & old_nei
        direct = args.entity in old_nei
        types, score, sp, sc, ss, si = classify(mode, args.entity, old_base, shared, new_note, old_note, notes, direct)
        results.append({
            'old': old_base, 'type': old_note['fm'].get('type', '?'),
            'shared': sorted(shared), 'types': types, 'score': round(score, 2),
            'direct': direct, 'sp': sp, 'sc': sc, 'ss': ss, 'si': si,
        })

    results.sort(key=lambda r: -r['score'])
    print(f'\n🔎 Cross-entity scan: {args.entity} vs {len(results)} 现有实体')
    print('=' * 60)
    shown = 0
    for r in results:
        if not args.all and r['score'] < 0.4 and not r['direct']:
            continue
        shown += 1
        level = '🚨' if r['score'] >= 0.75 else ('⚠️' if r['score'] >= 0.5 else '·')
        print(f'\n{level} {r["old"]}（{TYPE_LABEL.get(r["type"], r["type"])}）score={r["score"]}')
        print(f'   类型: {", ".join(r["types"])}')
        if r['shared']:
            print(f'   共享: {", ".join(r["shared"][:6])}')
    print(f'\n（显示 {shown}/{len(results)} 条，score≥0.5 或直接关联）')

    if args.report:
        out_dir = os.path.join(args.vault, '08-智能发现')
        os.makedirs(out_dir, exist_ok=True)
        today = datetime.date.today().isoformat()
        out = os.path.join(out_dir, f'{today}-{args.entity}-交叉关系发现.md')
        lines = [f'# 新实体交叉扫描：{args.entity}', '',
                 f'> 生成：{today} · 对比 {len(results)} 个现有实体 · 由 cross-entity-scan.py 自动生成', '',
                 '## 高优先级发现', '', '| 实体 | 类型 | 关系 | Score | 共享节点 |',
                 '|------|------|------|-------|---------|']
        for r in results:
            if r['score'] >= 0.5 or r['direct']:
                lines.append(f'| [[{r["old"]}]] | {TYPE_LABEL.get(r["type"], r["type"])} | {"、".join(r["types"])} | {r["score"]} | {", ".join(r["shared"][:5])} |')
        lines += ['', '## 待验证推断', '',
                  '以下为 HYPOTHESIS 级（仅共享节点/同行业推断，未经证据验证）：', '']
        for r in results:
            if r['score'] < 0.5 and not r['direct'] and r['shared']:
                lines.append(f'- [[{r["old"]}]]（{", ".join(r["types"])}，score {r["score"]}）')
        lines.append('')
        open(out, 'w', encoding='utf-8').write('\n'.join(lines))
        print(f'\n📄 Discovery Report: {out}')


if __name__ == '__main__':
    main()
