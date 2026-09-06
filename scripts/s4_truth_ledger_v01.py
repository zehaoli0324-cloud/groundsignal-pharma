#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import datetime
from dataclasses import dataclass, field
from typing import Any


REQUIRED_PROVENANCE = ("source_id", "passage_id", "locator", "source_version")
AUTO_ALLOWED_RELATION = "DIRECT_SUPPORT"
ALLOWED_REVIEW_STATES = {"SOURCE_VERIFIED", "DOMAIN_REVIEWED", "GOLD_APPROVED"}


def _stable(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_stable(value).encode("utf-8")).hexdigest()[:20]


def _norm(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().split())
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in sorted(value.items())}
    return value


def _slot_key(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "subject_id": p["subject_id"],
        "predicate": p["predicate"],
        "population": _norm(p.get("population")),
        "conditions": _norm(p.get("conditions", {})),
        "jurisdiction": p.get("jurisdiction"),
    }


def _claim_key(p: dict[str, Any]) -> dict[str, Any]:
    return {
        **_slot_key(p),
        "object_id": p["object_id"],
        "polarity": p.get("polarity", "POSITIVE"),
    }


def _parse_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("effective_at must be ISO date string")
    try:
        return str(datetime.date.fromisoformat(value))
    except Exception as exc:
        raise ValueError("effective_at must be YYYY-MM-DD") from exc


