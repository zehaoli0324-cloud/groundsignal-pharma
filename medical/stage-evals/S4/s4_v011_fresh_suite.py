"""Frozen independent fresh held-out suite for S4 truth-ledger v0.1.1.

Created after implementation freeze commit 8d0406df9bb91b16d3201e2b0cf97a0f084e1dad.
Do not edit after first observation; later reuse is exposed regression only.
"""
import copy

FREEZE_COMMIT = "8d0406df9bb91b16d3201e2b0cf97a0f084e1dad"
IMPLEMENTATION_BLOB = "3063927fb22c711ee35f6d629d61284455363cd5"
BASE_V01_BLOB = "860e8b38131e74d9dc06160bd95ade8bd04e77df"

BASE = {
    "event_id": "fv11-base",
    "proposition": {
        "subject_id": "drug:fv11-alpha", "predicate": "HAS_CONTROLLED_RULE",
        "object_id": "rule:base", "polarity": "POSITIVE", "population": "adult",
        "conditions": {"care": "ambulatory"}, "jurisdiction": "US",
        "effective_at": "2026-04-15",
    },
    "provenance": {
        "source_id": "CONTROLLED_V011_A", "passage_id": "p0",
        "locator": "fixture", "source_version": "sv0", "retrieved_at": "2026-09-06",
    },
    "s3_relation": "DIRECT_SUPPORT", "review_status": "SOURCE_VERIFIED", "source_scope": "external",
}

def I(eid, prop=None, prov=None, **extra):
    e = {"event_id": eid}
    if prop: e["proposition"] = prop
    if prov: e["provenance"] = prov
    e.update(extra)
    return {"op": "ingest", "event": e}

def D(eid, path):
    return {"op": "ingest", "event": {"event_id": eid}, "drop": [path]}

def CP(name): return {"op": "checkpoint", "name": name}
def RB(): return {"op": "rollback_last"}
def AC(name): return {"op": "assert_checkpoint", "name": name}

