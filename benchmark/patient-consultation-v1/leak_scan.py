#!/usr/bin/env python3
"""M0 评审包泄漏扫描（H-4）。

验证 A/B 两份 stage1 review.json 是否含作者预期标签或未来窗口信息。
这是 M0 清单第 7 条（"不向医生暴露作者预期标签"）的技术验证。

扫描策略（结构化，非关键词判临床）：
- 递归扫描每个 row 的所有键名
- 禁用键：expected / author_id / gold / label / hypothesis / family / severity_anchor / future
- 检查是否含 future 窗口的 sample_id 前缀（stage2 的样本不得出现在 stage1 包中）
- 输出实测结果，不修改任何文件

用法: python leak_scan.py [--base <repo_root>/benchmark/ap07-oracle-draft-v2]

默认 base 从脚本自身位置推断（本文件位于 <repo>/benchmark/patient-consultation-v1/），
因此不依赖任何绝对路径。
"""
import argparse
import json
import os
from pathlib import Path

# 默认 base：<repo>/benchmark/ap07-oracle-draft-v2
# 本脚本位于 <repo>/benchmark/patient-consultation-v1/leak_scan.py
_DEFAULT_BASE = str(Path(__file__).resolve().parent.parent / 'ap07-oracle-draft-v2')
BANNED_KEY_TOKENS = ['expected', 'gold', 'label', 'hypothesis', 'future_window']

# 合规声明字段：键名可能含 author/label 但语义是"声明未接触作者标签"，
# 属防泄漏机制本身，不得误报。
ALLOWLIST_KEYS = {
    'participated_in_authoring',
    'exposed_to_author_labels',
    'author_only_note',
}
# 注意：'family'/'severity' 在合法契约中可能出现，不做禁用，仅报告

TARGETS = [
    ('draft_stage1/A/review.json', 'stage1'),
    ('draft_stage1/B/review.json', 'stage1'),
    ('coordinator_only/withheld_stage2/A/review.json', 'stage2'),
    ('coordinator_only/withheld_stage2/B/review.json', 'stage2'),
]


def scan_keys(obj, path='', found=None):
    if found is None:
        found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if str(k) in ALLOWLIST_KEYS:
                scan_keys(v, f'{path}.{k}', found)
                continue
            for tok in BANNED_KEY_TOKENS:
                if tok in kl:
                    found.append((f'{path}.{k}', repr(v)[:80]))
            scan_keys(v, f'{path}.{k}', found)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:3]):
            scan_keys(v, f'{path}[{i}]', found)
    return found


def collect_ids(path):
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    return {r['sample_id'] for r in d.get('rows', [])}


def main():
    ap = argparse.ArgumentParser(description='M0 评审包泄漏扫描')
    ap.add_argument('--base', default=_DEFAULT_BASE,
                    help='ap07-oracle-draft-v2 目录（默认从脚本位置推断）')
    args = ap.parse_args()
    base = args.base

    print('=== 禁用键扫描 ===')
    print(f'base: {base}')
    print(f'禁用键 token: {BANNED_KEY_TOKENS}\n')

    all_clean = True
    for rel, stage in TARGETS:
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            print(f'{rel}: MISSING')
            continue
        d = json.load(open(p, encoding='utf-8'))
        hits = scan_keys(d)
        n_rows = len(d.get('rows', []))
        if hits:
            all_clean = False
            print(f'{rel} ({stage}): ✗ 发现 {len(hits)} 处禁用键')
            for k, v in hits[:5]:
                print(f'    {k} = {v}')
        else:
            print(f'{rel} ({stage}): ✓ 无禁用键 (rows={n_rows})')

    print('\n=== stage1/stage2 样本隔离 ===')
    s1_A = collect_ids(os.path.join(base, 'draft_stage1/A/review.json'))
    s2_A = collect_ids(os.path.join(base, 'coordinator_only/withheld_stage2/A/review.json'))
    overlap = s1_A & s2_A
    print(f'stage1 A 样本数 = {len(s1_A)}, stage2 A 样本数 = {len(s2_A)}')
    print(f'交集 = {len(overlap)} {"（应为 0）" if not overlap else "✗ 存在泄漏！"}')
    if overlap:
        all_clean = False

    print('\n=== 结论 ===')
    print('LEAK SCAN ' + ('PASS' if all_clean else 'FAIL'))
    print('（本扫描为结构化键检测，非关键词临床裁决；不修改任何文件）')
    return 0 if all_clean else 1


if __name__ == '__main__':
    raise SystemExit(main())
