"""Replay collection and bind reviews. A valid transcript is not a clinical pass."""
import json
from pathlib import Path
from collections import Counter
from scripts.patient_eval.contracts import require,validate_session
from scripts.patient_eval.import_batch import scenario_digest
from scripts.patient_eval import app_pilot
from .assets import VERSION,POLICY
from .runtime import run_case,schedule

class Replay:
    def __init__(self,requests):self.requests=iter(requests);self.used=0
    def __call__(self,messages):
        request=next(self.requests);require(messages==request['messages'],'input boundary mismatch')
        require(scenario_digest(messages)==request['messages_sha256'],'request digest mismatch')
        self.used+=1;return request['result']

def verify(out,suite,sha,patients,asset_sha,packets=None):
    out=Path(out);config=json.loads((out/'plan.json').read_text())
    require(config['version']==VERSION and config['policy']==POLICY,'protocol mismatch')
    require(config['suite_sha256']==sha and config['asset_sha256']==asset_sha,'stale assets/engine')
    require(type(config['repeats']) is int and 1<=config['repeats']<=20 and type(config['probe']) is bool,'invalid run config')
    require(config['backend'] in {'oracle','noop','naive','stale','openai'},'unknown backend')
    require(config['slots']==schedule(suite,config['repeats']),'missing/changed plan slots')
    require(type(config['max_calls']) is int and config['max_calls']>=sum(c['max_natural_answers']+int(config['probe']) for c in suite['scenarios'])*config['repeats'],'invalid call budget')
    expected={'plan.json'}|{slot['id']+'.json' for slot in config['slots']}
    require({p.name for p in out.glob('*.json')}==expected,'missing/extra session file; save reports outside run directory')
    cases={c['scenario_id']:c for c in suite['scenarios']};sessions=[]
    for slot in config['slots']:
        s=json.loads((out/(slot['id']+'.json')).read_text());validate_session(s)
        c=cases[slot['scenario_id']];replay=Replay(s['requests'])
        rebuilt=run_case(c,patients[c['scenario_id']],replay,config,slot)
        require(s==rebuilt,'transcript/disclosure/status replay mismatch: '+slot['id'])
        require(replay.used==len(s['requests']),'unused/extra requests')
        journal=[json.loads(line) for line in (out/(slot['id']+'.journal.jsonl')).read_text().splitlines()]
        reconstructed=[];run_case(c,patients[c['scenario_id']],Replay(s['requests']),config,slot,reconstructed.append)
        require(journal==reconstructed,'request journal differs from session')
        sessions.append(s)
    clinical=None
    if packets:
        for packet in packets:app_pilot.validate_review(packet,sessions,suite,sha)
        clinical=app_pilot.report(sessions,suite,sha,packets)
    return sessions,dict(version=VERSION,engineering_integrity='PASS',sessions=len(sessions),families=len({s['family_id'] for s in sessions}),statuses=dict(Counter(s['status'] for s in sessions)),target_calls=sum(len(s['requests']) for s in sessions),clinical_result=clinical,clinical_approval=False,clinical_score=None,readiness='PROVISIONAL_REVIEW' if packets else 'NEEDS_SEMANTIC_REVIEW',run_kind=config['backend'],authenticity_verified=False,internal_model_trajectory_available=False)
