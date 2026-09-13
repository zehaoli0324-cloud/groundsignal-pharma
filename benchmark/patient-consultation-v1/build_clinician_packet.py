#!/usr/bin/env python3
"""构建给临床医生的评审分发包（H-1 扩展）。

产出：每个 reviewer slot 一个独立目录 + zip，**绝不含 coordinator_only/**。

安全纪律（硬约束，任一违反即中止）：
  1. 不得复制 coordinator_only/ 下任何文件
  2. 不得复制 NODES.md 之外、未经协调人确认的节点定义（当前 NODES.md 默认不含，
     见 CLINICIAN_GUIDE.md 的“待确认”说明；如需包含用 --with-nodes 显式开启）
  3. 打包后对每个文件做键名 + 文本泄漏扫描，命中即中止
  4. 不修改源文件

用法：
    python build_clinician_packet.py                     # 只构建+自检，输出到 ./dist/
    python build_clinician_packet.py --out /tmp/packets  # 指定输出目录
    python build_clinician_packet.py --with-nodes        # 显式把 NODES.md 放进包
"""
import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent                 # benchmark/patient-consultation-v1
DEFAULT_SRC = SCRIPT_DIR.parent / 'ap07-oracle-draft-v2'     # benchmark/ap07-oracle-draft-v2

# 每个 slot 只复制这些文件（allowlist —— 白名单而非黑名单，防止未来新增文件误入）
PACKET_FILES = [
    'INSTRUCTIONS.md',
    'criteria.json',
    'SOURCES.json',
    'samples.json',
    'review.json',
]
OPTIONAL_NODES = 'NODES.md'

# 泄漏扫描 token（键名层）
BANNED_KEY_TOKENS = ['expected', 'gold', 'label', 'hypothesis',
                     'future_window', 'answer_key', 'ground_truth']
# 合规声明字段：键名含 author/label 但语义是“声明未接触作者标签”，属防泄漏机制本身
ALLOWLIST_KEYS = {
    'participated_in_authoring',
    'exposed_to_author_labels',
    'author_only_note',
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def scan_keys(obj, path='', found=None):
    """递归扫描 dict 键名中的禁用 token。"""
    if found is None:
        found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k) in ALLOWLIST_KEYS:
                scan_keys(v, f'{path}.{k}', found)
                continue
            for tok in BANNED_KEY_TOKENS:
                if tok in str(k).lower():
                    found.append(f'{path}.{k}')
            scan_keys(v, f'{path}.{k}', found)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_keys(v, f'{path}[{i}]', found)
    return found


def scan_file(p: Path):
    """返回 (json键命中, 文本token命中)。

    文本层扫描前必须先剔除 ALLOWLIST_KEYS —— 这些字段名本身含 'author'/'label'
    字样，但语义正是“声明未接触作者标签”，是防泄漏机制本身，不能误报。
    """
    raw = p.read_text(encoding='utf-8')
    text = raw
    for allowed in ALLOWLIST_KEYS:
        text = text.replace(allowed, '')  # 剔除合规字段名后再扫
    text_hits = [t for t in BANNED_KEY_TOKENS if t in text.lower()]

    key_hits = []
    if p.suffix == '.json':
        try:
            key_hits = scan_keys(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return key_hits, text_hits


def build_packet(slot: str, src: Path, out: Path, with_nodes: bool):
    src_dir = src / 'draft_stage1' / slot
    if not src_dir.is_dir():
        raise SystemExit(f'ERROR: 源目录不存在: {src_dir}')

    files = list(PACKET_FILES)
    if with_nodes:
        if not (src / OPTIONAL_NODES).exists():
            raise SystemExit(f'ERROR: --with-nodes 但 {src / OPTIONAL_NODES} 不存在')
        files.append(OPTIONAL_NODES)

    dest = out / f'reviewer_{slot}'
    dest.mkdir(parents=True, exist_ok=True)

    print(f'\n=== slot {slot} -> {dest} ===')
    for name in files:
        s = src_dir / name if name != OPTIONAL_NODES else src / name
        if not s.exists():
            raise SystemExit(f'ERROR: 声明要打包但源文件缺失: {s}')

        # 泄漏自检（先检后拷，命中即中止）
        key_hits, text_hits = scan_file(s)
        if key_hits:
            raise SystemExit(f'ABORT: {name} 键名命中禁用 token: {key_hits[:5]}')
        if text_hits and name != OPTIONAL_NODES:
            # NODES.md 是节点定义，可能天然含 "hypothesis" 一类词，单独放行需人工确认
            raise SystemExit(f'ABORT: {name} 文本命中禁用 token: {text_hits}')

        shutil.copy2(s, dest / name)
        print(f'  + {name:20s} {s.stat().st_size:7d} B  sha256={sha256_file(s)[:12]}')

    # 硬约束复查：dest 内不得出现 coordinator_only 任何痕迹
    for f in dest.iterdir():
        if 'coordinator' in f.name.lower() or 'blind' in f.name.lower():
            raise SystemExit(f'ABORT: 输出目录出现受限文件名 {f.name}')

    # 生成 MANIFEST
    manifest = {
        'slot': slot,
        'source': str(src_dir.relative_to(src)),
        'files': {n: {'bytes': (dest / n).stat().st_size,
                      'sha256': sha256_file(dest / n)} for n in files},
        'excluded': ['coordinator_only/ (author hypotheses, blind map, withheld stage2)']
                    + ([] if with_nodes else [f'{OPTIONAL_NODES} (节点定义，默认不含，见 CLINICIAN_GUIDE 待确认)']),
        'clinical_approval': False,
        'stage': 1,
    }
    (dest / 'MANIFEST.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  + MANIFEST.json')

    # 打 zip
    zip_path = out / f'reviewer_{slot}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dest.iterdir()):
            z.write(f, arcname=f'{slot}/{f.name}')
    print(f'  zip: {zip_path} ({zip_path.stat().st_size} B)')
    return dest, zip_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=str(DEFAULT_SRC))
    ap.add_argument('--out', default=str(SCRIPT_DIR / 'dist'))
    ap.add_argument('--with-nodes', action='store_true',
                    help='显式把 NODES.md 纳入包（默认不含）')
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # 前置：确认 coordinator_only 存在（证明我们知道它在哪，且刻意排除它）
    coord = src / 'coordinator_only'
    print(f'source      : {src}')
    print(f'output      : {out}')
    print(f'coordinator_only 存在 : {coord.is_dir()} (将被排除)')
    print(f'with_nodes  : {args.with_nodes}')

    built = []
    for slot in ('A', 'B'):
        built.append(build_packet(slot, src, out, args.with_nodes))

    print('\n=== 汇总 ===')
    for dest, zp in built:
        n = len(list(dest.glob('*')))
        print(f'  {dest.name}: {n} 文件, zip={zp.name}')
    print('\nPACKET BUILD OK —— 未包含 coordinator_only/ 任何内容')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
