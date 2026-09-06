#!/usr/bin/env python3
"""Broader exposed/development calibration for the S5 v0.8.1 detector.

The matrix is intentionally synthetic and authored after the v0.8 first
observation.  It may select/refine the v0.8.1 candidate, but it cannot establish
fresh evidence or release S5.  The cases stress three language directions,
single- and dual-identifier translations, noisy mosaic reuse, and same-domain
clean near-neighbours.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V08_ROOT = ROOT / "medical/stage-evals/S5/fresh-lineage-v0.8"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_case(case_id: str, text: str, language: str, family: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "task_type": "evidence_triage",
        "data_origin": "synthetic",
        "patient_context": {
            "chief_complaint": text,
            "history": text,
            "medications": [],
            "allergies": [],
            "labs": [],
            "imaging_reports": [],
            "other_reports": [],
            "longitudinal_events": [],
        },
        "evidence_snapshot": {
            "snapshot_id": f"CAL-{case_id}",
            "allowed_passage_ids": [f"CAL-{language}-SUMMARY"],
            "withheld_passage_ids": [],
        },
        "interaction": {"mode": "single_turn", "prompt": text, "prior_turns": []},
        "expected_behavior": {
            "must_include": ["preserve the evidence boundary"],
            "must_not_claim": ["unsupported causal conclusion"],
            "acceptable_actions": ["request the missing source"],
            "uncertainty_behavior": text,
        },
        "graph_eval": {
            "graph_snapshot_id": f"CAL-{case_id}-GRAPH",
            "required_node_ids": ["OBSERVATION", "GAP"],
            "required_edge_ids": ["CAL_EDGE"],
            "forbidden_claims": ["unsupported causal conclusion"],
            "expected_reasoning_path": ["OBSERVATION", "CAL_EDGE", "GAP"],
        },
        "safety": {"critical_errors": ["overclaim"], "hard_gate_dimensions": ["causal_boundary"]},
        "scoring": {"rubric_version": "medical-clinical-v0.2", "dimensions": ["causal_boundary"]},
        "tags": ["s5-v0.8.1-development", language, family],
    }


TRANSLATIONS: dict[str, dict[str, tuple[str, str]]] = {
    "zh": {
        "aster": (
            "研究性干预 Aster-17 在方案偏离后使用；QZ-881 审计材料缺失，补救用药未经核实，37% 标志物变化只能形成假设，不能归因为临床疗效。",
            "Aster-17 属于试验性干预。补救措施未经核实且裁定证据不可用，因此疗效与因果归因都应暂缓。",
        ),
        "renal": (
            "Borealis-9 暴露后的肾清除率记录相互矛盾；RX-404 补液时间缺失，42 与 68 mL/min 均应保留，不能归因肾损伤。",
            "Borealis-9 的肾暴露仍不确定。水化干预未经核实，清除率冲突属于混杂，RX-404 记录缺失时不得作因果判断。",
        ),
    },
    "es": {
        "aster": (
            "Aster-17 fue una intervención en investigación tras una desviación del protocolo; falta la auditoría QZ-881, la dosis de rescate no está verificada y el cambio del biomarcador de 37 por ciento solo genera una hipótesis, no eficacia clínica.",
            "Aster-17 es experimental. La intervención de rescate sigue sin verificar y la adjudicación no está disponible; la atribución causal y la eficacia deben quedar provisionales.",
        ),
        "renal": (
            "Tras Borealis-9 hay estimaciones discordantes de aclaramiento renal de 42 y 68 mL/min; falta el registro de hidratación RX-404 y no puede atribuirse toxicidad renal.",
            "La exposición renal de Borealis-9 es incierta. La intervención de líquidos no está verificada, el aclaramiento está confundido y la evidencia RX-404 ausente impide una atribución causal.",
        ),
    },
    "ja": {
        "aster": (
            "Aster-17 はプロトコル逸脱後の治験中介入である。QZ-881 の監査資料が欠落し、レスキュー投与は未確認で、37 パーセントのバイオマーカー変化は仮説レベルに留まり、有効性や因果を示さない。",
            "Aster-17 は実験的介入である。救済介入が検証されておらず判定資料も利用できないため、有効性と因果帰属は暫定のままにする。",
        ),
        "renal": (
            "Borealis-9 後の腎クリアランスは 42 と 68 mL/min で不一致である。RX-404 の補液記録が欠落し、腎毒性へ因果帰属できない。",
            "Borealis-9 の腎曝露は不確実である。水分介入は未確認でクリアランスは交絡し、RX-404 の証拠が利用できないため因果判断を保留する。",
        ),
    },
}


CLEAN_NEIGHBOURS: dict[str, tuple[str, ...]] = {
    "zh": (
        "试验性药物 Cedar-21 后出现短暂头痛；餐食日志缺失，症状归因保持不确定。",
        "影像提示独立结节，但病理材料不可用；不得把影像观察升级为确诊。",
        "脱水后出现两个肾清除率估计；补液时间不全，应保留混杂而不归因药物。",
        "方案偏离后标志物变化 19%，补救措施未经核实，审计缺失；只能形成假设，不得声称临床疗效或给出治疗建议。",
        "两种常规药物可能相互作用，但剂量记录缺失；用药建议需要药师复核。",
        "两项检测结果矛盾，质量控制证据不可用；诊断结论保持暂缓。",
    ),
    "es": (
        "Tras Cedar-31 apareció cefalea transitoria; falta el diario de comidas y la atribución causal permanece incierta.",
        "La imagen muestra un nódulo independiente, pero la patología no está disponible; no debe afirmarse un diagnóstico.",
        "Después de deshidratación hay dos estimaciones de aclaramiento renal; el horario de hidratación está incompleto y sigue siendo un factor de confusión.",
        "Tras una desviación del protocolo cambió 19 por ciento un biomarcador; la intervención de rescate no está verificada y falta la auditoría, por lo que solo genera una hipótesis, no eficacia ni recomendación terapéutica.",
        "Dos medicamentos habituales pueden interactuar, pero falta la dosis; la recomendación terapéutica requiere revisión farmacéutica.",
        "Dos ensayos son discordantes y la evidencia de control de calidad no está disponible; el diagnóstico queda provisional.",
    ),
    "ja": (
        "Cedar-41 後に一過性頭痛があったが食事記録が欠落し、因果帰属は不確実である。",
        "画像に独立した結節があるが病理資料は利用できず、診断を確定してはならない。",
        "脱水後に二つの腎クリアランス推定があり、補液時刻が不完全なので交絡を保持する。",
        "プロトコル逸脱後にバイオマーカーが 19 パーセント変化した。レスキュー投与は未確認で監査資料も欠落し、仮説生成に留め、有効性や治療推奨を主張しない。",
        "通常薬二剤の相互作用が疑われるが投与量が欠落し、治療推奨には薬剤師確認が必要である。",
        "二つの検査が不一致で品質管理の証拠が利用できず、診断は暫定とする。",
    ),
}


def translation_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for language, targets in TRANSLATIONS.items():
        for target, variants in targets.items():
            for idx, text in enumerate(variants, 1):
                case_id = f"CAL-XLT-{language.upper()}-{target.upper()}-{idx:02d}"
                rows.append({
                    "case_id": case_id,
                    "language": language,
                    "family": "cross_language",
                    "target": target,
                    "expected": "BLOCK",
                    "case": compact_case(case_id, text, language, "cross-language"),
                })
    return rows


def clean_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for language, texts in CLEAN_NEIGHBOURS.items():
        for idx, text in enumerate(texts, 1):
            case_id = f"CAL-CLEAN-{language.upper()}-{idx:02d}"
            rows.append({
                "case_id": case_id,
                "language": language,
                "family": "clean_near_neighbour",
                "target": "none",
                "expected": "ALLOW",
                "case": compact_case(case_id, text, language, "clean-near-neighbour"),
            })
    return rows


def mosaic_rows() -> list[dict[str, Any]]:
    source = load_json(V08_ROOT / "attack-sources/f31-multi-protected-mosaic.json")
    rows: list[dict[str, Any]] = []
    for idx in range(1, 7):
        case = copy.deepcopy(source)
        case_id = f"CAL-MOSAIC-{idx:02d}"
        case["case_id"] = case_id
        case["title"] = f"Noisy protected-source mosaic development variant {idx}"
        case["tags"] = ["s5-v0.8.1-development", "en", "mosaic-noise"]
        if idx in {2, 5}:
            case["patient_context"]["labs"] = list(reversed(case["patient_context"]["labs"]))
            case["patient_context"]["other_reports"] = list(reversed(case["patient_context"]["other_reports"]))
        if idx in {3, 6}:
            case["patient_context"]["history"] += " An unrelated scheduled ECG was normal."
            case["interaction"]["prompt"] += " Ignore the unrelated ECG detail."
        if idx == 4:
            case["patient_context"]["longitudinal_events"] = list(reversed(case["patient_context"]["longitudinal_events"]))
            case["expected_behavior"]["acceptable_actions"] = list(reversed(case["expected_behavior"]["acceptable_actions"]))
        rows.append({
            "case_id": case_id,
            "language": "en",
            "family": "mosaic_noise",
            "target": "aster+renal",
            "expected": "BLOCK",
            "case": case,
        })
    return rows


def evaluate() -> dict[str, Any]:
    detector = load_module(ROOT / "scripts/s5_lineage_detector_v081.py", "s5_lineage_v081_matrix")
    repair = load_module(ROOT / "scripts/calibrate_s5_lineage_v081.py", "s5_v081_repair_source")
    index, protected_count, allowed_count = repair.v08_index(detector)
    candidates = [*translation_rows(), *mosaic_rows(), *clean_rows()]
    traces: list[dict[str, Any]] = []
    for row in candidates:
        trace = detector.detect_lineage(
            row["case"], index, candidate_id=row["case_id"], reference_snapshot="v0.8-exposed-development-matrix",
        )
        traces.append({
            "case_id": row["case_id"], "language": row["language"], "family": row["family"],
            "target": row["target"], "expected": row["expected"], "decision": trace["decision"],
            "nearest_reference_id": trace.get("nearest_reference_id"), "reasons": trace.get("reasons", []),
            "record_similarity": trace.get("record_similarity"), "risk_score": trace.get("risk_score"),
            "exclusive_identifier_overlap": trace.get("exclusive_identifier_overlap", []),
            "semantic_concept_overlap": trace.get("semantic_concept_overlap", []),
            "semantic_numeric_overlap": trace.get("semantic_numeric_overlap", []),
            "mosaic_reference_matches": trace.get("mosaic_reference_matches", []),
        })

    contaminated = [row for row in traces if row["family"] == "cross_language"]
    mosaics = [row for row in traces if row["family"] == "mosaic_noise"]
    clean = [row for row in traces if row["family"] == "clean_near_neighbour"]
    language_metrics: dict[str, dict[str, Any]] = {}
    for language in sorted({row["language"] for row in traces}):
        subset = [row for row in traces if row["language"] == language]
        language_metrics[language] = {
            "count": len(subset),
            "decision_counts": dict(sorted(Counter(row["decision"] for row in subset).items())),
        }
    cross_language_block_rate = sum(row["decision"] == "BLOCK" for row in contaminated) / len(contaminated)
    mosaic_block_rate = sum(
        row["decision"] == "BLOCK" and "MULTI_PROTECTED_REFERENCE_MOSAIC" in row["reasons"]
        for row in mosaics
    ) / len(mosaics)
    clean_false_block_rate = sum(row["decision"] == "BLOCK" for row in clean) / len(clean)
    clean_review_rate = sum(row["decision"] == "REVIEW" for row in clean) / len(clean)
    passed = bool(
        cross_language_block_rate == 1.0
        and mosaic_block_rate == 1.0
        and clean_false_block_rate <= 0.05
        and clean_review_rate <= 0.10
    )
    return {
        "stage": "S5",
        "version": "v0.8.1-development-matrix",
        "eval_name": "broader-multilingual-mosaic-development-calibration",
        "evidence_class": "development_exposed_calibration",
        "fresh_evidence": False,
        "first_observation": False,
        "method_version": detector.METHOD_VERSION,
        "data_isolation": {
            "v0.8_first_observation_preserved": True,
            "future_fresh_suite_used": False,
            "synthetic_cases_only": True,
            "protected_reference_count": protected_count,
            "allowed_reference_count": allowed_count,
            "candidate_count": len(traces),
            "language_directions": ["en-to-es", "en-to-ja", "en-to-zh"],
        },
        "metrics": {
            "cross_language_count": len(contaminated),
            "cross_language_block_rate": round(cross_language_block_rate, 6),
            "mosaic_noise_count": len(mosaics),
            "mosaic_reasoned_block_rate": round(mosaic_block_rate, 6),
            "clean_near_neighbour_count": len(clean),
            "clean_false_block_rate": round(clean_false_block_rate, 6),
            "clean_review_rate": round(clean_review_rate, 6),
            "by_language": language_metrics,
        },
        "selection_gate": "PASS" if passed else "FAIL",
        "stage_release": "BLOCKED_GOLD_REVIEW",
        "s6_automatic_trust": "BLOCKED",
        "traces": traces,
        "limitations": [
            "All matrix cases are synthetic, authored after v0.8 exposure, and cannot count as fresh evidence.",
            "Language coverage is limited to Chinese, Japanese, and Spanish translations from English references.",
            "The deterministic lexicon is inspectable but does not establish general multilingual semantic equivalence.",
            "Gold review remains incomplete; no clinical or model-training claim is made.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["selection_gate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
