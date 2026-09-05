#!/usr/bin/env python3
"""Run S2 live retrieval checks against authoritative public sources.

This script separates external infrastructure failures (network/HTTP/parse)
from semantic retrieval failures. It uses only Python's standard library so it
can run in GitHub Actions without extra dependencies.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

USER_AGENT = "GroundSignal-Medical-S2-Eval/0.2 (research evaluation; contact via repository)"


def get_json(url: str, timeout: int = 20):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body), getattr(resp, "status", 200)


def run_dailymed(test):
    q = test["query"]
    params = {"drug_name": q["drug_name"], "name_type": q.get("name_type", "both"), "pagesize": 100, "page": 1}
    url = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?" + urlencode(params)
    data, status = get_json(url)
    rows = data.get("data", [])
    return {
        "url": url,
        "http_status": status,
        "result_count": len(rows),
        "records": [
            {"title": r.get("title"), "setid": r.get("setid"), "spl_version": r.get("spl_version"), "published_date": r.get("published_date")}
            for r in rows[:20]
        ],
    }


def run_drugsfda(test):
    app = test["query"]["application_number"]
    params = {"search": f'application_number:"{app}"', "limit": 10}
    url = "https://api.fda.gov/drug/drugsfda.json?" + urlencode(params)
    data, status = get_json(url)
    rows = data.get("results", [])
    return {
        "url": url,
        "http_status": status,
        "result_count": len(rows),
        "application_numbers": [r.get("application_number") for r in rows],
    }


def run_clinicaltrials(test):
    nct = test["query"]["nct_id"]
    url = f"https://clinicaltrials.gov/api/v2/studies/{quote(nct)}"
    data, status = get_json(url)
    protocol = data.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    status_mod = protocol.get("statusModule", {})
    return {
        "url": url,
        "http_status": status,
        "nct_id": ident.get("nctId"),
        "brief_title": ident.get("briefTitle"),
        "overall_status": status_mod.get("overallStatus"),
    }


def run_rxnorm(test):
    name = test["query"]["name"]
    params = {"name": name, "search": 2}
    url = "https://rxnav.nlm.nih.gov/REST/rxcui.json?" + urlencode(params)
    data, status = get_json(url)
    ids = (data.get("idGroup") or {}).get("rxnormId") or []
    return {"url": url, "http_status": status, "rxnorm_ids": ids}


def run_pubmed(test):
    q = test["query"]
    params = {"db": "pubmed", "term": q["term"], "retmode": "json", "retmax": q.get("retmax", 5)}
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(params)
    data, status = get_json(url)
    ids = (data.get("esearchresult") or {}).get("idlist") or []
    return {"url": url, "http_status": status, "pmids": ids}


def run_faers(test):
    generic = test["query"]["generic_name"]
    params = {"search": f'patient.drug.openfda.generic_name:"{generic}"', "limit": 1}
    url = "https://api.fda.gov/drug/event.json?" + urlencode(params)
    data, status = get_json(url)
    total = (((data.get("meta") or {}).get("results") or {}).get("total"))
    return {"url": url, "http_status": status, "total": total}


ADAPTERS = {
    "dailymed_spls": run_dailymed,
    "openfda_drugsfda": run_drugsfda,
    "clinicaltrials_study": run_clinicaltrials,
    "rxnorm_rxcui": run_rxnorm,
    "pubmed_esearch": run_pubmed,
    "openfda_faers": run_faers,
}


def run_one(test, timeout_retries=1):
    adapter = test["adapter"]
    fn = ADAPTERS[adapter]
    started = time.time()
    try:
        result = fn(test)
        return {
            "test_id": test["test_id"],
            "source_id": test["source_id"],
            "adapter": adapter,
            "execution_status": "OK",
            "latency_ms": round((time.time() - started) * 1000, 1),
            "result": result,
        }
    except HTTPError as exc:
        return {
            "test_id": test["test_id"], "source_id": test["source_id"], "adapter": adapter,
            "execution_status": "HTTP_ERROR", "http_status": exc.code,
            "error": str(exc), "latency_ms": round((time.time() - started) * 1000, 1),
        }
    except (URLError, socket.timeout, TimeoutError) as exc:
        return {
            "test_id": test["test_id"], "source_id": test["source_id"], "adapter": adapter,
            "execution_status": "NETWORK_ERROR", "error": str(exc),
            "latency_ms": round((time.time() - started) * 1000, 1),
        }
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError, ValueError) as exc:
        return {
            "test_id": test["test_id"], "source_id": test["source_id"], "adapter": adapter,
            "execution_status": "PARSE_ERROR", "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": round((time.time() - started) * 1000, 1),
        }
    except Exception as exc:  # keep unknown failures observable rather than crashing the batch
        return {
            "test_id": test["test_id"], "source_id": test["source_id"], "adapter": adapter,
            "execution_status": "UNEXPECTED_ERROR", "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": round((time.time() - started) * 1000, 1),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="medical/stage-evals/S2/live-retrieval-v0.2.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    rows = []
    for test in suite["tests"]:
        row = run_one(test)
        rows.append(row)
        print(test["test_id"], row["execution_status"], row.get("latency_ms"))

    payload = {
        "benchmark_id": suite["benchmark_id"],
        "runner_version": "s2-live-retrieval-v0.2.0",
        "results": rows,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} live retrieval results to {out}")


if __name__ == "__main__":
    main()
