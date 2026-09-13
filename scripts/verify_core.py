"""Run the focused offline engineering checks; preserve clinical unknowns."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ('static', 'autoreview', 'track-static', 'track-validation',
            'difficulty-review', 'validation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    out = args.out or ROOT/'runs'/('core-check-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    fingerprints = {}
    for directory in ('scripts', 'tests', 'benchmark', 'medical/patient-eval/app-pilot-v1'):
        for path in sorted((ROOT/directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                fingerprints[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'input-fingerprints.json').write_text(json.dumps(fingerprints, indent=2)+'\n')
    results = []
    for command in COMMANDS:
        invocation = [sys.executable, '-m', 'scripts.benchmark_checks', command, '--out', str(out/command)]
        with (out/(command+'.log')).open('w') as log:
            process = subprocess.run(invocation, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        report_path = out/command/'report.json'
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        counts = Counter(row['status'] for row in report.get('findings', []))
        tests = [row for row in report.get('findings', []) if row.get('file', '').startswith('tests/')]
        status = report.get('status', 'ERROR')
        ok = process.returncode == 0 and status in {'PASS', 'NEEDS_REVIEW', 'ADVISORY'}
        result = dict(command=command, exit_code=process.returncode, status=status,
                      engineering_step_ok=ok, counts=dict(counts),
                      test_result_rows=len(tests), report=str(report_path.relative_to(out)))
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    summary = dict(schema='focused-core-verification/v1',
                   checked_at=datetime.now(timezone.utc).isoformat(),
                   python=sys.version.split()[0],
                   engineering_checks_completed=all(row['engineering_step_ok'] for row in results),
                   clinical_approval=False, clinical_score=None,
                   real_model_test_executed=False, results=results)
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print('Evidence:', out)
    raise SystemExit(0 if summary['engineering_checks_completed'] else 1)


if __name__ == '__main__':
    main()
