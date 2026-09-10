"""Generate a bound offline decision page after authoritative input validation."""
import argparse
import json
from pathlib import Path

from .choice_adjudication import prepare_queue, decision_template

ASSETS = Path(__file__).with_name('adjudication_assets')


def render_page(original, left, right):
    queue = prepare_queue(original, left, right)
    subjects = {}
    names = {'clarification.relevant': '澄清关键歧义', 'questioning.unknown': '追问未知信息',
             'correction.absorbed': '使用纠正后的信息', 'risk.boundary': '识别风险与能力边界',
             'explanation.repair': '解释判断变化', 'completion.summary': '准确总结已知与未知'}
    for row in queue['rows']:
        item = next(i for i in original['items'] if i['candidate_id'] == row['candidate_id'])
        if row['section'] == 'facts':
            fact = next(f for f in item['fact_draft']['fact_candidates'] if f['candidate_id'] == row['item_id'])
            subject = '待核对摘录：' + fact['upstream_annotation']['text']
        elif row['section'] == 'rubrics':
            rule = next(r for r in item['review']['rubrics'] if r['criterion_id'] == row['item_id'])
            subject = rule['description'] or names.get(rule['criterion_id'], rule['criterion_id'])
        elif row['section'] == 'privacy':
            subject = '本项检查话轮：' + str(row['item_id'])
        else:
            subject = '判断这段材料是否足够理解当前情况。'
        subjects[row['row_id']] = subject
    payload = {'queue': queue, 'template': decision_template(queue), 'original': original, 'subjects': subjects}
    raw = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    for char, escaped in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'),
                          ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
        raw = raw.replace(char, escaped)
    return (ASSETS.joinpath('index.html').read_text()
            .replace('/* APP */', ASSETS.joinpath('app.js').read_text())
            .replace('__DATA__', raw))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('original', 'left', 'right', 'out'):
        parser.add_argument('--' + field, required=True)
    args = parser.parse_args(argv)
    html = render_page(*(json.loads(Path(getattr(args, field)).read_bytes())
                         for field in ('original', 'left', 'right')))
    with Path(args.out).open('x', encoding='utf-8') as stream:
        stream.write(html)


if __name__ == '__main__':
    main()
