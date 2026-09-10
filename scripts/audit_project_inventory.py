"""Read tracked code at one Git tree without executing project modules."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess


def inventory():
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', tree], text=True).splitlines()
    rows = []
    for path in paths:
        if not (path.startswith(('scripts/', 'tests/', '.github/workflows/'))
                and Path(path).suffix in {'.py', '.js', '.cjs', '.yml', '.yaml'}):
            continue
        source = subprocess.check_output(['git', 'show', tree + ':' + path]).decode('utf-8')
        stage = re.search(r'(?:^|/)(?:eval_|test_|verify_|generate_)?s([1-9]|10)(?:_|\b)', path, re.I)
        area = ('patient-eval' if 'patient_eval/' in path else 'workflow' if path.startswith('.github/')
                else 'S' + stage[1] if stage else 'shared-or-unclassified')
        row = {'path': path, 'area': area, 'syntax': 'not_checked', 'test_definitions': 0,
               'review_network_usage': bool(re.search(r'urlopen|requests\.|urllib.request|https?://', source)),
               'review_writes': bool(re.search(r'write_text|write_bytes|json.dump|git push|open\(.+[, ]\s*[\'"]w', source)),
               'execution_status': 'NOT_RUN'}
        if path.endswith('.py'):
            try:
                parsed = ast.parse(source, filename=path)
                row['syntax'] = 'parsed'
                row['test_definitions'] = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                                                and n.name.startswith('test_') for n in ast.walk(parsed))
            except SyntaxError as error:
                row.update(syntax='syntax_error', error_line=error.lineno)
        rows.append(row)
    return {'schema_version': 'project-audit-inventory/v0.1', 'input_tree': tree,
            'tracked_files': len(paths), 'inspected_code_and_workflow_files': len(rows),
            'python_syntax_errors': sum(r['syntax'] == 'syntax_error' for r in rows),
            'python_test_definitions': sum(r['test_definitions'] for r in rows),
            'workflow_files': sum(r['area'] == 'workflow' for r in rows), 'rows': rows,
            'project_audit_complete': False, 'project_tests_complete': False,
            'note': 'Keyword flags are triage hints, not proof of side effects or safety. Test definitions are not tests executed. No project module was imported or executed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    report = inventory()
    with Path(args.out).open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
