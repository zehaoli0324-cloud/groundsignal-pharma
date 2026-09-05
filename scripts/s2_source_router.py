#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

ROUTER_VERSION = "deterministic-s2-v0.2.0"


def has_any(q, terms):
    return any(t in q for t in terms)


def route(query: str):
    q = query.lower().strip()

    def ranked(*ids):
        return list(dict.fromkeys(ids))[:3]

    # Multi-source information needs must be decomposed before single-source fallbacks.
    approval_signal_lit = (
        has_any(q, ["faers", "不良反应", "安全信号", "adverse event", "safety signal"])
        and has_any(q, ["批准", "获批", "approval", "approved indication"])
        and has_any(q, ["论文", "文献", "clinical paper", "publication", "pubmed"])
    )
    if approval_signal_lit:
        return ranked("DRUGS_AT_FDA", "OPENFDA_FAERS", "PUBMED")

    # Jurisdiction-specific authorities.
    if has_any(q, ["eu product information", "ema", "epar", "sm-pc", "smpc", "欧洲", "欧盟"]):
        return ranked("EMA_EPAR_SMPC")
    if has_any(q, ["中国", "china", "cde", "nmpa"]) and has_any(q, ["受理", "审评", "review", "获批", "批准", "监管", "guidance"]):
        return ranked("CDE_NMPA")
    if has_any(q, ["中国", "china", "国家层面", "国家"] ) and has_any(q, ["临床路径", "clinical pathway", "national pathway"]):
        return ranked("NHC_CHINA", "CDE_NMPA")

    # Regulatory approval outranks trial registration when approval status is the question.
    if has_any(q, [
        "approval status", "approval date", "approved by fda", "approved indication", "received fda approval",
        "fda approval", "fda 批准", "获 fda 批准", "获批", "已经批准", "批准日期", "批准了"
    ]):
        return ranked("DRUGS_AT_FDA", "DAILYMED_SPL", "CLINICALTRIALS_GOV")

    # Terminology / identity normalization.
    if has_any(q, [
        "rxcui", "rxnorm", "normalized ingredient", "brand drug name", "generic ingredient", "dose-form concept",
        "标准化成统一药物", "统一药物概念", "药物概念", "品牌名", "通用名", "成分标准化"
    ]):
        return ranked("RXNORM")
    if has_any(q, ["loinc", "lab concept", "laboratory test identity", "标准 lab", "标准化验", "化验项目", "实验室项目"]) or (
        has_any(q, ["laboratory", "lab test", "化验", "实验室"]) and has_any(q, ["concept", "term", "mapping", "标准", "映射"])
    ):
        return ranked("LOINC")

    # Trial registry metadata.
    if has_any(q, [
        "nct", "recruitment status", "registered primary endpoint", "registered endpoint", "trial currently recruiting",
        "试验注册", "招募", "主要终点", "注册终点", "clinicaltrials.gov"
    ]):
        return ranked("CLINICALTRIALS_GOV", "PUBMED")

    # Safety signal discovery vs causal/clinical truth.
    if has_any(q, ["faers", "spontaneous adverse-event", "spontaneous adverse event", "自发报告", "安全信号"]):
        return ranked("OPENFDA_FAERS", "FDA_SAFETY_COMMUNICATIONS")
    if has_any(q, ["drug-induced liver injury", "drug induced liver injury", "dili background", "nih reference", "dili", "药物性肝损伤"]):
        return ranked("LIVERTOX", "DAILYMED_SPL", "PUBMED")

    # Literature discovery must beat generic trial fallback when peer review is explicitly requested.
    if has_any(q, [
        "peer-reviewed", "peer reviewed", "published randomized", "randomized-trial publications", "clinical trial paper",
        "同行评议", "随机试验论文", "临床论文", "pubmed", "论文", "文献"
    ]):
        return ranked("PUBMED")

    # Professional / public-health guidance.
    if has_any(q, ["american heart association", "aha", "美国心脏协会", "胸痛", "chest pain", "acute chest"]):
        return ranked("AHA_GUIDANCE")
    if has_any(q, ["cdc", "stroke warning", "卒中", "中风", "一侧无力", "说话不清"]):
        return ranked("CDC_CLINICAL_PUBLIC_HEALTH")
    if has_any(q, ["national kidney foundation", "nkf", "肾脏专科", "aki background", "aki 常见病因", "kidney-disease reference", "kidney disease reference"]):
        return ranked("NKF_CLINICAL_REFERENCE", "PUBMED")

    # Product-label structure / special-population regulatory guidance.
    if has_any(q, ["pregnancy and lactation labeling", "pllr", "pregnancy category", "妊娠分级", "妊娠标签", "哺乳标签"]):
        return ranked("FDA_PLLR")
    if has_any(q, ["qtc information", "qtc labeling", "qt labeling", "qt 间期", "qtc 标签"]):
        return ranked("FDA_QTC_LABELING_2025")
    if has_any(q, ["renal impairment", "肾功能不全", "renal pk", "肾功能药代"]) and has_any(q, ["guidance", "方法学", "study", "研究", "dose-development", "剂量建议"]):
        return ranked("FDA_RENAL_IMPAIRMENT_GUIDANCE")
    if has_any(q, ["hepatic impairment", "肝功能不全", "hepatic pk", "hepatic function"]) and has_any(q, ["guidance", "draft", "study design", "方法学", "研究"]):
        return ranked("FDA_HEPATIC_IMPAIRMENT_2026_DRAFT")

    # Pharmacogenomics before general label routing.
    if has_any(q, [
        "hla-b*57:01", "hla-b*5701", "pharmacogenetic", "pharmacogenomic", "cyp2d6 poor metabolizer",
        "药物基因组", "基因型", "poor metabolizer"
    ]):
        return ranked("FDA_PGX", "DAILYMED_SPL", "DRUGS_AT_FDA")

    # Drug-drug interaction methodology vs specific lookup.
    if has_any(q, [
        "drug interaction studies", "enzyme- and transporter-mediated", "enzyme and transporter mediated",
        "ddi methodology", "ddi study", "ddi 方法", "相互作用研究", "设计和解释"
    ]):
        return ranked("FDA_ICH_M12", "FDA_DDI_TABLES")
    if has_any(q, ["cyp3a", "cyp2d6", "cyp2c19", "bcrp", "oatp", "oct2", "mate", "transporter", "转运体"]):
        return ranked("FDA_DDI_TABLES", "FDA_ICH_M12")

    # Regulatory safety updates.
    if has_any(q, ["safety communication", "label-change warning", "label change warning", "安全警告", "标签变更", "监管安全更新"]):
        return ranked("FDA_SAFETY_COMMUNICATIONS", "DRUGS_AT_FDA", "DAILYMED_SPL")

    # Current prescribing information / patient-level management truth.
    label_terms = [
        "current u.s. label", "current us label", "current label", "prescribing information", "label say", "label warn",
        "label warning", "indicated for reversal", "sertraline prescribing", "apixaban label", "metformin use", "naloxone indicated",
        "最新美国说明书", "最新版原始标签", "最新官方来源", "最新说明书", "说明书", "原始标签", "处方信息"
    ]
    brand_or_label_drugs = ["eliquis", "zoloft", "metformin", "二甲双胍", "apixaban", "sertraline", "glipizide", "naloxone"]
    if has_any(q, label_terms) or (has_any(q, brand_or_label_drugs) and has_any(q, ["风险", "warning", "警告", "eGFR".lower(), "出血"])):
        if has_any(q, ["eliquis", "apixaban", "fda"]):
            return ranked("DRUGS_AT_FDA", "DAILYMED_SPL")
        return ranked("DAILYMED_SPL", "DRUGS_AT_FDA")

    # Deliberately conservative fallbacks.
    if "trial" in q or "试验" in q:
        return ranked("CLINICALTRIALS_GOV", "PUBMED")
    if has_any(q, ["drug", "medication", "药", "用药"]):
        return ranked("DAILYMED_SPL", "DRUGS_AT_FDA", "RXNORM")
    return ranked("PUBMED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    preds = []
    for row in data["queries"]:
        preds.append({
            "query_id": row["query_id"],
            "ranked_source_ids": route(row["query"]),
            "router_version": ROUTER_VERSION
        })
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"predictions": preds}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(preds)} predictions to {args.out}")


if __name__ == "__main__":
    main()