CASES = [
{"case_id":"S4F11-001","name":"five-version monotonic chain","tags":["temporal","long_chain"],
 "steps":[I("v22",{"object_id":"r22","effective_at":"2022-04-15"},{"passage_id":"p22","source_version":"s22"}),
          I("v23",{"object_id":"r23","effective_at":"2023-04-15"},{"passage_id":"p23","source_version":"s23"}),
          I("v24",{"object_id":"r24","effective_at":"2024-04-15"},{"passage_id":"p24","source_version":"s24"}),
          I("v25",{"object_id":"r25","effective_at":"2025-04-15"},{"passage_id":"p25","source_version":"s25"}),
          I("v26",{"object_id":"r26"},{"passage_id":"p26","source_version":"s26"})],
 "expect":{"actions":["INSERTED_ACTIVE","SUPERSEDED_PRIOR","SUPERSEDED_PRIOR","SUPERSEDED_PRIOR","SUPERSEDED_PRIOR"],
           "edge_count":5,"active_count":1,"contested_count":0,"superseded_count":4,"stale_active":0,"active_objects":["r26"],"rejections":0}},

{"case_id":"S4F11-002","name":"contested frontier blocks three old arrivals","tags":["temporal","contradiction","late_arrival"],
 "steps":[I("a",{"object_id":"a"},{"passage_id":"pa","source_version":"sa"}),
          I("b",{"object_id":"b"},{"source_id":"SRCB","passage_id":"pb","source_version":"sb"}),
          I("o5",{"object_id":"o5","effective_at":"2025-04-15"},{"passage_id":"po5","source_version":"so5"}),
          I("o4",{"object_id":"o4","effective_at":"2024-04-15"},{"passage_id":"po4","source_version":"so4"}),
          I("o3",{"object_id":"o3","effective_at":"2023-04-15"},{"passage_id":"po3","source_version":"so3"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","INSERTED_HISTORICAL","INSERTED_HISTORICAL","INSERTED_HISTORICAL"],
           "edge_count":5,"active_count":0,"contested_count":2,"superseded_count":3,"stale_active":0,"unresolved_contradiction_slots":1,"rejections":0}},

{"case_id":"S4F11-003","name":"contest resolve recontest resolve","tags":["temporal","contradiction","frontier_closure","long_chain"],
 "steps":[I("a",{"object_id":"a","effective_at":"2024-06-01"},{"passage_id":"pa","source_version":"sa"}),
          I("b",{"object_id":"b","effective_at":"2024-06-01"},{"source_id":"SRCB","passage_id":"pb","source_version":"sb"}),
          I("c",{"object_id":"c","effective_at":"2025-06-01"},{"passage_id":"pc","source_version":"sc"}),
          I("d",{"object_id":"d","effective_at":"2025-06-01"},{"source_id":"SRCD","passage_id":"pd","source_version":"sd"}),
          I("e",{"object_id":"e"},{"passage_id":"pe","source_version":"se"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","SUPERSEDED_PRIOR","CONTRADICTION_RECORDED","SUPERSEDED_PRIOR"],
           "edge_count":5,"active_count":1,"contested_count":0,"superseded_count":4,"stale_active":0,"active_objects":["e"],"rejections":0}},

{"case_id":"S4F11-004","name":"four-way contested closure","tags":["contradiction","frontier_closure"],
 "steps":[I("a",{"object_id":"a"},{"passage_id":"pa","source_version":"sa"}),
          I("b",{"object_id":"b"},{"source_id":"B","passage_id":"pb","source_version":"sb"}),
          I("c",{"object_id":"c"},{"source_id":"C","passage_id":"pc","source_version":"sc"}),
          I("d",{"object_id":"d"},{"source_id":"D","passage_id":"pd","source_version":"sd"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","CONTRADICTION_RECORDED","CONTRADICTION_RECORDED"],
           "edge_count":4,"active_count":0,"contested_count":4,"superseded_count":0,"stale_active":0,"unresolved_contradiction_slots":1,"rejections":0}},

{"case_id":"S4F11-005","name":"late duplicate enriches superseded contested history","tags":["temporal","contradiction","provenance","late_arrival"],
 "steps":[I("a1",{"object_id":"a","effective_at":"2024-01-01"},{"passage_id":"pa1","source_version":"sa"}),
          I("b",{"object_id":"b","effective_at":"2024-01-01"},{"source_id":"B","passage_id":"pb","source_version":"sb"}),
          I("r",{"object_id":"resolved"},{"passage_id":"pr","source_version":"sr"}),
          I("a2",{"object_id":"a","effective_at":"2024-01-01"},{"source_id":"A2","passage_id":"pa2","source_version":"sa2"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","SUPERSEDED_PRIOR","MERGED_IDEMPOTENT"],
           "edge_count":3,"active_count":1,"contested_count":0,"superseded_count":2,"stale_active":0,"active_objects":["resolved"],"min_provenance_on_any_edge":2,"rejections":0}},

{"case_id":"S4F11-006","name":"duplicate current contested claim preserves abstention","tags":["contradiction","provenance"],
 "steps":[I("a1",{"object_id":"a"},{"passage_id":"pa1","source_version":"sa1"}),
          I("b",{"object_id":"b"},{"source_id":"B","passage_id":"pb","source_version":"sb"}),
          I("a2",{"object_id":"a"},{"source_id":"A2","passage_id":"pa2","source_version":"sa2"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","MERGED_IDEMPOTENT"],
           "edge_count":2,"active_count":0,"contested_count":2,"superseded_count":0,"stale_active":0,"min_provenance_on_any_edge":2,"rejections":0}},

{"case_id":"S4F11-007","name":"combined scope isolation","tags":["scope"],
 "steps":[I("uao",{"object_id":"uao","jurisdiction":"US","population":"adult","conditions":{"care":"ambulatory"}},{"passage_id":"p1","source_version":"s1"}),
          I("upo",{"object_id":"upo","jurisdiction":"US","population":"pediatric","conditions":{"care":"ambulatory"}},{"passage_id":"p2","source_version":"s2"}),
          I("eao",{"object_id":"eao","jurisdiction":"EU","population":"adult","conditions":{"care":"ambulatory"}},{"passage_id":"p3","source_version":"s3"}),
          I("uai",{"object_id":"uai","jurisdiction":"US","population":"adult","conditions":{"care":"inpatient"}},{"passage_id":"p4","source_version":"s4"})],
 "expect":{"actions":["INSERTED_ACTIVE"]*4,"edge_count":4,"active_count":4,"contested_count":0,"superseded_count":0,"stale_active":0,"active_objects":["eao","uai","uao","upo"],"rejections":0}},

{"case_id":"S4F11-008","name":"condition conflict isolated from parallel condition","tags":["scope","contradiction"],
 "steps":[I("ra",{"object_id":"ra","conditions":{"care":"ambulatory","renal":"impaired"}},{"passage_id":"pra","source_version":"sra"}),
          I("rb",{"object_id":"rb","conditions":{"renal":"impaired","care":"ambulatory"}},{"source_id":"RB","passage_id":"prb","source_version":"srb"}),
          I("h",{"object_id":"hep","conditions":{"care":"ambulatory","hepatic":"impaired"}},{"passage_id":"ph","source_version":"sh"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","INSERTED_ACTIVE"],"edge_count":3,"active_count":1,"contested_count":2,"superseded_count":0,"stale_active":0,"active_objects":["hep"],"rejections":0}},

{"case_id":"S4F11-009","name":"interleaved subjects preserve separate histories","tags":["scope","temporal","contradiction","long_chain"],
 "steps":[I("a1",{"subject_id":"slot:a","object_id":"a1","effective_at":"2025-01-01"},{"passage_id":"pa1","source_version":"sa1"}),
          I("b1",{"subject_id":"slot:b","object_id":"b1","effective_at":"2024-01-01"},{"passage_id":"pb1","source_version":"sb1"}),
          I("a2",{"subject_id":"slot:a","object_id":"a2","effective_at":"2025-01-01"},{"source_id":"A2","passage_id":"pa2","source_version":"sa2"}),
          I("b2",{"subject_id":"slot:b","object_id":"b2"},{"passage_id":"pb2","source_version":"sb2"}),
          I("a3",{"subject_id":"slot:a","object_id":"a3"},{"passage_id":"pa3","source_version":"sa3"})],
 "expect":{"actions":["INSERTED_ACTIVE","INSERTED_ACTIVE","CONTRADICTION_RECORDED","SUPERSEDED_PRIOR","SUPERSEDED_PRIOR"],
           "edge_count":5,"active_count":2,"contested_count":0,"superseded_count":3,"stale_active":0,"active_objects":["a3","b2"],"rejections":0}},

{"case_id":"S4F11-010","name":"rollback resolver restores contested frontier","tags":["rollback","temporal","contradiction"],
 "steps":[I("a",{"object_id":"a","effective_at":"2025-05-01"},{"passage_id":"pa","source_version":"sa"}),
          I("b",{"object_id":"b","effective_at":"2025-05-01"},{"source_id":"B","passage_id":"pb","source_version":"sb"}),
          CP("c"),I("r",{"object_id":"r"},{"passage_id":"pr","source_version":"sr"}),RB(),AC("c")],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","CHECKPOINT","SUPERSEDED_PRIOR","ROLLED_BACK","CHECKPOINT_MATCH"],
           "edge_count":2,"active_count":0,"contested_count":2,"superseded_count":0,"stale_active":0,"rollback_exact":True,"rejections":0}},

{"case_id":"S4F11-011","name":"rollback third conflict restores two-way set","tags":["rollback","contradiction","frontier_closure"],
 "steps":[I("a",{"object_id":"a"},{"passage_id":"pa","source_version":"sa"}),
          I("b",{"object_id":"b"},{"source_id":"B","passage_id":"pb","source_version":"sb"}),
          CP("two"),I("c",{"object_id":"c"},{"source_id":"C","passage_id":"pc","source_version":"sc"}),RB(),AC("two")],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","CHECKPOINT","CONTRADICTION_RECORDED","ROLLED_BACK","CHECKPOINT_MATCH"],
           "edge_count":2,"active_count":0,"contested_count":2,"superseded_count":0,"stale_active":0,"rollback_exact":True,"rejections":0}},

{"case_id":"S4F11-012","name":"rollback provenance merge restores exact source set","tags":["rollback","provenance"],
 "steps":[I("a1",{"object_id":"a"},{"passage_id":"pa1","source_version":"sa1"}),CP("one"),
          I("a2",{"object_id":"a"},{"source_id":"A2","passage_id":"pa2","source_version":"sa2"}),RB(),AC("one")],
 "expect":{"actions":["INSERTED_ACTIVE","CHECKPOINT","MERGED_IDEMPOTENT","ROLLED_BACK","CHECKPOINT_MATCH"],
           "edge_count":1,"active_count":1,"contested_count":0,"superseded_count":0,"stale_active":0,"max_provenance_on_any_edge":1,"rollback_exact":True,"rejections":0}},

{"case_id":"S4F11-013","name":"polarity conflict resolved by future evidence","tags":["temporal","contradiction"],
 "steps":[I("p",{"object_id":"same","polarity":"POSITIVE","effective_at":"2025-01-01"},{"passage_id":"pp","source_version":"sp"}),
          I("n",{"object_id":"same","polarity":"NEGATIVE","effective_at":"2025-01-01"},{"source_id":"N","passage_id":"pn","source_version":"sn"}),
          I("f",{"object_id":"future"},{"passage_id":"pf","source_version":"sf"})],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","SUPERSEDED_PRIOR"],"edge_count":3,"active_count":1,"contested_count":0,"superseded_count":2,"stale_active":0,"active_objects":["future"],"rejections":0}},

{"case_id":"S4F11-014","name":"missing source id rejected","tags":["safety","provenance"],"steps":[D("bad","provenance.source_id")],
 "expect":{"actions":["REJECTED"],"edge_count":0,"active_count":0,"stale_active":0,"rejections":1,"rejection_reasons":["MISSING_PROVENANCE_SOURCE_ID"]},"must_reject":True},

{"case_id":"S4F11-015","name":"missing predicate rejected","tags":["safety"],"steps":[D("bad","proposition.predicate")],
 "expect":{"actions":["REJECTED"],"edge_count":0,"active_count":0,"stale_active":0,"rejections":1,"rejection_reasons":["MISSING_PREDICATE"]},"must_reject":True},

{"case_id":"S4F11-016","name":"unreviewed source rejected","tags":["safety"],"steps":[I("bad",review_status="MACHINE_PARSED")],
 "expect":{"actions":["REJECTED"],"edge_count":0,"active_count":0,"stale_active":0,"rejections":1,"rejection_reasons":["SOURCE_NOT_VERIFIED"]},"must_reject":True},

{"case_id":"S4F11-017","name":"partial support rejected","tags":["safety"],"steps":[I("bad",s3_relation="PARTIAL_SUPPORT")],
 "expect":{"actions":["REJECTED"],"edge_count":0,"active_count":0,"stale_active":0,"rejections":1,"rejection_reasons":["S3_RELATION_NOT_DIRECT_SUPPORT"]},"must_reject":True},

{"case_id":"S4F11-018","name":"synthetic source rejected from clinical partition","tags":["safety","partition"],
 "steps":[I("bad",prov={"source_id":"SYN","passage_id":"sp","locator":"f","source_version":"sv"},source_scope="synthetic_controlled")],
 "expect":{"actions":["REJECTED"],"edge_count":0,"active_count":0,"stale_active":0,"rejections":1,"rejection_reasons":["SYNTHETIC_PARTITION_VIOLATION"]},"must_reject":True},

{"case_id":"S4F11-019","name":"external source rejected from synthetic partition","tags":["safety","partition"],"graph_partition":"benchmark_synthetic",
 "steps":[I("bad")],
 "expect":{"actions":["REJECTED"],"edge_count":0,"active_count":0,"stale_active":0,"rejections":1,"rejection_reasons":["EXTERNAL_PARTITION_VIOLATION"]},"must_reject":True},

{"case_id":"S4F11-020","name":"rejected event preserves contested state exactly","tags":["safety","contradiction","rollback"],
 "steps":[I("a",{"object_id":"a"},{"passage_id":"pa","source_version":"sa"}),
          I("b",{"object_id":"b"},{"source_id":"B","passage_id":"pb","source_version":"sb"}),
          CP("before"),I("bad",s3_relation="DOES_NOT_SUPPORT"),AC("before")],
 "expect":{"actions":["INSERTED_ACTIVE","CONTRADICTION_RECORDED","CHECKPOINT","REJECTED","CHECKPOINT_MATCH"],
           "edge_count":2,"active_count":0,"contested_count":2,"superseded_count":0,"stale_active":0,"rollback_exact":True,
           "rejections":1,"rejection_reasons":["S3_RELATION_NOT_DIRECT_SUPPORT"]},"must_reject":True},
]

SUITE = {
    "benchmark_id": "S4-truth-ledger-v0.1.1-independent-fresh-heldout-v0.1",
    "split": "fresh_heldout", "fresh_heldout": True,
    "created_after_implementation_freeze": True,
    "implementation_freeze_commit": FREEZE_COMMIT,
    "implementation_blob_sha": IMPLEMENTATION_BLOB,
    "base_v01_blob_sha": BASE_V01_BLOB,
    "release_criteria": {
        "min_case_accuracy": 1.0, "required_tag_accuracy": 1.0,
        "max_high_risk_false_accept_count": 0, "max_stale_active_edge_count": 0,
        "max_invariant_violation_count": 0,
    },
    "base_event": BASE, "cases": CASES,
}