@dataclass
class TruthLedger:
    graph_partition: str = "clinical_external"
    edges: dict[str, dict[str, Any]] = field(default_factory=dict)
    transactions: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "graph_partition": self.graph_partition,
            "edges": copy.deepcopy(self.edges),
        }

    def state_hash(self) -> str:
        return hashlib.sha256(_stable(self.snapshot()).encode("utf-8")).hexdigest()

    def _reject(self, event: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "event_id": event.get("event_id"),
            "action": "REJECTED",
            "reason": reason,
            "changed_edge_ids": [],
            "active_truth_changed": False,
        }

    def _validate(self, event: dict[str, Any]) -> str | None:
        p = event.get("proposition")
        if not isinstance(p, dict):
            return "MISSING_PROPOSITION"
        for key in ("subject_id", "predicate", "object_id", "effective_at"):
            if not p.get(key):
                return f"MISSING_{key.upper()}"
        try:
            _parse_date(p["effective_at"])
        except ValueError:
            return "INVALID_EFFECTIVE_AT"

        provenance = event.get("provenance")
        if not isinstance(provenance, dict):
            return "MISSING_PROVENANCE"
        for key in REQUIRED_PROVENANCE:
            if not provenance.get(key):
                return f"MISSING_PROVENANCE_{key.upper()}"

        if event.get("s3_relation") != AUTO_ALLOWED_RELATION:
            return "S3_RELATION_NOT_DIRECT_SUPPORT"
        if event.get("review_status") not in ALLOWED_REVIEW_STATES:
            return "SOURCE_NOT_VERIFIED"

        source_scope = event.get("source_scope", "external")
        if source_scope == "synthetic_controlled" and self.graph_partition != "benchmark_synthetic":
            return "SYNTHETIC_PARTITION_VIOLATION"
        if source_scope != "synthetic_controlled" and self.graph_partition == "benchmark_synthetic":
            return "EXTERNAL_PARTITION_VIOLATION"
        return None

    def _provenance_record(self, event: dict[str, Any]) -> dict[str, Any]:
        p = event["provenance"]
        return {
            "source_id": p["source_id"],
            "passage_id": p["passage_id"],
            "locator": p["locator"],
            "source_version": p["source_version"],
            "retrieved_at": p.get("retrieved_at"),
            "review_status": event["review_status"],
            "source_scope": event.get("source_scope", "external"),
            "s3_relation": event["s3_relation"],
        }

    def ingest(self, event: dict[str, Any]) -> dict[str, Any]:
        reason = self._validate(event)
        if reason:
            return self._reject(event, reason)

        before = self.snapshot()
        p = copy.deepcopy(event["proposition"])
        p["effective_at"] = _parse_date(p["effective_at"])
        p["polarity"] = p.get("polarity", "POSITIVE")
        p["population"] = _norm(p.get("population"))
        p["conditions"] = _norm(p.get("conditions", {}))
        p["jurisdiction"] = p.get("jurisdiction")
        slot = _slot_key(p)
        claim = _claim_key(p)
        slot_id = _hash("slot:", slot)
        claim_id = _hash("claim:", claim)
        provenance = self._provenance_record(event)

        same_claim = [e for e in self.edges.values() if e["claim_id"] == claim_id and e["effective_at"] == p["effective_at"]]
        if same_claim:
            edge = sorted(same_claim, key=lambda e: e["edge_id"])[0]
            if provenance not in edge["provenance"]:
                edge["provenance"].append(provenance)
                edge["provenance"] = sorted(edge["provenance"], key=_stable)
            result = {
                "event_id": event["event_id"],
                "action": "MERGED_IDEMPOTENT",
                "reason": None,
                "changed_edge_ids": [edge["edge_id"]],
                "active_truth_changed": False,
            }
            self.transactions.append({"event_id": event["event_id"], "before": before, "result": result})
            return result

        edge_id = _hash("edge:", {
            "claim_id": claim_id,
            "effective_at": p["effective_at"],
            "source_version": provenance["source_version"],
        })
        new_edge = {
            "edge_id": edge_id,
            "slot_id": slot_id,
            "claim_id": claim_id,
            "subject_id": p["subject_id"],
            "predicate": p["predicate"],
            "object_id": p["object_id"],
            "polarity": p["polarity"],
            "population": p["population"],
            "conditions": p["conditions"],
            "jurisdiction": p["jurisdiction"],
            "effective_at": p["effective_at"],
            "lifecycle_status": "ACTIVE",
            "superseded_by": None,
            "conflicts_with": [],
            "provenance": [provenance],
        }

        peers = [e for e in self.edges.values() if e["slot_id"] == slot_id]
        active_peers = [e for e in peers if e["lifecycle_status"] == "ACTIVE"]
        contested_peers = [e for e in peers if e["lifecycle_status"] == "CONTESTED"]
        changed = []
        active_truth_changed = False
        action = "INSERTED_ACTIVE"

        newer_active = [e for e in active_peers if e["effective_at"] > p["effective_at"]]
        equal_active = [e for e in active_peers if e["effective_at"] == p["effective_at"]]
        older_active = [e for e in active_peers if e["effective_at"] < p["effective_at"]]

        if newer_active:
            new_edge["lifecycle_status"] = "SUPERSEDED"
            newest = max(newer_active, key=lambda e: e["effective_at"])
            new_edge["superseded_by"] = newest["edge_id"]
            action = "INSERTED_HISTORICAL"
        elif equal_active:
            new_edge["lifecycle_status"] = "CONTESTED"
            for peer in equal_active:
                peer["lifecycle_status"] = "CONTESTED"
                if edge_id not in peer["conflicts_with"]:
                    peer["conflicts_with"].append(edge_id)
                    peer["conflicts_with"].sort()
                new_edge["conflicts_with"].append(peer["edge_id"])
                changed.append(peer["edge_id"])
            new_edge["conflicts_with"] = sorted(set(new_edge["conflicts_with"]))
            action = "CONTRADICTION_RECORDED"
            active_truth_changed = True
        else:
            for peer in older_active:
                peer["lifecycle_status"] = "SUPERSEDED"
                peer["superseded_by"] = edge_id
                changed.append(peer["edge_id"])
            if contested_peers:
                max_contested_date = max(e["effective_at"] for e in contested_peers)
                if p["effective_at"] > max_contested_date:
                    for peer in contested_peers:
                        if peer["effective_at"] == max_contested_date:
                            peer["lifecycle_status"] = "SUPERSEDED"
                            peer["superseded_by"] = edge_id
                            changed.append(peer["edge_id"])
            active_truth_changed = bool(older_active or contested_peers or not peers)
            action = "SUPERSEDED_PRIOR" if older_active or contested_peers else "INSERTED_ACTIVE"

        self.edges[edge_id] = new_edge
        changed.append(edge_id)
        changed = sorted(set(changed))
        result = {
            "event_id": event["event_id"],
            "action": action,
            "reason": None,
            "changed_edge_ids": changed,
            "active_truth_changed": active_truth_changed,
        }
        self.transactions.append({"event_id": event["event_id"], "before": before, "result": result})
        return result

    def rollback_last(self) -> dict[str, Any]:
        if not self.transactions:
            return {"action": "NOOP", "rolled_back_event_id": None}
        tx = self.transactions.pop()
        self.graph_partition = tx["before"]["graph_partition"]
        self.edges = copy.deepcopy(tx["before"]["edges"])
        return {"action": "ROLLED_BACK", "rolled_back_event_id": tx["event_id"]}

    def summary(self) -> dict[str, Any]:
        lifecycle = {}
        for edge in self.edges.values():
            lifecycle[edge["lifecycle_status"]] = lifecycle.get(edge["lifecycle_status"], 0) + 1
        unresolved_slots = sorted({
            e["slot_id"] for e in self.edges.values()
            if e["lifecycle_status"] == "CONTESTED"
        })
        active = sorted(
            e["edge_id"] for e in self.edges.values()
            if e["lifecycle_status"] == "ACTIVE"
        )
        stale_active = 0
        for e in self.edges.values():
            if e["lifecycle_status"] != "ACTIVE":
                continue
            later = [
                p for p in self.edges.values()
                if p["slot_id"] == e["slot_id"] and p["effective_at"] > e["effective_at"]
                and p["lifecycle_status"] in {"ACTIVE", "CONTESTED"}
            ]
            if later:
                stale_active += 1
        return {
            "edge_count": len(self.edges),
            "lifecycle_counts": dict(sorted(lifecycle.items())),
            "active_edge_ids": active,
            "unresolved_contradiction_slots": unresolved_slots,
            "stale_active_edge_count": stale_active,
            "state_hash": self.state_hash(),
        }
