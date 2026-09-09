"""Small, inspectable BM25 retrieval baseline with explicit eligibility filters.

BM25 is a term-frequency ranking method with inverse-document-frequency weights
and document-length normalization. Chinese runs use overlapping character bigrams
(single-character runs use unigrams); Latin words and numbers are case-folded
tokens. This is lexical retrieval, not a semantic or clinical relevance model.
Dates and patient-population scope are hard filters before ranking, making stale
or inapplicable evidence distinguishable from a ranking failure in experiments.
"""

from collections import Counter
from copy import deepcopy
from datetime import date
import math
import re


_TOKEN_RUNS = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+|[a-z0-9]+(?:['’-][a-z0-9]+)*")
_CJK = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff]+$")


def _tokens(text: str) -> list[str]:
    terms: list[str] = []
    for run in _TOKEN_RUNS.findall(text.casefold()):
        if _CJK.fullmatch(run) and len(run) > 1:
            terms.extend(run[index:index + 2] for index in range(len(run) - 1))
        else:
            terms.append(run)
    return terms


def _date(value: object, field: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must be an ISO date YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date YYYY-MM-DD") from exc


def _populations(value: object) -> set[str] | None:
    """Missing scope is unspecified; 'all' is the explicit universal scope."""
    if value is None:
        return None
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list) or not items:
        raise ValueError("population must be a nonempty string or string list")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError("population labels must be nonempty strings")
    return {item.strip().casefold() for item in items}


def rank_evidence(
    query: str,
    passages: list[dict],
    top_k: int = 3,
    as_of: str | None = None,
    population: str | None = None,
) -> list[dict]:
    """Return eligible lexical matches as copied passages plus positive ``score``.

    Eligibility dates are inclusive. Supplying ``as_of`` filters dates; omitting
    it intentionally performs no temporal filtering (never reads today's date).
    Missing date bounds mean unbounded validity, not verified currency. When a
    population is requested, only an exact label or explicit ``'all'`` is eligible;
    passages with unspecified scope are excluded. With no population requested,
    no scope filter is applied. No clinical ontology is inferred from labels.

    Invalid records, duplicate IDs, reversed intervals, or bad filter inputs raise
    ``ValueError`` rather than silently losing evidence. Empty queries and no
    overlapping terms return ``[]``. Ties use the passage ID in ascending order,
    so input order cannot influence a paired experiment. Scores use k1=1.5, b=.75
    and corpus statistics computed over the eligible corpus.
    """
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    if not isinstance(passages, list):
        raise ValueError("passages must be a list")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 0:
        raise ValueError("top_k must be a nonnegative integer")
    cutoff = _date(as_of, "as_of")
    if population is not None and (not isinstance(population, str) or not population.strip()):
        raise ValueError("population filter must be a nonempty string")
    requested = population.strip().casefold() if population is not None else None

    eligible: list[dict] = []
    seen_ids: set[str] = set()
    for passage in passages:
        if not isinstance(passage, dict):
            raise ValueError("each passage must be a dictionary")
        passage_id, text = passage.get("id"), passage.get("text")
        if not isinstance(passage_id, str) or not passage_id.strip():
            raise ValueError("each passage requires a nonempty string id")
        if passage_id in seen_ids:
            raise ValueError(f"duplicate passage id: {passage_id}")
        seen_ids.add(passage_id)
        if not isinstance(text, str):
            raise ValueError("each passage requires string text")
        start = _date(passage.get("valid_from"), "valid_from")
        end = _date(passage.get("valid_to"), "valid_to")
        if start is not None and end is not None and start > end:
            raise ValueError("valid_from must not be after valid_to")
        scopes = _populations(passage.get("population"))
        if cutoff is not None and ((start is not None and cutoff < start)
                                   or (end is not None and cutoff > end)):
            continue
        if requested is not None and (scopes is None or (requested not in scopes and "all" not in scopes)):
            continue
        eligible.append(passage)

    query_terms = set(_tokens(query))
    if not query_terms or not eligible or top_k == 0:
        return []
    counts = [Counter(_tokens(passage["text"])) for passage in eligible]
    lengths = [sum(terms.values()) for terms in counts]
    average_length = sum(lengths) / len(lengths)
    if average_length == 0:
        return []
    document_frequencies = Counter(term for terms in counts for term in terms)
    n_documents = len(eligible)
    k1, b = 1.5, 0.75
    ranked: list[dict] = []
    for passage, terms, length in zip(eligible, counts, lengths):
        score = 0.0
        for term in sorted(query_terms):
            frequency = terms.get(term, 0)
            if frequency == 0:
                continue
            df = document_frequencies[term]
            inverse_frequency = math.log(1 + (n_documents - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * length / average_length)
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        if score > 0:
            result = deepcopy(passage)
            result["score"] = score
            ranked.append(result)
    ranked.sort(key=lambda result: (-result["score"], result["id"]))
    return ranked[:top_k]
