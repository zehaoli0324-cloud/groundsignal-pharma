"""Text-free, patient-speech-only similarity cues for candidate human review.

This is a lexical screen of the supplied candidates, not a semantic duplicate
detector, a patient identity linker, or evidence of independent test data.
"""

from itertools import combinations
import math
import unicodedata


def _normalise(content):
    normalised = unicodedata.normalize("NFKC", content).casefold()
    return "".join(character for character in normalised if not character.isspace())


def _patient_features(record):
    if not isinstance(record, dict):
        raise ValueError("each candidate must be an object")
    candidate_id = record.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError("candidate_id must be a nonempty string")
    turns = record.get("turns")
    if not isinstance(turns, list):
        raise ValueError("candidate turns must be a list")
    patient_turns = []
    for turn in turns:
        if not isinstance(turn, dict) or turn.get("role") not in ("patient", "doctor"):
            raise ValueError("candidate turn role must be patient or doctor")
        if not isinstance(turn.get("content"), str):
            raise ValueError("candidate turn content must be a string")
        if turn["role"] == "patient":
            content = _normalise(turn["content"])
            if content:
                patient_turns.append(content)
    grams = set()
    for content in patient_turns:
        if len(content) < 3:
            grams.add(content)
        else:
            grams.update(content[index:index + 3] for index in range(len(content) - 2))
    return candidate_id, tuple(patient_turns), grams


def audit_candidate_similarity(records, threshold=0.85):
    """Return candidate-pair review cues without including patient/doctor text.

    Character trigrams are formed inside each normalised patient utterance;
    their set union ignores utterance order, repetitions and doctor turns.
    Jaccard similarity is |intersection| / |union|. For an utterance shorter
    than three characters, its complete text is its single feature. Exact
    means the ordered, nonempty normalised patient utterances are identical;
    doctor text is never part of that designation.

    Empty patient speech is missing data, never a perfect empty-set match.
    Connected components are explicitly transitive suggestions: not every
    pair in a component necessarily exceeds the threshold. A threshold of
    zero is accepted and includes every eligible pair, even zero overlap.
    """
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold) or not 0 <= threshold <= 1):
        raise ValueError("threshold must be a finite number between zero and one")
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    features = [_patient_features(record) for record in records]
    identifiers = [item[0] for item in features]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("candidate_id values must be unique")
    # Stable output and grouping do not depend on input record order.
    features.sort(key=lambda item: item[0])
    eligible = [item for item in features if item[2]]
    missing = [item[0] for item in features if not item[2]]
    neighbours = {item[0]: set() for item in eligible}
    pairs = []
    for left, right in combinations(eligible, 2):
        similarity = len(left[2] & right[2]) / len(left[2] | right[2])
        if similarity >= threshold:
            pairs.append({
                "candidate_a": left[0], "candidate_b": right[0],
                "jaccard": similarity,
                "match_type": "exact" if left[1] == right[1] else "near",
            })
            neighbours[left[0]].add(right[0])
            neighbours[right[0]].add(left[0])
    groups, visited = [], set()
    for candidate_id in sorted(neighbours):
        if candidate_id in visited or not neighbours[candidate_id]:
            continue
        pending, component = [candidate_id], set()
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(neighbours[current] - component)
        visited.update(component)
        direct_pairs = sum(len(neighbours[item] & component) for item in component) // 2
        possible_pairs = len(component) * (len(component) - 1) // 2
        groups.append({
            "group_id": f"SG{len(groups) + 1:03d}",
            "candidate_ids": sorted(component),
            "relation": "transitive_similarity_component",
            "direct_pair_count": direct_pairs,
            "possible_pair_count": possible_pairs,
            "pairwise_complete": direct_pairs == possible_pairs,
        })
    possible_pair_count = len(features) * (len(features) - 1) // 2
    compared_pair_count = len(eligible) * (len(eligible) - 1) // 2
    return {
        "schema_version": "candidate-similarity/v0.1",
        "scope": "provided_candidates_patient_speech_only",
        "method": {
            "normalisation": "Unicode NFKC; casefold; remove Unicode whitespace",
            "features": "set union of within-patient-turn character trigrams; short-turn whole-text fallback",
            "similarity": "Jaccard: intersection size divided by union size",
            "order": "trigram character order retained; turn order and repeated features ignored for Jaccard",
            "exact_match": "same ordered nonempty normalised patient turns; doctor text excluded",
            "missing_data": "no nonempty normalised patient speech: omit from comparisons and flag",
        },
        "threshold": threshold,
        "threshold_status": "uncalibrated_review_cue",
        "candidate_count": len(features),
        "eligible_candidate_count": len(eligible),
        "possible_pair_count": possible_pair_count,
        "compared_pair_count": compared_pair_count,
        "skipped_pair_count": possible_pair_count - compared_pair_count,
        "missing_patient_candidate_ids": missing,
        "near_duplicate_pairs": pairs,
        "exact_pair_count": sum(pair["match_type"] == "exact" for pair in pairs),
        "near_pair_count": sum(pair["match_type"] == "near" for pair in pairs),
        "source_group_suggestions": groups,
        "interpretation": [
            "Lexical similarity is a human review cue, not semantic equivalence, patient identity, or clinical truth.",
            "Transitive groups may include pairs below threshold; group membership is not a proven shared source.",
            "Scope is only the supplied candidates, not the full source corpus or other datasets.",
            "No detected match does not establish independent held-out data or absence from model training.",
            "Threshold is uncalibrated; candidate text and feature text are not included in this audit.",
        ],
    }
