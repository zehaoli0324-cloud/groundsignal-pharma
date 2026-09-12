"""Create a broken COPY of a card and demonstrate actionable diagnostics."""
import argparse
import json
from pathlib import Path
import shutil
from .__main__ import ASSETS, static_checks, write_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    assets=args.out/'broken-assets'
    shutil.copytree(ASSETS,assets)
    suite=json.loads((assets/'suite.json').read_text())
    for case in suite['scenarios']:
        if case['family_id']=='AP01': case['criteria'][0]['requires']=['F999']
    (assets/'suite.json').write_text(json.dumps(suite,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=static_checks(assets)
    write_report(args.out,'static',rows,assets)
    detected=[r for r in rows if r['rule']=='criterion_requires' and r['status']=='FAIL']
    if len(detected)!=2: raise SystemExit('演示失败：检测器没有定位预设缺陷')
    print('演示成功：AP01 两个版本的评分点引用了不存在的 F999。原始题库没有修改。')


if __name__=='__main__': main()
