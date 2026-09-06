#!/usr/bin/env python3
import argparse, json
from collections import Counter
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--gold',required=True); ap.add_argument('--pred',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    g=load(a.gold); pm={x['query_id']:x for x in load(a.pred)['predictions']}
    rows=[]; counts=Counter(); subgroup=Counter(); subgroup_ok=Counter(); high=miss=0
    for x in g['queries']:
        p=pm.get(x['query_id'],{}); intent_ok=p.get('predicted_intent')==x['expected_intent']; src=(p.get('ranked_source_ids') or []); primary_ok=bool(src) and src[0]==x['expected_primary_source_id']; acceptable=any(s in set(x['acceptable_source_ids']) for s in src[:3]); ok=intent_ok and primary_ok and acceptable
        sub=x.get('subset','other'); subgroup[sub]+=1; subgroup_ok[sub]+=int(ok)
        if x.get('high_risk'): high+=1; miss+=int(not acceptable)
        if not ok:
            rows.append({'query_id':x['query_id'],'query':x['query'],'subset':sub,'expected_intent':x['expected_intent'],'predicted_intent':p.get('predicted_intent'),'expected_primary_source_id':x['expected_primary_source_id'],'predicted_sources':src,'feature_hits':p.get('feature_hits',{}),'negated_feature_hits':p.get('negated_feature_hits',{}),'excluded_source_ids':p.get('excluded_source_ids',[])})
    n=len(g['queries']); intent=sum(pm.get(x['query_id'],{}).get('predicted_intent')==x['expected_intent'] for x in g['queries']); pri=sum(bool(pm.get(x['query_id'],{}).get('ranked_source_ids')) and pm[x['query_id']]['ranked_source_ids'][0]==x['expected_primary_source_id'] for x in g['queries']); acc=sum(any(s in set(x['acceptable_source_ids']) for s in (pm.get(x['query_id'],{}).get('ranked_source_ids') or [])[:3]) for x in g['queries'])
    metrics={'n_queries':n,'intent_accuracy':intent/n,'primary_source_accuracy':pri/n,'acceptable_source_recall_at_3':acc/n,'negation_subset_accuracy':subgroup_ok['negation']/subgroup['negation'],'legacy_subset_accuracy':subgroup_ok['legacy']/subgroup['legacy'],'high_risk_source_miss_rate':miss/high if high else 0.0,'failure_count':len(rows)}
    c=g['release_criteria']; checks={'overall_intent':metrics['intent_accuracy']>=c['min_overall_intent_accuracy'],'overall_primary':metrics['primary_source_accuracy']>=c['min_overall_primary_source_accuracy'],'negation_subset':metrics['negation_subset_accuracy']>=c['min_negation_subset_accuracy'],'critical_miss':metrics['high_risk_source_miss_rate']<=c['max_high_risk_source_miss_rate']}
    out={'benchmark_id':g['benchmark_id'],'router_version':next(iter(pm.values())).get('router_version') if pm else None,'metrics':metrics,'gate_checks':checks,'release_gate':'PASS' if all(checks.values()) else 'FAIL','failures':rows}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(out,ensure_ascii=False,indent=2)); return 0 if out['release_gate']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
