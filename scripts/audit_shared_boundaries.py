#!/usr/bin/env python3
"""A1 batch 4: synthetic local boundary probes plus static workflow inventory.

Exit 2 means observed invariant failures; never an instruction to run workflows.
All mutated files are newly authored markers in a temporary directory.
"""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.patient_eval.candidate_privacy import scan_text, redact_spans


def load_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def probes():
    rows = []
    def record(pid, finding, expected, actual, passed):
        rows.append(dict(probe_id=pid, finding_id=finding, expected=expected,
                         actual=actual, invariant_pass=bool(passed)))
    with tempfile.TemporaryDirectory(prefix='a1-shared-authored-markers-') as temp:
        root = Path(temp)
        policy = {'version':'audit-synthetic/v1', 'require_same_case_ids':True,
                  'critical_error_policy':{'max_candidate_errors':0, 'allow_increase':False},
                  'metrics':[{'name':'marker', 'path':'scores.marker', 'scale_max':1,
                              'min_delta':0, 'required':True}]}
        baseline = [{'case_id':cid, 'scores':{'marker':0.5}, 'critical_errors':[]} for cid in ('A','B')]
        for pid in ('complete_comparison', 'partly_missing_required_score', 'missing_safety_review',
                    'duplicate_weighting', 'known_critical_error_blocks', 'all_required_scores_missing'):
            candidate = deepcopy(baseline)
            finding = None
            expected_pass = pid == 'complete_comparison'
            if pid == 'partly_missing_required_score':
                candidate[0]['scores']['marker'] = 0.7
                candidate[1]['scores'] = {}
                finding = 'A1-013'
            elif pid == 'missing_safety_review':
                for r in candidate: del r['critical_errors']
                finding = 'A1-013'
            elif pid == 'duplicate_weighting':
                candidate[0]['scores']['marker'] = 0.9
                candidate[1]['scores']['marker'] = 0.0
                candidate.append(deepcopy(candidate[0]))
                finding = 'A1-013'
            elif pid == 'known_critical_error_blocks':
                candidate[0]['critical_errors'] = ['AUTHORED-SYNTHETIC-ERROR']
            elif pid == 'all_required_scores_missing':
                for r in candidate: r['scores'] = {}
            folder = root / pid; folder.mkdir()
            for name, data in [('baseline',baseline),('candidate',candidate)]:
                (folder / (name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
            dump(folder/'policy.json', policy)
            cmd = [sys.executable, str(ROOT/'scripts/regression_gate.py'), '--baseline',str(folder/'baseline.jsonl'),
                   '--candidate',str(folder/'candidate.jsonl'),'--policy',str(folder/'policy.json'),
                   '--out',str(folder/'report.json')]
            run = subprocess.run(cmd, capture_output=True, text=True)
            report = json.loads((folder/'report.json').read_text()) if (folder/'report.json').exists() else None
            gate = report.get('release_gate') if report else None
            record(pid, finding, 'Complete valid pair passes; missing required review, duplicate or critical error must not release',
                   dict(baseline=baseline,candidate=candidate,policy=policy,report=report,exit_code=run.returncode,stderr=run.stderr),
                   (gate == 'PASS' and run.returncode == 0) if expected_pass else (gate != 'PASS' and run.returncode != 0))

        importer = load_script('import-helper.py', 'audit_import_helper')
        for pid in ('renamed_markdown_collision', 'non_markdown_collision', 'clean_merge', 'check_does_not_write'):
            folder=root/pid; src=folder/'source'; dst=folder/'destination'; src.mkdir(parents=True); dst.mkdir()
            (src/'note.md').write_text('NEW-SYNTHETIC-NOTE')
            if pid == 'renamed_markdown_collision':
                (dst/'note.md').write_text('KEEP-ORIGINAL')
                (dst/'企业情报-note.md').write_text('KEEP-PREVIOUS-RENAMED')
            if pid == 'non_markdown_collision':
                (src/'settings.json').write_text('{"marker":"new"}')
                (dst/'settings.json').write_text('{"marker":"keep"}')
            before={p.name:p.read_text() for p in dst.iterdir()}
            with redirect_stdout(io.StringIO()):
                (importer.check if pid=='check_does_not_write' else importer.merge)(str(src),str(dst))
            after={p.name:p.read_text() for p in dst.iterdir()}
            preserved=all(after.get(k)==v for k,v in before.items())
            passed = before==after if pid=='check_does_not_write' else preserved
            if pid=='clean_merge': passed=after=={'note.md':'NEW-SYNTHETIC-NOTE'}
            record(pid, 'A1-014' if 'collision' in pid else None,
                   'Existing destination content survives merge; read-only check writes nothing',
                   dict(before=before,after=after),passed)

    evidence=load_script('evidence-audit.py','audit_evidence_helper')
    for pid,url,expected in [
        ('domain_in_path','https://example.invalid/fda.gov/report','UNKNOWN'),
        ('domain_in_query','https://example.invalid/?source=fda.gov','UNKNOWN'),
        ('domain_suffix_spoof','https://fda.gov.example.invalid/report','UNKNOWN'),
        ('official_host','https://www.fda.gov/report','VERIFIED'),
        ('unknown_host','https://example.invalid/report','UNKNOWN')]:
        actual=evidence.classify([url],'synthetic source marker')
        record(pid,'A1-015' if expected=='UNKNOWN' and pid!='unknown_host' else None,
               'Source-domain classification uses parsed hostname, not path/query/suffix substring',
               dict(url=url,label=actual,expected_label=expected),actual==expected)
    text='demo@example.invalid'
    spans=scan_text(text)
    record('privacy_metadata_omits_value',None,'Review cues do not copy contact values and always need review',
           dict(cues=spans), bool(spans) and text not in json.dumps(spans) and all(s['review_required'] for s in spans))
    mapping={}; error=None
    try: redact_spans('abc',[{'start':0,'end':2,'kind':'name'},{'start':1,'end':3,'kind':'name'}],mapping)
    except ValueError as exc: error=str(exc)
    record('privacy_overlap_rejected',None,'Ambiguous redaction fails before changing mapping',
           dict(error=error,mapping_empty=not mapping),error is not None and not mapping)
    return rows


def inventory():
    import yaml
    paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    workflows=[]
    for path in paths:
        if not path.startswith('.github/workflows/') or not path.endswith(('.yml','.yaml')): continue
        raw=(ROOT/path).read_text()
        # BaseLoader preserves the YAML key 'on' as text and executes no tags.
        doc=yaml.load(raw,Loader=yaml.BaseLoader)
        jobs=doc.get('jobs',{})
        workflows.append(dict(path=path,sha256=hashlib.sha256(raw.encode()).hexdigest(),
            events=list(doc.get('on',{})) if isinstance(doc.get('on'),dict) else doc.get('on'),
            top_permissions=doc.get('permissions'),
            job_permissions={k:v.get('permissions') for k,v in jobs.items()},
            actions=[s['uses'] for j in jobs.values() for s in j.get('steps',[]) if 'uses' in s],
            repository_write_steps=[s.get('name','unnamed') for j in jobs.values() for s in j.get('steps',[]) if re.search(r'\bgit\s+push\b',s.get('run',''))],
            secret_reference_names=sorted(set(re.findall(r'secrets\.([A-Za-z0-9_]+)',raw))),
            direct_expression_run_steps=[s.get('name','unnamed') for j in jobs.values() for s in j.get('steps',[]) if '${{' in s.get('run','')],
            semantic_review='PENDING_EXCEPT_EXPLICIT_COVERAGE_ROWS'))
    deps=[p for p in paths if Path(p).name.startswith('requirements') or Path(p).name in {'pyproject.toml','package.json','package-lock.json','poetry.lock','uv.lock'}]
    return dict(scope='static tracked workflow/dependency metadata only; no workflow execution or online vulnerability check',
                parser='PyYAML '+yaml.__version__+' BaseLoader',workflows=workflows,workflow_count=len(workflows),
                workflows_with_repository_write_steps=sum(bool(r['repository_write_steps']) for r in workflows),
                workflows_without_explicit_top_permissions=sum(r['top_permissions'] is None for r in workflows),
                dependency_files=[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in deps],
                missing_permissions_means='inherits repository/organization defaults; effective permission not verified',
                vulnerabilities_confirmed_by_inventory=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    rows=probes();failed=sum(not r['invariant_pass'] for r in rows)
    result=dict(total=len(rows),passed=len(rows)-failed,failed=failed,rows=rows,production_fixes=0,
                real_patient_reads=0,external_model_calls=0,real_vault_writes=0)
    dump(args.out/'observations.json',result);dump(args.out/'workflow-inventory.json',inventory())
    files=['scripts/audit_shared_boundaries.py','scripts/regression_gate.py','scripts/import-helper.py','scripts/evidence-audit.py','scripts/patient_eval/candidate_privacy.py']
    dump(args.out/'run-manifest.json',dict(argv=[sys.executable,*sys.argv],cwd=str(Path.cwd()),python=platform.python_version(),
         input_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         input_git_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
         file_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
         probe_script_uncommitted_at_first_execution=True,input_scope='new authored markers; tracked workflow metadata',
         network='no network-capable command invoked; network not sandbox-isolated',output=str(args.out),
         expected_exit_code_at_audit_baseline=2,actual_exit_code=2 if failed else 0))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    return 2 if failed else 0


if __name__=='__main__': raise SystemExit(main())
