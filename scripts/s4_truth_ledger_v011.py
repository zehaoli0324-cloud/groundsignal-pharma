#!/usr/bin/env python3
"""S4 v0.1.1 unified temporal frontier + contested-set closure.

Structural repair over v0.1. ACTIVE and unresolved CONTESTED edges are treated
as one current per-slot temporal frontier. Validation, provenance, rollback,
partition safety and scope keys are inherited unchanged from v0.1.
"""
from __future__ import annotations
import copy
from typing import Any
import s4_truth_ledger_v01 as v01

VERSION = "S4-truth-ledger-v0.1.1"
CURRENT_FRONTIER_STATES = {"ACTIVE", "CONTESTED"}

class TruthLedger(v01.TruthLedger):
    @staticmethod
    def _frontier(peers: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
        current=[e for e in peers if e["lifecycle_status"] in CURRENT_FRONTIER_STATES]
        if not current:
            return None, []
        date=max(e["effective_at"] for e in current)
        return date,[e for e in current if e["effective_at"]==date]

    def ingest(self,event:dict[str,Any])->dict[str,Any]:
        reason=self._validate(event)
        if reason:
            return self._reject(event,reason)

        before=self.snapshot()
        p=copy.deepcopy(event["proposition"])
        p["effective_at"]=v01._parse_date(p["effective_at"])
        p["polarity"]=p.get("polarity","POSITIVE")
        p["population"]=v01._norm(p.get("population"))
        p["conditions"]=v01._norm(p.get("conditions",{}))
        p["jurisdiction"]=p.get("jurisdiction")
        slot=v01._slot_key(p); claim=v01._claim_key(p)
        slot_id=v01._hash("slot:",slot); claim_id=v01._hash("claim:",claim)
        provenance=self._provenance_record(event)

        same=[e for e in self.edges.values() if e["claim_id"]==claim_id and e["effective_at"]==p["effective_at"]]
        if same:
            edge=sorted(same,key=lambda e:e["edge_id"])[0]
            if provenance not in edge["provenance"]:
                edge["provenance"].append(provenance)
                edge["provenance"]=sorted(edge["provenance"],key=v01._stable)
            result={"event_id":event["event_id"],"action":"MERGED_IDEMPOTENT","reason":None,
                    "changed_edge_ids":[edge["edge_id"]],"active_truth_changed":False}
            self.transactions.append({"event_id":event["event_id"],"before":before,"result":result})
            return result

        edge_id=v01._hash("edge:",{"claim_id":claim_id,"effective_at":p["effective_at"],"source_version":provenance["source_version"]})
        new={"edge_id":edge_id,"slot_id":slot_id,"claim_id":claim_id,"subject_id":p["subject_id"],
             "predicate":p["predicate"],"object_id":p["object_id"],"polarity":p["polarity"],
             "population":p["population"],"conditions":p["conditions"],"jurisdiction":p["jurisdiction"],
             "effective_at":p["effective_at"],"lifecycle_status":"ACTIVE","superseded_by":None,
             "conflicts_with":[],"provenance":[provenance]}
        peers=[e for e in self.edges.values() if e["slot_id"]==slot_id]
        frontier_date,frontier=self._frontier(peers)
        changed=[]; active_truth_changed=False; action="INSERTED_ACTIVE"

        if frontier_date is not None and p["effective_at"] < frontier_date:
            new["lifecycle_status"]="SUPERSEDED"
            new["superseded_by"]=sorted(frontier,key=lambda e:e["edge_id"])[0]["edge_id"]
            action="INSERTED_HISTORICAL"
        elif frontier_date is not None and p["effective_at"] == frontier_date:
            new["lifecycle_status"]="CONTESTED"
            for peer in frontier:
                peer["lifecycle_status"]="CONTESTED"
                if edge_id not in peer["conflicts_with"]:
                    peer["conflicts_with"].append(edge_id); peer["conflicts_with"].sort()
                new["conflicts_with"].append(peer["edge_id"]); changed.append(peer["edge_id"])
            new["conflicts_with"]=sorted(set(new["conflicts_with"]))
            action="CONTRADICTION_RECORDED"
            active_truth_changed=any(e.get("slot_id")==slot_id and e.get("lifecycle_status")=="ACTIVE" for e in before["edges"].values())
        else:
            # A later fact replaces the whole current frontier, whether resolved
            # ACTIVE truth or an unresolved CONTESTED set.
            for peer in frontier:
                peer["lifecycle_status"]="SUPERSEDED"; peer["superseded_by"]=edge_id; changed.append(peer["edge_id"])
            action="SUPERSEDED_PRIOR" if frontier else "INSERTED_ACTIVE"
            active_truth_changed=bool(frontier or not peers)

        self.edges[edge_id]=new; changed.append(edge_id)
        result={"event_id":event["event_id"],"action":action,"reason":None,
                "changed_edge_ids":sorted(set(changed)),"active_truth_changed":active_truth_changed}
        self.transactions.append({"event_id":event["event_id"],"before":before,"result":result})
        return result
