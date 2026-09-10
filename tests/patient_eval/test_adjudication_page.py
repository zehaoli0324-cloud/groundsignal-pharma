from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import unittest

from scripts.patient_eval.adjudication_page import render_page
from scripts.patient_eval.choice_adjudication import apply_decisions
from tests.patient_eval import test_choice_adjudication as fixture_module


class AdjudicationPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.ChoiceAdjudicationTests.setUpClass()
        t = fixture_module.ChoiceAdjudicationTests()
        t.setUp()
        cls.original, cls.left, cls.right, cls.decisions = t.original, t.left, t.right, t.decision()

    def payload(self):
        html = render_page(self.original, self.left, self.right)
        return html, json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)[1])

    def js(self, payload):
        code = "const fs=require('fs'),a=require('./scripts/patient_eval/adjudication_assets/app.js');const x=JSON.parse(fs.readFileSync(0,'utf8'));try{process.stdout.write(JSON.stringify({ok:true,draft:a.validateDraft(x.data,x.draft)}));}catch(e){process.stdout.write(JSON.stringify({ok:false,error:e.message}));}"
        r = subprocess.run(['node', '-e', code], input=json.dumps(payload), text=True, capture_output=True, check=True)
        return json.loads(r.stdout)

    def test_exported_decisions_are_accepted_by_backend(self):
        _, data = self.payload()
        output = self.js({'data': data, 'draft': self.decisions})
        self.assertTrue(output['ok'])
        result, _ = apply_decisions(self.original, self.left, self.right, output['draft'])
        self.assertEqual(result['counts'], {'adjudicated': 1, 'confirmed_agreement': 3, 'unresolved': 8})

    def test_restore_rejects_stale_flags_missing_reason_and_unreviewed_rows(self):
        _, data = self.payload()
        missing = next(r['row_id'] for r in data['queue']['rows'] if r['status'] == 'missing_answer')
        mutations = [lambda d: d.update(queue_sha256='0' * 64), lambda d: d.update(formal_approval=True),
                     lambda d: d['decisions'][0].update(reason=''),
                     lambda d: d['decisions'][0].update(row_id=missing),
                     lambda d: d['decisions'].append(deepcopy(d['decisions'][0]))]
        for mutate in mutations:
            d = deepcopy(self.decisions)
            mutate(d)
            self.assertFalse(self.js({'data': data, 'draft': d})['ok'])

    def test_partial_export_never_fills_pending_rows(self):
        _, data = self.payload()
        d = deepcopy(self.decisions)
        d['decisions'] = []
        output = self.js({'data': data, 'draft': d})
        self.assertTrue(output['ok'])
        result, _ = apply_decisions(self.original, self.left, self.right, output['draft'])
        self.assertEqual(result['counts']['unresolved'], 9)

    def test_page_includes_source_subject_and_no_network_or_auto_decision(self):
        html, data = self.payload()
        self.assertIn('connect-src \'none\'', html)
        self.assertIn('待核对摘录：昨天', data['subjects'].values())
        self.assertIn('识别风险与能力边界', data['subjects'].values())
        self.assertEqual(data['template']['decisions'], [])
        self.assertNotIn('/* APP */', html)
        js = Path('scripts/patient_eval/adjudication_assets/app.js').read_text()
        for forbidden in ('innerHTML', 'fetch(', 'localStorage', 'sessionStorage', 'eval('):
            self.assertNotIn(forbidden, js)


if __name__ == '__main__':
    unittest.main()
