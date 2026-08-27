#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import-helper.py — 把企业情报库(demo)合并进自己的 Obsidian 库

场景: 你已经有一个 Obsidian 库，想把这套企业情报库的内容并进去。

用法:
    python3 import-helper.py <源vault> <目标vault> --check    # 只扫描冲突，不写文件
    python3 import-helper.py <源vault> <目标vault> --merge    # 执行合并（先自动跑 check 再写）

合并规则（安全设计）:
- 复制源库所有 .md 到目标库（保持相对目录结构）
- 目标库已有同名文件:
    * 内容完全相同 -> 跳过
    * 内容不同     -> 复制为「企业情报-原名.md」，并把新文件内部的
                      [[原名]] 引用改写为 [[企业情报-原名]]（不碰你已有的文件）
- 00-总目录.md 冲突时重命名为 企业情报-总目录.md（避免覆盖你的索引）
- 不复制 .obsidian 配置（每个库的配置互相独立）
"""

import argparse
import filecmp
import os
import re
import shutil
import sys

PREFIX = '企业情报-'


def scan_md(vault):
    """返回 {相对路径: 绝对路径}"""
    out = {}
    for root, dirs, fnames in os.walk(vault):
        if '.obsidian' in root:
            continue
        for f in fnames:
            if f.endswith('.md'):
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, vault)
                out[rel] = fp
    return out


def check(src, dst, verbose=True):
    src_files = scan_md(src)
    dst_files = scan_md(dst)
    dst_names = {os.path.basename(p): p for p in dst_files.values()}

    to_copy, identical, conflict, ok = [], [], [], []
    for rel, fp in sorted(src_files.items()):
        base = os.path.basename(rel)
        dst_fp = os.path.join(dst, rel)
        if not os.path.exists(dst_fp):
            if base in dst_names:
                # 同名但不同路径（同名不同目录）—— 保守处理：按冲突走
                conflict.append((rel, dst_names[base]))
            else:
                ok.append(rel)
                to_copy.append(rel)
        else:
            if filecmp.cmp(fp, dst_fp, shallow=False):
                identical.append(rel)
            else:
                conflict.append((rel, dst_fp))

    if verbose:
        print(f'源库 .md 数: {len(src_files)}')
        print(f'可安全复制: {len(to_copy)}')
        print(f'内容相同跳过: {len(identical)}')
        print(f'冲突(将重命名): {len(conflict)}')
        if conflict:
            print()
            print('冲突清单（将复制为 企业情报-原名.md）:')
            for rel, _ in conflict:
                print(f'  {rel}')
    return to_copy, identical, conflict


def rewrite_wikilinks(content, old_base, new_base):
    """把 [[old]] / [[old|...]] / [[path/old]] 改写成 [[new]]"""
    old_esc = re.escape(old_base)
    # 可选路径前缀 + 名字 + 可选 |alias
    pattern = re.compile(
        r'\[\[(?:[^\]|#]*/)?' + old_esc + r'(\|[^\]]+)?\]\]'
    )

    def repl(m):
        alias = m.group(1) or ''
        return f'[[{new_base}{alias}]]'

    return pattern.sub(repl, content)


def merge(src, dst):
    to_copy, identical, conflict = check(src, dst, verbose=True)
    print()
    if not (to_copy or conflict):
        print('无需任何操作。')
        return

    # 预计算冲突重命名映射（先算完，复制时统一改写，避免漏改）
    # 注意：冲突文件也要复制（重命名为 企业情报-前缀），不能只处理 to_copy
    all_copy = sorted(set(to_copy) | {r for r, _ in conflict})
    rename_map = {}
    for rel in all_copy:
        base = os.path.basename(rel)
        if any(r == rel for r, _ in conflict) or base == '00-总目录.md':
            rename_map[base] = PREFIX + base

    for rel in all_copy:
        src_fp = os.path.join(src, rel)
        dst_fp = os.path.join(dst, rel)
        base = os.path.basename(rel)
        if base in rename_map:
            dst_fp = os.path.join(os.path.dirname(dst_fp), rename_map[base])

        os.makedirs(os.path.dirname(dst_fp), exist_ok=True)
        content = open(src_fp, encoding='utf-8').read()
        # 改写新文件内部的 wikilink（指向被重命名的文件）
        for old, new in rename_map.items():
            old_base = os.path.splitext(old)[0]
            new_base = os.path.splitext(new)[0]
            if old != new and old_base in content:
                content = rewrite_wikilinks(content, old_base, new_base)
        with open(dst_fp, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  + {rel}' + (f'  → {os.path.basename(dst_fp)}（冲突重命名）' if os.path.basename(dst_fp) != base else ''))

    # 复制模板/脚本等非 .md 文件（ask.py/ingest.py/模板 yaml）
    for root, dirs, fnames in os.walk(src):
        if '.obsidian' in root:
            continue
        for f in fnames:
            if f.endswith(('.py', '.yaml', '.yml', '.html', '.json')):
                src_fp = os.path.join(root, f)
                rel = os.path.relpath(src_fp, src)
                dst_fp = os.path.join(dst, rel)
                if os.path.exists(dst_fp) and filecmp.cmp(src_fp, dst_fp, shallow=False):
                    continue
                os.makedirs(os.path.dirname(dst_fp), exist_ok=True)
                shutil.copy2(src_fp, dst_fp)
                print(f'  + {rel}')

    print()
    print('完成。打开 Obsidian 后检查：')
    print('  1. 图谱视图是否有断裂（重命名文件的旧引用应已自动改写）')
    print('  2. 如有遗漏，用 00-总目录 或 企业情报-总目录 入口复查')


def main():
    ap = argparse.ArgumentParser(description='合并企业情报库到自己的 Obsidian 库')
    ap.add_argument('src', help='源库（本仓库 demo/ 或解压的 zip 目录）')
    ap.add_argument('dst', help='目标库（你自己的 Obsidian vault）')
    ap.add_argument('--check', action='store_true', help='只扫描冲突，不写文件')
    ap.add_argument('--merge', action='store_true', help='执行合并')
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        print(f'❌ 源库不存在: {args.src}', file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.dst):
        print(f'❌ 目标库不存在: {args.dst}', file=sys.stderr)
        sys.exit(1)

    if args.check:
        check(args.src, args.dst)
    elif args.merge:
        merge(args.src, args.dst)
    else:
        print('请指定 --check 或 --merge', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
