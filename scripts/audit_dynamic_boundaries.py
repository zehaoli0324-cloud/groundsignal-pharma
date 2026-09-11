#!/usr/bin/env python3
"""A1 batch 5: synthetic state, stable path, and HTML-data boundary probes.

No browser execution, real source loading, admission change or production fix.
Exit 2 records observed invariant failures. Use a new output directory.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.patient_eval import dynamic_case_drafts as drafts
from scripts.patient_eval.dynamic_case_offline import SyntheticContractExecutor, _synthetic_case
from scripts.patient_eval.clinical_console import demo_packet, render_console
from scripts.patient_eval.candidate_review import _digest
from scripts.patient_eval.candidate_review_ui import render_review_workspace


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def probes():
    rows=[]
    def record(pid,finding,expected,actual,passed):
        rows.append(dict(probe_id=pid,finding_id=finding,expected=expected,actual=actual,invariant_pass=bool(passed)))
    for pid in ('opening_missing_payload','event_missing_payload'):
        case=_synthetic_case()
        if pid=='opening_missing_payload':del case['opening']['evidence_fragments']
        else:del case['disclosure_events'][0]['response']['evidence_fragments']
        executor=SyntheticContractExecutor(case)
        if pid=='event_missing_payload':executor.open()
        before=executor.snapshot();error=None;retry_error=None
        try:
            executor.open() if pid=='opening_missing_payload' else executor.confirm('E-QUESTION')
        except (KeyError,ValueError) as exc:error=type(exc).__name__+': '+str(exc)
        after=executor.snapshot()
        try:
            executor.open() if pid=='opening_missing_payload' else executor.confirm('E-QUESTION')
        except (KeyError,ValueError) as exc:retry_error=type(exc).__name__+': '+str(exc)
        record(pid,'A1-016','Missing output payload fails without recording successful state/disclosure',
               dict(error=error,before=before,after=after,retry_error=retry_error),error is not None and before==after)
    executor=SyntheticContractExecutor(_synthetic_case());opened=executor.open();executor.confirm('E-QUESTION');final=executor.stop()
    record('normal_disclosure_and_stop',None,'Normal sequence discloses only selected slots and preserves unreached event',
           final,opened['disclosed']==['F-INITIAL'] and final['state']=='CLOSED'
           and final['unreached_event_ids']==['E-SCHEDULED'] and 'F-NEVER' not in final['disclosed_fact_ids'])
    case=_synthetic_case();case.update(scope='development_only',clinical_runnable='BLOCKED');error=None
    try:SyntheticContractExecutor(case)
    except ValueError as exc:error=str(exc)
    record('source_derived_mode_rejected',None,'Declared source-derived mode cannot enter synthetic executor',dict(error=error),error is not None)
    with tempfile.TemporaryDirectory(prefix='a1-path-only-synthetic-') as temp:
        root=Path(temp);private=root/'private';outside=root/'outside';private.mkdir();outside.mkdir()
        (private/'link').symlink_to(outside,target_is_directory=True)
        # Only the helper's path anchor is redirected to a synthetic temporary
        # root. No real private directory or authentication constant is changed.
        with patch.object(drafts,'LOCAL_ROOT',private):
            for pid,path in [('outside_private_root',outside/'marker.json'),('symlink_parent_escape',private/'link'/'marker.json')]:
                error=None
                try:drafts._new_local(path)
                except ValueError as exc:error=str(exc)
                record(pid,None,'Stable outside-root or linked path rejected before writing',
                       dict(error=error,target_created=(outside/'marker.json').exists(),scope='isolated temporary root'),
                       error is not None and not (outside/'marker.json').exists())
    packet=demo_packet()
    marker='</script><script>globalThis.AUDIT_SENTINEL=1</script><img src=x onerror="AUDIT_SENTINEL=2">&\u2028\u2029'
    packet['source_binding']['synthetic_injection_marker']=marker
    packet['packet_sha256']=_digest(packet)
    for pid,renderer,data_id,key in [('console_data_escape',render_console,'console-data','packet'),
                                    ('review_workspace_data_escape',render_review_workspace,'packet-data',None)]:
        html=renderer(packet)
        m=re.search(r'<script id="'+data_id+r'" type="application/json">(.*?)</script>',html,re.S)
        decoded=json.loads(m[1]) if m else None
        recovered=decoded[key] if key and decoded else decoded
        actual=dict(raw_marker_in_html=marker in html,raw_less_than_in_payload='<' in m[1] if m else None,
                    marker_roundtrip=recovered['source_binding']['synthetic_injection_marker']==marker if recovered else False,
                    scope='generated HTML and JSON parser only; not a browser test')
        record(pid,None,'Source marker roundtrips as escaped JSON without becoming an HTML script tag',actual,
               not actual['raw_marker_in_html'] and actual['raw_less_than_in_payload'] is False and actual['marker_roundtrip'])
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);rows=probes();failed=sum(not r['invariant_pass'] for r in rows)
    report=dict(total=len(rows),passed=len(rows)-failed,failed=failed,rows=rows,production_fixes=0,
                real_patient_reads=0,external_model_calls=0,browser_sessions=0)
    dump(args.out/'observations.json',report)
    files=['scripts/audit_dynamic_boundaries.py','scripts/patient_eval/dynamic_case_offline.py',
           'scripts/patient_eval/dynamic_case_drafts.py','scripts/patient_eval/clinical_console.py',
           'scripts/patient_eval/candidate_review_ui.py']
    dump(args.out/'run-manifest.json',dict(argv=[sys.executable,*sys.argv],cwd=str(Path.cwd()),python=platform.python_version(),
         input_git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         input_git_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
         file_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
         probe_script_uncommitted_at_first_execution=True,input_scope='new markers and existing synthetic demo',
         path_test_scope='isolated helper anchor only; no race or real private-path test',
         output=str(args.out),expected_exit_code_at_audit_baseline=2,actual_exit_code=2 if failed else 0))
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2));return 2 if failed else 0


if __name__=='__main__':raise SystemExit(main())
