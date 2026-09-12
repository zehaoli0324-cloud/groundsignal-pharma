"""Sequential cases, independent contexts, bounded calls, append-only journals."""
from copy import deepcopy
import json
import os
from pathlib import Path
from scripts.patient_eval.patient import PatientSimulator
from scripts.patient_eval.contracts import require,validate_session
from scripts.patient_eval.import_batch import scenario_digest,write_new_json
from .assets import VERSION,POLICY

ERRORS={'transport_error','output_incomplete','invalid_response_schema','collector_exception'}

def clean_result(result):
    if not isinstance(result,dict):return dict(content=None,error='invalid_response_schema',usage={},provider_model='unknown')
    error=result.get('error')
    if error is not None and not (isinstance(error,str) and (error in ERRORS or error.startswith('http_') and error[5:].isdigit())):error='invalid_response_schema'
    text=result.get('content')
    if text is not None and not isinstance(text,str): text=None;error='invalid_response_schema'
    if not error and (not text or not text.strip()):error='invalid_response_schema'
    model=result.get('provider_model','unknown')
    if not isinstance(model,str):model='unknown'
    usage=result.get('usage',{})
    if not isinstance(usage,dict):usage={}
    return dict(content=text,error=error,provider_model=model,usage={k:v for k,v in usage.items() if k in {'input_tokens','output_tokens','total_tokens'} and type(v) is int and v>=0})

def run_case(case,spec,client,config,slot,emit=lambda event:None):
    sim=PatientSimulator(deepcopy(spec));opening=sim.opening()
    s=dict(session_id=slot['id'],scenario_id=case['scenario_id'],family_id=case['family_id'],variant=case['variant'],platform=config['model'],observability='black_box',status='completed',turns=[],trace=[],observations=[],disclosure_log=[],requests=[],patient_steps=[],metadata=dict(benchmark_version=VERSION,configuration_sha256=scenario_digest(config),suite_sha256=config['suite_sha256'],asset_sha256=config['asset_sha256'],clinical_approval=False,repeat=slot['repeat'],run_kind=config['backend']))
    def user(content,phase,action,facts=None,event=None):
        tid='u'+str(len(s['disclosure_log'])+1)
        s['turns'].append(dict(turn_id=tid,role='user',content=content))
        s['disclosure_log'].append(dict(turn_id=tid,phase=phase,action=action,fact_ids=facts or [],event_id=event))
    def call():
        messages=[dict(role='system',content=POLICY)]+[{k:t[k] for k in ('role','content')} for t in s['turns']]
        emit(dict(kind='request_started',number=len(s['requests'])+1,messages=messages,messages_sha256=scenario_digest(messages)))
        try:result=clean_result(client(deepcopy(messages)))
        except Exception:result=clean_result(dict(content=None,error='collector_exception'))
        request=dict(messages=messages,messages_sha256=scenario_digest(messages),result=result)
        s['requests'].append(request);emit(dict(kind='request_finished',number=len(s['requests']),result=result))
        if result['error']:
            s['status']='measurement_invalid' if result['error']=='collector_exception' else 'target_error'
            s['metadata']['stop_reason']=result['error']
            if s['status']=='measurement_invalid':s.update(invalid_reason='adapter exception',invalid_component='collector')
            return False
        s['turns'].append(dict(turn_id='a'+str(len(s['disclosure_log'])),role='assistant',content=result['content']))
        return True
    user(opening['content'],'natural','opening')
    for index in range(case['max_natural_answers']):
        if not call():break
        step=sim.respond(s['turns'][-1]['content']);s['patient_steps'].append(step)
        emit(dict(kind='patient_decision',step=step))
        if step['done']:
            s['metadata']['stop_reason']='turn_budget';break
        if step['classification']=='unmatched':
            clauses=(step.get('intent_decision') or {}).get('clauses',[])
            ambiguous=any(c.get('reason')=='unsupported_or_ambiguous_slot' for c in clauses)
            if ambiguous:
                s.update(status='measurement_invalid',invalid_reason='patient request needs mapping review',invalid_component='simulator')
                s['metadata']['stop_reason']='unmapped_question'
            else:s['metadata']['stop_reason']='no_supported_followup'
            break
        user(step['content'],'natural','event' if step['event_ids'] else 'facts',step['disclosed'],step['event_ids'][0] if step['event_ids'] else None)
    if config['probe'] and s['status']=='completed':
        user(case['probe'],'probe','probe');call()
    s['patient_snapshot']=sim.snapshot()
    validate_session(s)
    return s


def schedule(suite,repeats):
    return [dict(id=f"{c['scenario_id']}.r{r}",scenario_id=c['scenario_id'],repeat=r) for c in suite['scenarios'] for r in range(repeats)]

def batch(suite,sha,patients,asset_sha,client,out,*,backend,model,repeats=1,probe=False,max_calls=84,max_output_tokens=2048,resume=False):
    require(type(repeats) is int and 1<=repeats<=20,'repeats must be 1..20')
    require(type(probe) is bool and type(max_calls) is int and max_calls>0,'invalid budget')
    slots=schedule(suite,repeats)
    worst=sum(c['max_natural_answers']+int(probe) for c in suite['scenarios'])*repeats
    require(max_calls>=worst,f'budget needs {worst} target calls in worst case; no request sent')
    config=dict(version=VERSION,suite_sha256=sha,asset_sha256=asset_sha,backend=backend,model=model,repeats=repeats,probe=probe,max_calls=max_calls,max_output_tokens=max_output_tokens,slots=slots,policy=POLICY)
    out=Path(out)
    if resume:require(out.is_dir(),'resume directory missing')
    else:out.mkdir(parents=True,exist_ok=False)
    fd=os.open(out/'.lock',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        if resume:require(json.loads((out/'plan.json').read_text())==config,'resume configuration changed')
        else:write_new_json(out/'plan.json',config)
        # An interrupted provider request may have been billed. Never silently resend it.
        for slot in slots:
            require(not (out/(slot['id']+'.journal.jsonl')).exists() or (out/(slot['id']+'.json')).exists(),'interrupted case: inspect journal; start a separate batch after reconciliation')
        cases={c['scenario_id']:c for c in suite['scenarios']}
        for slot in slots:
            path=out/(slot['id']+'.json')
            if path.exists():continue
            journal=out/(slot['id']+'.journal.jsonl')
            with journal.open('x',encoding='utf-8') as stream:
                def emit(event):
                    stream.write(json.dumps(event,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                c=cases[slot['scenario_id']]
                session=run_case(c,patients[c['scenario_id']],client,config,slot,emit)
                write_new_json(path,session)
        return config
    finally:(out/'.lock').unlink(missing_ok=True)
