from copy import deepcopy
import json
from pathlib import Path
from scripts.patient_eval.app_pilot import get_suite
from scripts.patient_eval.patient import validate_patient_spec
from scripts.patient_eval.import_batch import digest_bytes, scenario_digest
from scripts.patient_eval.contracts import require

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'benchmark/medical-dialogue-v1'
VERSION = 'medical-dialogue/v1'
POLICY = '你是一名健康信息助手，请用中文回应用户的问题。'

def load_assets(root=ASSETS):
    root=Path(root)
    suite,sha=get_suite(root/'suite.json')
    patterns=json.loads((root/'patient-patterns.json').read_text())
    patients={}
    for case in suite['scenarios']:
        rules=patterns[case['family_id']]
        require(set(rules)=={f['id'] for f in case['facts']},'patient rules/facts mismatch')
        facts={f['id']:dict(value=f['answer'],status='confirmed',answer=f['answer'],ask_patterns=rules[f['id']]) for f in case['facts']}
        events=[dict(id=e['id'],kind='correction',after_disclosed=e['requires'],min_assistant_turn=e['min_assistant_turns'],content=e['answer'],updates=[dict(slot=k,value=v,status='confirmed',answer=v) for k,v in e.get('fact_overrides',{}).items()]) for e in case['events']]
        spec=dict(initial_user_message=case['prefix'][0]['content'],initial_disclosed=[],facts=facts,events=events,max_assistant_turns=case['max_natural_answers'],closing_message='本轮结束。')
        validate_patient_spec(spec);patients[case['scenario_id']]=spec
    manifest=json.loads((root/'manifest.json').read_text())
    require(manifest['version']==VERSION,'unsupported manifest')
    required={'suite.json','patient-patterns.json','oracle-policy.json','RUBRIC.md'}
    require(set(manifest['files'])==required,'manifest files changed')
    for name,sha256 in manifest['files'].items():
        require(digest_bytes((root/name).read_bytes())==sha256,'asset digest mismatch: '+name)
    # Bind the implementation as well as data; changed code invalidates resume/reviews.
    code_files=sorted((ROOT/'scripts/medical_dialogue_bench').glob('*.py'))
    code_files += [ROOT/'scripts/patient_eval'/f for f in ['patient.py','patient_intent.py','app_pilot.py','contracts.py','review_contract.py','import_batch.py','importers.py']]
    engine=scenario_digest({str(p.relative_to(ROOT)):digest_bytes(p.read_bytes()) for p in code_files})
    return suite,sha,patients,scenario_digest(dict(manifest=manifest,engine=engine,policy=POLICY))
