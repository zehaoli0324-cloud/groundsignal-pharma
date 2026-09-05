#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "GroundSignal-Medical-S2-Eval/0.3 (research evaluation; contact via repository)"
NS = {"h": "urn:hl7-org:v3"}


def request_text(url: str, accept: str | None = None, timeout: int = 20):
    # DailyMed v2 chooses representation from the URL suffix (.json/.xml).
    # Sending a narrow Accept header caused HTTP 406 on history/XML endpoints,
    # so only advertise */* unless a future adapter proves stricter negotiation is required.
    headers = {"User-Agent": USER_AGENT, "Accept": accept or "*/*"}
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8"), getattr(resp, "status", 200)


def request_json(url: str):
    text, status = request_text(url)
    return json.loads(text), status


def normalize(text: str):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def parse_date(s: str):
    return datetime.strptime(s, "%b %d, %Y")


def latest_history_entry(history: list[dict]):
    return max(history, key=lambda x: (parse_date(x["published_date"]), int(x.get("spl_version", 0))))


def section_rows(xml_text: str):
    root = ET.fromstring(xml_text)
    version_el = root.find(".//h:versionNumber", NS)
    xml_version = version_el.get("value") if version_el is not None else None
    rows = []
    for sec in root.findall(".//h:section", NS):
        title_el = sec.find("h:title", NS)
        text_el = sec.find("h:text", NS)
        title = "" if title_el is None else " ".join(title_el.itertext())
        text = "" if text_el is None else " ".join(text_el.itertext())
        if title or text:
            rows.append({"title": normalize(title), "text": normalize(text)})
    return xml_version, rows


def score_section(row: dict, query_terms: list[str], title_terms: list[str]):
    title = row["title"]
    text = row["text"]
    score = 0.0
    for term in query_terms:
        if term in title:
            score += 4.0
        elif term in text:
            score += 1.0
    for term in title_terms:
        if term in title:
            score += 6.0
    return score


def run_test(test: dict):
    setid = test["setid"]
    history_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}/history.json"
    xml_url = f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
    started = time.time()
    history_doc, history_status = request_json(history_url)
    xml_text, xml_status = request_text(xml_url)
    history = ((history_doc.get("data") or {}).get("history") or [])
    latest = latest_history_entry(history) if history else None
    xml_version, sections = section_rows(xml_text)

    query_terms = [normalize(x) for x in re.findall(r"[A-Za-z0-9-]+", test["critical_query"]) if len(x) > 1]
    title_terms = [normalize(x) for x in test.get("acceptable_section_title_contains", [])]
    ranked = sorted(
        ({**row, "score": score_section(row, query_terms, title_terms)} for row in sections),
        key=lambda r: (-r["score"], r["title"]),
    )
    top = [
        {
            "rank": i + 1,
            "title": row["title"],
            "score": row["score"],
            "text_preview": row["text"][:700],
        }
        for i, row in enumerate(ranked[:5])
    ]
    return {
        "test_id": test["test_id"],
        "drug": test["drug"],
        "setid": setid,
        "execution_status": "OK",
        "history_http_status": history_status,
        "xml_http_status": xml_status,
        "latest_history_entry": latest,
        "xml_version": xml_version,
        "version_consistent": bool(latest and xml_version and str(latest.get("spl_version")) == str(xml_version)),
        "top_sections": top,
        "latency_ms": round((time.time() - started) * 1000, 1),
    }


def safe_run(test: dict):
    started = time.time()
    try:
        return run_test(test)
    except HTTPError as exc:
        return {"test_id": test["test_id"], "execution_status": "HTTP_ERROR", "http_status": exc.code, "error": str(exc), "latency_ms": round((time.time() - started) * 1000, 1)}
    except (URLError, socket.timeout, TimeoutError) as exc:
        return {"test_id": test["test_id"], "execution_status": "NETWORK_ERROR", "error": str(exc), "latency_ms": round((time.time() - started) * 1000, 1)}
    except (json.JSONDecodeError, UnicodeDecodeError, ET.ParseError, KeyError, TypeError, ValueError) as exc:
        return {"test_id": test["test_id"], "execution_status": "PARSE_ERROR", "error": f"{type(exc).__name__}: {exc}", "latency_ms": round((time.time() - started) * 1000, 1)}
    except Exception as exc:
        return {"test_id": test["test_id"], "execution_status": "UNEXPECTED_ERROR", "error": f"{type(exc).__name__}: {exc}", "latency_ms": round((time.time() - started) * 1000, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="medical/stage-evals/S2/dailymed-truth-retrieval-v0.3.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    rows = []
    for test in suite["tests"]:
        row = safe_run(test)
        rows.append(row)
        print(test["test_id"], row["execution_status"], row.get("http_status"), row.get("version_consistent"), row.get("latency_ms"), row.get("error"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"benchmark_id": suite["benchmark_id"], "runner_version": "s2-dailymed-truth-v0.3.1", "results": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
