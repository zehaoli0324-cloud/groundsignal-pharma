#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest.py — 在 Obsidian 情报库中生成节点和关系连接

用法:
    python3 ingest.py <vault> -f relations.yaml       # 从 YAML 关系文件批量生成
    python3 ingest.py <vault> -f relations.yaml --dry  # 预演，不写文件

YAML 格式 (relations.yaml):
    entities:                       # 要生成的节点
      - name: 富瀚微                # 节点名（= 文件名）
        type: company               # company/person/product/investor/deal
        code: 300613.SZ             # 可选字段，会写入 frontmatter
        industry: 集成电路设计
        region: 上海
        desc: 一句话简介            # 可选，写进正文
        source_url: https://...     # 可选
    relations:                      # 要建立的关系（双向 wikilink）
      - from: 联想控股
        to: 富瀚微
        type: 投资                  # 投资/供货/竞争/代工/持股/合作（或任意词）
        desc: 2020-09 以 9.89 亿受让 9.9% 股份
      - from: 富瀚微
        to: 海康威视
        type: 供货
        desc: 第一大客户，占营收 60%+

行为:
- 实体按 type 放到对应目录（company→01-公司, person→02-人物, product→03-产品物料, investor→04-投资人, deal→05-交易事件）
- 新节点自动生成 frontmatter（type + tags: [type/xxx]）+ 正文 + 关联段
- 已有节点不覆盖正文，只在「## 关联」段补充缺失的关系行（幂等）
- 关系在 from/to 两侧都写 wikilink（反向词自动转换：供货↔采购、投资↔被投、持股↔被持股）
"""

import argparse
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

TYPE_DIR = {
    'company': '01-公司',
    'person': '02-人物',
    'product': '03-产品物料',
    'investor': '04-投资人',
    'deal': '05-交易事件',
    'analysis': '06-产业链',
    'changelog': '07-变更日志',
}
REVERSE_REL = {
    '投资': '被投', '供货': '采购', '持股': '被持股',
    '竞争': '竞争', '代工': '代工', '合作': '合作',
    '供应': '采购', '采购': '供货', '被投': '投资',
}


def ensure_dir(vault, sub):
    d = os.path.join(vault, sub)
    os.makedirs(d, exist_ok=True)
    return d


def note_path(vault, etype, name):
    sub = TYPE_DIR.get(etype, '01-公司')
    return os.path.join(vault, sub, f'{name}.md')


def gen_frontmatter(fields):
    lines = ['---']
    for k, v in fields.items():
        if v is None:
            continue
        v = str(v).strip()
        if not v:
            continue
        if ':' in v or '#' in v or v.startswith(('[', '{')):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f'{k}: {v}')
    lines.append('---')
    return '\n'.join(lines)


def build_new_note(entity):
    name = entity['name']
    etype = entity.get('type', 'company')
    fm = {
        'type': etype,
        'tags': f'type/{etype}',
        'name': name,
    }
    for k in ('code', 'industry', 'region', 'founded', 'status', 'website',
              'investor_type', 'amount', 'date', 'role', 'company',
              'products', 'suppliers', 'customers', 'investors',
              'competitors', 'source_url', 'fetched_at', 'evidence'):
        if entity.get(k):
            fm[k] = entity[k]
    body = [f'# {name}', '']
    if entity.get('desc'):
        body.append(entity['desc'].strip())
        body.append('')
    body.append('## 关联')
    body.append('')
    body.append('<!-- 关系由 ingest.py 自动维护，勿手改此行 -->')
    body.append('')
    return gen_frontmatter(fm) + '\n\n' + '\n'.join(body) + '\n'


def ensure_note(vault, entity):
    """返回 (path, is_new)"""
    name = entity['name']
    etype = entity.get('type', 'company')
    path = note_path(vault, etype, name)
    if os.path.exists(path):
        return path, False
    ensure_dir(vault, TYPE_DIR.get(etype, '01-公司'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(build_new_note(entity))
    return path, True


def rel_line(other, rel_type, desc, reverse=False):
    label = REVERSE_REL.get(rel_type, rel_type) if reverse else rel_type
    line = f'- [[{other}]]（{label}'
    if desc:
        line += f'：{desc}'
    line += '）'
    return line


def add_relation(vault, rel):
    """在 from/to 两侧都加关联行（幂等：已存在则跳过）"""
    frm, to = rel['from'], rel['to']
    rtype = rel.get('type', '关联')
    desc = rel.get('desc', '')
    # 找两个节点的路径（不限目录，按文件名搜）
    paths = {}
    for root, dirs, fnames in os.walk(vault):
        if '.obsidian' in root:
            continue
        for f in fnames:
            if f.endswith('.md'):
                base = os.path.splitext(f)[0]
                paths.setdefault(base, os.path.join(root, f))
    if frm not in paths:
        print(f'  ⚠ 节点不存在，跳过关系: {frm} -> {to}（先建实体）')
        return 0
    if to not in paths:
        print(f'  ⚠ 节点不存在，跳过关系: {frm} -> {to}（先建实体）')
        return 0

    added = 0
    for target, other, reverse in ((frm, to, False), (to, frm, True)):
        fp = paths[target]
        content = open(fp, encoding='utf-8').read()
        line = rel_line(other, rtype, desc, reverse=reverse)
        if line in content:
            continue
        content = append_to_section(content, '关联', line)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        added += 1
    return added


def append_to_section(content, section, line):
    """把 line 追加到 '## {section}' 段的末尾（不产生行间空行）"""
    anchor = f'## {section}'
    aidx = content.find(anchor)
    if aidx == -1:
        return content.rstrip() + f'\n\n{anchor}\n\n{line}\n'
    head = content[:aidx + len(anchor)]
    tail = content[aidx + len(anchor):]
    nxt = tail.find('\n## ')
    seg = tail if nxt == -1 else tail[:nxt]
    seg_clean = seg.rstrip('\n') + f'\n{line}\n'
    return head + seg_clean + (tail[nxt:] if nxt != -1 else '')


def main():
    ap = argparse.ArgumentParser(description='生成 Obsidian 节点和关系连接')
    ap.add_argument('vault', help='Obsidian vault 路径')
    ap.add_argument('-f', '--file', required=True, help='YAML/JSON 关系文件')
    ap.add_argument('--dry', action='store_true', help='预演模式，不写文件')
    args = ap.parse_args()

    if not os.path.isdir(args.vault):
        print(f'❌ vault 不存在: {args.vault}', file=sys.stderr)
        sys.exit(1)

    with open(args.file, encoding='utf-8') as f:
        raw = f.read()
    if yaml is not None:
        data = yaml.safe_load(raw)
    else:
        import json
        data = json.loads(raw)

    entities = data.get('entities', [])
    relations = data.get('relations', [])

    new_nodes, exist_nodes = [], []
    for e in entities:
        name = e.get('name', '').strip()
        if not name:
            continue
        if args.dry:
            path = note_path(args.vault, e.get('type', 'company'), name)
            new_nodes.append(name) if not os.path.exists(path) else exist_nodes.append(name)
            continue
        path, is_new = ensure_note(args.vault, e)
        (new_nodes if is_new else exist_nodes).append(name)

    rel_added = 0
    for r in relations:
        if not r.get('from') or not r.get('to'):
            continue
        if args.dry:
            rel_added += 1
            continue
        rel_added += add_relation(args.vault, r)

    print(f'✅ 完成（{"预演" if args.dry else "写入"}）')
    print(f'   新增节点: {len(new_nodes)}  {new_nodes[:8]}')
    print(f'   已存在跳过: {len(exist_nodes)}')
    print(f'   关系边: {len(relations)} 条（写入 {rel_added} 条 wikilink）')


if __name__ == '__main__':
    main()
