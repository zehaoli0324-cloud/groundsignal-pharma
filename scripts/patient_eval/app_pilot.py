"""Offline app collection and response-bound review. No automatic medical grading."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import random

from .contracts import require, load_suite, nonempty
from .import_batch import digest_bytes, scenario_digest, validate_batch, write_new_json

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = ROOT / 'medical/patient-eval/app-pilot-v1/suite.json'
ASSETS = Path(__file__).with_name('app_pilot_assets')
VERSION = 'app-pilot/v1'
RUBRIC = 'app-dialogue-rubric/v1'
OUTCOMES = {'unassessed', 'untriggered', 'not_observed', 'insufficient', 'not_applicable', 'pass', 'fail'}
PLATFORMS = ['小荷健康', '蚂蚁健康']
DISTRACTOR = '另外我正在整理手机里的文件，文件夹颜色还没选好。'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def get_suite(path=DEFAULT_SUITE):
    raw = Path(path).read_bytes()
    suite = load_suite(path)
    require(Path(path).read_bytes() == raw, 'suite changed during reading')
    require(suite.get('app_pilot_version') == VERSION and suite.get('rubric_version') == RUBRIC,
            'unsupported app suite/rubric')
    families = defaultdict(list)
    source_ids = {s['id'] for s in suite['sources']}
    for c in suite['scenarios']:
        require(c['source'] == 'synthetic' and c['clinical_approval'] is False,
                'this collector admits public synthetic development cases only')
        require(len(c['prefix']) == 1, 'app cannot inject assistant history')
        ids = [f['id'] for f in c['facts']] + [e['id'] for e in c['events']]
        require(len(ids) == len(set(ids)), 'duplicate fact/event ID')
        for r in c['criteria']:
            require(set(r['requires']) <= set(ids), 'unknown prerequisite')
            require(set(r['source_ids']) <= source_ids, 'unknown source')
        for e in c['events']:
            require(set(e['requires']) <= {f['id'] for f in c['facts']}, 'invalid event prerequisites')
        families[c['family_id']].append(c)
    for pair in families.values():
        require(len(pair) == 2 and {c['variant'] for c in pair} == {'base','distractor'}, 'invalid pair')
        base = next(c for c in pair if c['variant'] == 'base')
        other = deepcopy(next(c for c in pair if c['variant'] == 'distractor'))
        require(other['prefix'][0]['content'] == base['prefix'][0]['content'] + DISTRACTOR,
                'distractor changed more than approved suffix')
        other['scenario_id'] = base['scenario_id']; other['variant'] = 'base'
        other['prefix'] = deepcopy(base['prefix'])
        require(other == base, 'pair has additional changed fields')
    return suite, digest_bytes(raw)


def make_plan(suite, suite_sha, seed=20260912, smoke=False):
    rng = random.Random(seed)
    cases = [c for c in suite['scenarios'] if not smoke or
             (c['family_id'] in {'AP01','AP03','AP05'} and c['variant'] == 'base')]
    cases = list(cases); rng.shuffle(cases)
    slots=[]
    for c in cases:
        platforms=PLATFORMS.copy(); rng.shuffle(platforms)
        for platform in platforms:
            slots.append(dict(slot_id=f'run-{len(slots)+1:02}', scenario_id=c['scenario_id'],
                              platform=platform, repeat=1, purpose='exploratory'))
    return dict(schema_version=VERSION, suite_sha256=suite_sha, seed=seed,
                scope='smoke' if smoke else 'full', slots=slots,
                max_wait_seconds=120, clinical_approval=False)


def render_page(template, payload):
    # Safe inside script[type=application/json], including hostile imported answers.
    data=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    return (ASSETS/template).read_text(encoding='utf-8').replace('__PAYLOAD__',data)


def prepare(out, suite_path=DEFAULT_SUITE, smoke=False, seed=20260912):
    suite, sha = get_suite(suite_path)
    plan=make_plan(suite,sha,seed,smoke)
    out=Path(out); out.mkdir(parents=True,exist_ok=False)
    write_new_json(out/'plan.json',plan)
    payload=dict(suite=suite,plan=plan,plan_sha256=scenario_digest(plan),
                 case_hashes={c['scenario_id']:scenario_digest(c) for c in suite['scenarios']})
    with (out/'collector.html').open('x',encoding='utf-8') as stream:
        stream.write(render_page('collector.html',payload))
    return dict(sessions_planned=len(plan['slots']),real_patient_cases=0,model_calls=0)


def due_event(case, disclosed, answers, fired):
    return next((e for e in case['events'] if e['id'] not in fired
                 and set(e['requires']) <= disclosed and answers >= e['min_assistant_turns']),None)


def validate_capture(session, case):
    meta=session['metadata']
    require(meta.get('app_pilot_version') == VERSION,'missing app pilot version')
    require(meta['comparison_lane'] == 'free_dialogue','app pilot uses free dialogue only')
    require(meta['conversation_reset'] is True,'new conversation required')
    for key in ('session_note','memory_setting','network_setting','device','ended_at','stop_reason','slot_id'):
        require(nonempty(meta.get(key)), 'missing metadata.'+key)
    try:
        end=datetime.fromisoformat(meta['ended_at'].replace('Z','+00:00'))
        start=datetime.fromisoformat(meta['collected_at'].replace('Z','+00:00'))
        require(end.tzinfo is not None and end >= start, 'invalid end timestamp')
    except (ValueError,TypeError) as error:
        raise ValueError('invalid collection timestamps') from error
    require(session['observations'] == [],'raw captures cannot self-score; use bound review packet')
    log=session.get('disclosure_log')
    user_turns=[t for t in session['turns'] if t['role']=='user']
    require(isinstance(log,list) and len(log)==len(user_turns),'missing/extra disclosure log')
    facts={f['id']:f for f in case['facts']}; events={e['id']:e for e in case['events']}
    known=set(); fired=set(); phase='natural'; probe_count=0
    for i,(t,e) in enumerate(zip(user_turns,log)):
        require(e.get('turn_id')==t['turn_id'],'disclosure turn mismatch')
        action=e.get('action'); ids=e.get('fact_ids'); eid=e.get('event_id')
        require(isinstance(ids,list) and len(ids)==len(set(ids)) and set(ids)<=set(facts),'invalid facts')
        require(e.get('phase') in {'natural','probe'},'invalid phase')
        if e['phase']=='probe':
            phase='probe'; probe_count+=1
            require(i>0 and action=='probe' and probe_count<=case['max_probe_answers'],'invalid probe')
        else:
            require(phase=='natural','natural phase cannot follow probe')
            require(i<case['max_natural_answers'],'natural turn budget exceeded')
        if i==0:
            require(action=='opening' and e['phase']=='natural','first turn must be natural opening')
            expected=case['prefix'][0]['content']
        else:
            due=due_event(case,known,i,fired)
            if due and e['phase']=='natural':
                require(action=='event' and eid==due['id'],'due correction must be delivered next')
            if action=='facts':
                require(ids and not eid,'facts action needs IDs only')
                require(nonempty(e.get('question_quote')) and e['question_quote'] in session['turns'][2*i-1]['content'],
                        'fact disclosure needs actual preceding question quote')
                current={fid:f['answer'] for fid,f in facts.items()}
                for event in case['events']:
                    if event['id'] in fired: current.update(event.get('fact_overrides',{}))
                expected='\n'.join(current[fid] for fid in sorted(ids))
                known.update(ids)
            elif action=='event':
                require(eid in events and due and eid==due['id'],'event not eligible or already fired')
                expected=events[eid]['answer']; fired.add(eid); known.add(eid)
            elif action=='unknown': expected=case['unknown']
            elif action=='continue': expected=case['continue_message']
            elif action=='probe': expected=case['probe']
            else: raise ValueError('invalid action')
        if action!='facts': require(not ids,'non-fact action cannot claim facts')
        if action!='event': require(eid is None,'non-event action cannot claim event')
        require(t['content']==expected,'submitted text differs from frozen disclosure')
    require(nonempty(meta.get('stop_reason')),'stop reason required')
    if session['status']=='target_error': require(nonempty(session.get('error_detail')),'target error needs detail')
    return session


def validate_records(records, suite, sha, plan):
    require(plan==make_plan(suite,sha,plan.get('seed'),plan.get('scope')=='smoke'), 'plan changed')
    slots={s['slot_id']:s for s in plan['slots']}
    sessions=validate_batch(records,suite,sha)
    cases={c['scenario_id']:c for c in suite['scenarios']}; seen=set()
    for s in sessions:
        meta=s['metadata']; slot=slots.get(meta.get('slot_id'))
        require(slot is not None and slot['scenario_id']==s['scenario_id'] and slot['platform']==s['platform'],
                'session/plan mismatch')
        require(meta.get('plan_sha256')==scenario_digest(plan),'plan digest mismatch')
        require(slot['slot_id'] not in seen,'duplicate planned run; keep retries in a separate plan')
        seen.add(slot['slot_id']); validate_capture(s,cases[s['scenario_id']])
    return sessions


def review_rows(sessions,suite):
    cases={c['scenario_id']:c for c in suite['scenarios']}; rows=[]
    for s in sessions:
        if s['status']=='measurement_invalid': continue
        case=cases[s['scenario_id']]; known=set(); triggered=set()
        for i,e in enumerate(s['disclosure_log']):
            known.update(e['fact_ids'])
            if e['event_id']: known.add(e['event_id'])
            response=s['turns'][2*i+1] if 2*i+1<len(s['turns']) else None
            for r in case['criteria']:
                if not set(r['requires'])<=known: continue
                triggered.add(r['id'])
                rows.append(dict(row_id=f"{s['session_id']}:{e['turn_id']}:{r['id']}",
                  session_id=s['session_id'],criterion_id=r['id'],dimension=r['dimension'],phase=e['phase'],
                  trigger_turn_id=e['turn_id'],response_turn_id=response['turn_id'] if response else None,
                  available_fact_ids=sorted(known),opportunity='observed' if response else 'not_observed',
                  outcome='unassessed' if response else 'not_observed',serious_error=None,
                  evidence=[],reason=''))
        for r in case['criteria']:
            if r['id'] not in triggered:
                rows.append(dict(row_id=f"{s['session_id']}:untriggered:{r['id']}",session_id=s['session_id'],
                  criterion_id=r['id'],dimension=r['dimension'],phase='natural',trigger_turn_id=None,
                  response_turn_id=None,available_fact_ids=[],opportunity='untriggered',outcome='untriggered',
                  serious_error=None,evidence=[],reason=''))
    return rows


def make_review(sessions,suite,sha,reviewer):
    require(nonempty(reviewer),'reviewer required')
    return dict(schema_version='app-review/v1',rubric_version=RUBRIC,suite_sha256=sha,
                sessions_sha256=scenario_digest(sessions),reviewer_id=reviewer,reviewer_kind='human',
                review_status='provisional',clinical_approval=False,rows=review_rows(sessions,suite))


def validate_review(packet,sessions,suite,sha):
    require(packet.get('schema_version')=='app-review/v1' and packet.get('rubric_version')==RUBRIC,'wrong review version')
    require(packet.get('suite_sha256')==sha and packet.get('sessions_sha256')==scenario_digest(sessions),
            'stale review: suite or sessions changed')
    require(nonempty(packet.get('reviewer_id')) and packet.get('reviewer_kind') in {'human','ai_assisted'},'reviewer required')
    require(packet.get('clinical_approval') is False and packet.get('review_status')=='provisional','cannot self-certify')
    expected=review_rows(sessions,suite); rows=packet.get('rows')
    require(isinstance(rows,list) and len(rows)==len(expected),'missing or extra review rows')
    by_session={s['session_id']:s for s in sessions}; seen=set()
    editable={'outcome','serious_error','evidence','reason'}
    for row,exp in zip(rows,expected):
        require(row['row_id'] not in seen,'duplicate review row'); seen.add(row['row_id'])
        require({k:v for k,v in row.items() if k not in editable}==
                {k:v for k,v in exp.items() if k not in editable},'review row identity/boundary changed')
        outcome=row.get('outcome'); require(outcome in OUTCOMES,'invalid outcome')
        require(isinstance(row.get('reason'),str),'reason must be text')
        serious=row.get('serious_error')
        require(serious is None or type(serious) is bool,'serious error must be bool or null')
        if exp['opportunity']!='observed':
            require(outcome==exp['opportunity'] and serious is None and row['evidence']==[],
                    'unobserved/untriggered row cannot be scored')
            continue
        require(outcome not in {'untriggered','not_observed'},'observed opportunity cannot disappear')
        if outcome in {'pass','fail'}:
            require(type(serious) is bool and nonempty(row['reason']),'decisions require safety assessment and reason')
        else: require(serious is None,'unknown/unscored safety must remain null')
        if serious is True: require(outcome=='fail','serious error cannot pass')
        turns=by_session[row['session_id']]['turns']; indexes={t['turn_id']:i for i,t in enumerate(turns)}
        texts={t['turn_id']:t['content'] for t in turns}; evidence=row.get('evidence')
        require(isinstance(evidence,list),'evidence must be a list')
        for ref in evidence:
            require(isinstance(ref,dict) and ref.get('turn_id') in indexes and nonempty(ref.get('quote')),
                    'evidence needs actual turn and nonempty quote')
            require(indexes[ref['turn_id']]<=indexes[row['response_turn_id']],'future evidence is prohibited')
            require(ref['quote'] in texts[ref['turn_id']],'quote is not in cited turn')
        if outcome in {'pass','fail','insufficient','not_applicable'}:
            require(nonempty(row['reason']) and any(e['turn_id']==row['response_turn_id'] for e in evidence),
                    'decided or insufficient row needs target answer quote and reason')
    return packet


def report(sessions,suite,sha,packets):
    require(1<=len(packets)<=2,'supply one or two reviews')
    for p in packets: validate_review(p,sessions,suite,sha)
    require(len({p['reviewer_id'] for p in packets})==len(packets),'reviewers must differ')
    valid_ids={s['session_id'] for s in sessions if s['status']!='measurement_invalid'}
    counts=defaultdict(Counter); safety=defaultdict(Counter); disagreements=[]; comparable=0; agreements=0
    by_id={s['session_id']:s for s in sessions}
    for i,row in enumerate(packets[0]['rows']):
        if row['session_id'] not in valid_ids: continue
        outcome=row['outcome']
        if len(packets)==2:
            other=packets[1]['rows'][i]
            if row['outcome'] in {'pass','fail'} and other['outcome'] in {'pass','fail'}:
                comparable+=1
                if (row['outcome'],row['serious_error'])==(other['outcome'],other['serious_error']): agreements+=1
            if (outcome,row['serious_error']) != (other['outcome'],other['serious_error']):
                disagreements.append(row['row_id']); outcome='disputed'
        key=(by_id[row['session_id']]['platform'],row['phase'],row['dimension'])
        counts[key][outcome]+=1
        safety[key]['disputed' if outcome=='disputed' else
                    'unassessed' if row['serious_error'] is None else
                    'serious_error' if row['serious_error'] else 'no_serious_error_observed']+=1
    metrics=[]
    for (platform,phase,dim),c in sorted(counts.items()):
        decided=c['pass']+c['fail']
        observed=sum(v for k,v in c.items() if k not in {'untriggered','not_observed'})
        metrics.append(dict(platform=platform,phase=phase,dimension=dim,counts=dict(c),
          safety_counts=dict(safety[(platform,phase,dim)]),
          decided=decided,observed=observed,review_coverage=decided/observed if observed else None,
          conditional_pass_rate=c['pass']/decided if decided else None))
    return dict(schema_version='app-report/v1',sessions=len(sessions),
      unique_families=len({s['family_id'] for s in sessions}),
      statuses=dict(Counter(s['status'] for s in sessions)),metrics=metrics,
      disagreement_row_ids=disagreements,dual_decided_rows=comparable,
      exact_agreement=agreements/comparable if comparable else None,
      clinical_approval=False,overall_pass=None,root_cause_proven=False,
      review_kinds=[p['reviewer_kind'] for p in packets],
      limits='描述性开发试评；逐回答判据不是独立样本，不汇成产品总排名；双人一致不等于临床认证。')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite',default=str(DEFAULT_SUITE))
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('validate-suite')
    prep=sub.add_parser('prepare'); prep.add_argument('--out',required=True)
    prep.add_argument('--smoke',action='store_true'); prep.add_argument('--seed',type=int,default=20260912)
    imp=sub.add_parser('import'); imp.add_argument('--input',nargs='+',required=True)
    for parser in (imp,):
        parser.add_argument('--plan',required=True); parser.add_argument('--out',required=True)
    rev=sub.add_parser('review-template'); rev.add_argument('--reviewer',required=True)
    rep=sub.add_parser('report'); rep.add_argument('--reviews',nargs='+',required=True)
    for parser in (rev,rep):
        parser.add_argument('--sessions',required=True); parser.add_argument('--plan',required=True)
        parser.add_argument('--out',required=True)
    a=p.parse_args(argv)
    try:
        suite,sha=get_suite(a.suite)
        if a.command=='validate-suite': result=dict(cases=len(suite['scenarios']),families=len(suite['scenarios'])//2)
        elif a.command=='prepare': result=prepare(a.out,a.suite,a.smoke,a.seed)
        elif a.command=='import':
            records=[]
            for path in a.input:
                value=read_json(path); require(isinstance(value,list),'capture must be a list'); records.extend(value)
            sessions=validate_records(records,suite,sha,read_json(a.plan))
            write_new_json(a.out,sessions); result=dict(imported=len(sessions),clinical_approval=False)
        else:
            sessions=validate_records(read_json(a.sessions),suite,sha,read_json(a.plan))
            if a.command=='review-template':
                packet=make_review(sessions,suite,sha,a.reviewer); write_new_json(a.out,packet)
                html_path=Path(a.out).with_suffix('.html')
                with html_path.open('x',encoding='utf-8') as stream:
                    stream.write(render_page('review.html',dict(packet=packet,sessions=sessions,suite=suite)))
                result=dict(rows=len(packet['rows']),scored=0)
            else:
                result=report(sessions,suite,sha,[read_json(f) for f in a.reviews]); write_new_json(a.out,result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as error:
        p.exit(2,f'app pilot failed: {error}\n')


if __name__=='__main__': main()
