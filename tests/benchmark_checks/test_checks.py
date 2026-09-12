from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import os
import subprocess
import unittest
from unittest.mock import patch

from scripts.benchmark_checks.__main__ import (
    ASSETS, MODEL_RULES, RecordingResult, inspect_suite, model_review, write_report,
)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.suite=json.loads((ASSETS/'suite.json').read_text())

    def test_good_suite_has_no_failures(self):
        rows=inspect_suite(self.suite,semantic=True)
        self.assertTrue(rows)
        self.assertFalse([r for r in rows if r['status']!='PASS'])

    def test_labeled_defects_are_detected_by_the_expected_rule(self):
        fixtures=json.loads(Path(__file__).with_name('mutations.json').read_text())
        for f in fixtures:
            with self.subTest(fixture=f['name']):
                suite=deepcopy(self.suite); target=suite
                parts=f['path'].strip('/').split('/')
                for p in parts[:-1]: target=target[int(p)] if isinstance(target,list) else target[p]
                key=int(parts[-1]) if isinstance(target,list) else parts[-1]
                if f.get('remove'): del target[key]
                else: target[key]=f['value']
                rows=inspect_suite(suite,semantic=True)
                failures=[r for r in rows if r['rule']==f['expected'] and r['status']=='FAIL']
                self.assertTrue(failures,f)
                self.assertTrue(all(r['file'] and r['pointer'] if f['path']!='/clinical_approval' else True for r in failures))

    def test_malformed_containers_fail_without_crashing(self):
        for value in [None,[],42,{'scenarios':[]}]:
            with self.subTest(value=value):
                self.assertTrue(any(r['status']=='FAIL' for r in inspect_suite(value)))
        for path in ['facts','criteria','events','prefix']:
            s=deepcopy(self.suite);s['scenarios'][0][path]=[None]
            self.assertTrue(any(r['status']=='FAIL' for r in inspect_suite(s)))

    def test_review_rejects_invented_quotes_and_missing_rules(self):
        suite=deepcopy(self.suite);suite['scenarios']=suite['scenarios'][:1]
        for checks in [[],[dict(rule=k,status='pass',reason='fixture',quote='not present anywhere 123') for k in MODEL_RULES]]:
            rows,_=model_review(suite,lambda _:dict(content=json.dumps(dict(checks=checks))))
            self.assertEqual([r['status'] for r in rows],['ERROR'])

    def test_review_preserves_insufficient_and_records_model(self):
        suite=deepcopy(self.suite);suite['scenarios']=suite['scenarios'][:1]
        checks=[dict(rule=k,status='insufficient',reason='未核验原文',quote=suite['scenarios'][0]['title']) for k in MODEL_RULES]
        rows,audit=model_review(suite,lambda _:dict(content=json.dumps(dict(checks=checks)),provider_model='fixture'))
        self.assertEqual({r['status'] for r in rows},{'INSUFFICIENT'})
        self.assertEqual(audit[0]['result']['provider_model'],'fixture')

    def test_provider_failure_does_not_become_pass(self):
        rows,_=model_review(self.suite,lambda _:dict(error='http_429'))
        self.assertEqual({r['status'] for r in rows},{'ERROR'})

    def test_budget_failure_makes_zero_requests(self):
        calls=[]
        with self.assertRaises(ValueError):
            model_review(self.suite,lambda m:calls.append(m),max_calls=1)
        self.assertFalse(calls)

    def test_subtest_failure_is_in_report(self):
        class Broken(unittest.TestCase):
            def runTest(self):
                with self.subTest(case='bad'): self.fail('planted failure')
        result=unittest.TextTestRunner(stream=io.StringIO(),resultclass=RecordingResult).run(Broken())
        self.assertTrue(any(r['status']=='FAIL' for r in result.rows))

    def test_advisory_never_claims_clinical_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            with patch.dict('os.environ',{},clear=True):
                write_report(out,'model-review',[],ASSETS)
            r=json.loads((out/'report.json').read_text())
            self.assertEqual(r['status'],'ADVISORY');self.assertFalse(r['clinical_approval'])

    def test_workflow_aggregate_rejects_missing_or_failed_required_jobs(self):
        workflow=ASSETS.parents[1]/'.github/workflows/medical-dialogue-benchmark-ci.yml'
        text=workflow.read_text()
        body=text.split("python3 - <<'PY'\n",1)[1].rsplit('\n          PY',1)[0]
        import textwrap
        body=textwrap.dedent(body)
        with tempfile.TemporaryDirectory() as tmp:
            for state in ['success','failure','skipped','cancelled','unknown']:
                with self.subTest(state=state):
                    env=dict(os.environ,STATIC_RESULT='success',AUTOREVIEW_RESULT='success',
                        VALIDATION_RESULT=state,MODEL_RESULT='skipped',PR_HEAD_SHA='fixture',
                        RUN_URL='https://example.invalid/run',GITHUB_STEP_SUMMARY=tmp+'/summary.md')
                    result=subprocess.run(['python','-c',body],env=env,capture_output=True,text=True)
                    self.assertEqual(result.returncode,0 if state=='success' else 1,result.stderr)


if __name__=='__main__': unittest.main()
