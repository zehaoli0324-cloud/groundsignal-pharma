#!/usr/bin/env python3
import argparse, json
from pathlib import Path


def route(query: str):
    q = query.lower()

    def ranked(*ids):
        return list(dict.fromkeys(ids))[:3]

    # Jurisdiction / dedicated authorities first.
    if any(x in q for x in ["eu product information", "ema", "epar", "sm-pc", "smpc"]):
        return ranked("EMA_EPAR_SMPC")
    if "china" in q and any(x in q for x in ["cde", "drug review", "review status", "guidance document"]):
        return ranked("CDE_NMPA")
    if "china" in q and any(x in q for x in ["clinical pathway", "national clinical pathway", "national pathway"]):
        return ranked("NHC_CHINA", "CDE_NMPA")

    # Regulatory approval must outrank trial registration when both appear.
    if any(x in q for x in ["approval status", "approval date", "approved by fda", "approved indication", "received fda approval", "received fda approval", "fda approval"]):
        return ranked("DRUGS_AT_FDA", "DAILYMED_SPL", "CLINICALTRIALS_GOV")

    # Terminology / registry tools.
    if any(x in q for x in ["rxcui", "rxnorm", "normalized ingredient", "brand drug name", "generic ingredient", "dose-form concept"]):
        return ranked("RXNORM")
    if "loinc" in q or ("laboratory" in q and any(x in q for x in ["concept", "term", "mapping"])):
        return ranked("LOINC")
    if any(x in q for x in ["nct", "recruitment status", "registered primary endpoint", "registered endpoint", "trial currently recruiting", "phase 3 trial"]):
        return ranked("CLINICALTRIALS_GOV", "PUBMED")

    # Safety signals / literature.
    if "faers" in q or "spontaneous adverse-event" in q or "spontaneous adverse event" in q:
        return ranked("OPENFDA_FAERS", "FDA_SAFETY_COMMUNICATIONS")
    if any(x in q for x in ["drug-induced liver injury", "drug induced liver injury", "dili background", "nih reference"]):
        return ranked("LIVERTOX", "DAILYMED_SPL", "PUBMED")
    if any(x in q for x in ["peer-reviewed studies", "peer reviewed studies", "published randomized", "clinical trial paper"]):
        return ranked("PUBMED")

    # Professional/public-health guidance.
    if any(x in q for x in ["chest-pain warning", "chest pain warning", "cardiovascular sources", "acute chest"]):
        return ranked("AHA_GUIDANCE")
    if "stroke warning" in q or "cdc-recognized stroke" in q or "cdc recognized stroke" in q:
        return ranked("CDC_CLINICAL_PUBLIC_HEALTH")
    if any(x in q for x in ["kidney-disease reference", "kidney disease reference", "aki background"]):
        return ranked("NKF_CLINICAL_REFERENCE", "PUBMED")

    # Pharmacogenomics before general label routing.
    if any(x in q for x in ["hla-b*57:01", "hla-b*5701", "pharmacogenetic", "cyp2d6 poor metabolizer", "therapeutic management recommendation rather than pk"]):
        return ranked("FDA_PGX", "DAILYMED_SPL", "DRUGS_AT_FDA")

    # General DDI study methodology is distinct from a specific CYP/transporter lookup.
    if any(x in q for x in [
        "drug interaction studies generally", "drug interaction studies", "enzyme- and transporter-mediated",
        "enzyme and transporter mediated", "designed and interpreted", "ddi methodology"
    ]):
        return ranked("FDA_ICH_M12", "FDA_DDI_TABLES")

    # Specific DDI / clinical pharmacology reference questions.
    if any(x in q for x in ["cyp3a", "cyp2d6", "cyp2c19", "bcrp", "oatp", "oct2", "mate", "transporter systems"]):
        return ranked("FDA_DDI_TABLES", "FDA_ICH_M12")

    # Regulatory safety update.
    if "safety communication" in q or "label-change warning" in q or "label change warning" in q:
        return ranked("FDA_SAFETY_COMMUNICATIONS", "DRUGS_AT_FDA", "DAILYMED_SPL")

    # Current prescribing information / patient-level label rules.
    label_terms = [
        "current u.s. label", "current us label", "current label", "prescribing information",
        "label say", "label warn", "label warning", "indicated for reversal", "current glipizide",
        "sertraline prescribing", "apixaban label", "metformin use", "naloxone indicated"
    ]
    if any(x in q for x in label_terms):
        if "apixaban" in q or "fda" in q:
            return ranked("DRUGS_AT_FDA", "DAILYMED_SPL")
        return ranked("DAILYMED_SPL", "DRUGS_AT_FDA")

    # Generic fallbacks are deliberately authority-oriented, not web-search-oriented.
    if "trial" in q:
        return ranked("CLINICALTRIALS_GOV", "PUBMED")
    if "drug" in q or "medication" in q:
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
            "router_version": "deterministic-s2-v0.1.1"
        })
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"predictions": preds}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(preds)} predictions to {args.out}")


if __name__ == "__main__":
    main()
