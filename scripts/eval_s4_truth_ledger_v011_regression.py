#!/usr/bin/env python3
"""Regression evaluator for S4 truth-ledger v0.1.1.

Reuses the frozen v0.1 case expectations after they became exposed. It does not
relabel the historical fresh v0.1 suite as fresh evidence.
"""
from __future__ import annotations
import argparse, copy, json
from collections import defaultdict
from pathlib import Path
from s4_truth_ledger_v011 import TruthLedger, VERSION

def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def deep_merge(base, override):
    out=copy.deepcopy(base)
    for k,v in override.items():
        if isinstance(v,dict) and isinstance(out.get(k),dict): out[k]=deep_merge(out[k],v)
        else: out[k]=copy.deepcopy(v)
    return out
def drop_path(doc,dotted):
    parts=dotted.split('.'); cur=doc
    for p in parts[:-1]: cur=cur.get(p,{})
    if isinstance(cur,dict): cur.pop(parts[-1],None)
def materialize(base,step):
    e=deep_merge(base,step.get('event',{}))
    for p in step.get('drop',[]): drop_path(e,p)
    return e
def counts(ledger):
    vals=list(ledger.edges.values()); s=ledger.summary()
    return {'edge_count':len(vals),'active_count':sum(e['lifecycle_status']=='ACTIVE' for e in vals),
            'contested_count':sum(e['lifecycle_status']=='CONTESTED' for e in vals),
            'superseded_count':sum(e['lifecycle_status']=='SUPERSEDED' for e in vals),
            'stale_active':s['stale_active_edge_count'],
            'unresolved_contradiction_slots':len(s['unresolved_contradiction_slots']),
            'active_objects':sorted(e['object_id'] for e in vals if e['lifecycle_status']=='ACTIVE'),
            'max_provenance_on_any_edge':max((len(e.get('provenance',[])) for e in vals),default=0)}
def run_case(case,base):
    ledger=TruthLedger(graph_partition=case.get('graph_partition','clinical_external'))
    actions=[]; rejects=[]; cps={}; rollback_exact=None
    for step in case['steps']:
        op=step['op']
        if op=='ingest':
            r=ledger.ingest(materialize(base,step)); actions.append(r['action'])
            if r['action']=='REJECTED': rejects.append(r['reason'])
        elif op=='checkpoint': cps[step['name']]=ledger.state_hash(); actions.append('CHECKPOINT')
        elif op=='rollback_last': actions.append(ledger.rollback_last()['action'])
        elif op=='assert_checkpoint':
            rollback_exact=ledger.state_hash()==cps[step['name']]
            actions.append('CHECKPOINT_MATCH' if rollback_exact else 'CHECKPOINT_MISMATCH')
        else: raise ValueError(op)
    got=counts(ledger); got.update(actions=actions,rejections=len(rejects),rejection_reasons=rejects,rollback_exact=rollback_exact)
    failures=[]
    for k,exp in case['expect'].items():
        if k=='min_provenance_on_any_edge':
            if got['max_provenance_on_any_edge']<exp: failures.append({'field':k,'expected':f'>={exp}','got':got['max_provenance_on_any_edge']})
        elif got.get(k)!=exp: failures.append({'field':k,'expected':exp,'got':got.get(k)})
    return {'case_id':case['case_id'],'name':case['name'],'tags':case.get('tags',[]),'must_reject':bool(case.get('must_reject',False)),
            'passed':not failures,'observed':got,'failures':failures}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--suite',required=True); ap.add_argument('--out-dir',required=True); ap.add_argument('--suite-role',choices=['development','exposed_fresh_regression'],required=True); a=ap.parse_args()
    suite=load(a.suite); rows=[run_case(c,suite['base_event']) for c in suite['cases']]
    tags=defaultdict(list)
    for r in rows:
        for t in r['tags']: tags[t].append(r)
    tag_accuracy={t:sum(x['passed'] for x in rs)/len(rs) for t,rs in sorted(tags.items())}
    must=[r for r in rows if r['must_reject']]
    metrics={'benchmark_id':suite['benchmark_id'],'suite_role':a.suite_role,'historical_split':suite.get('split'),
             'fresh_evidence':False,'implementation_version':VERSION,'n_cases':len(rows),'passed_cases':sum(r['passed'] for r in rows),
             'failed_cases':sum(not r['passed'] for r in rows),'case_accuracy':sum(r['passed'] for r in rows)/len(rows),
             'tag_accuracy':tag_accuracy,'must_reject_cases':len(must),
             'high_risk_false_accept_count':sum(r['observed']['rejections']==0 for r in must),
             'stale_active_edge_count':sum(r['observed']['stale_active'] for r in rows)}
    checks={'case_accuracy':metrics['case_accuracy']==1.0,
            'high_risk_false_accept_count':metrics['high_risk_false_accept_count']==0,
            'stale_active_edge_count':metrics['stale_active_edge_count']==0}
    if a.suite_role=='exposed_fresh_regression':
        required=('temporal','contradiction','scope','rollback','safety','partition','provenance')
        checks['required_tag_coverage']=all(t in tag_accuracy for t in required)
        checks['required_tag_accuracy']=all(tag_accuracy.get(t)==1.0 for t in required)
    gate='PASS' if all(checks.values()) else 'FAIL'
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    (out/'metrics.json').write_text(json.dumps({'metrics':metrics,'gate_checks':checks,'regression_gate':gate},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'case-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'failures.json').write_text(json.dumps([r for r in rows if not r['passed']],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'metrics':metrics,'gate_checks':checks,'regression_gate':gate},ensure_ascii=False,indent=2))
    return 0 if gate=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
