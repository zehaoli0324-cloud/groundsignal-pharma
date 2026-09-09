"""Two-rater agreement with independent quality, safety and opportunity records.

Linear weighted Cohen's kappa uses disagreement |a-b|/2 for ratings 0,1,2.
It describes annotation consistency, not clinical validity or rater expertise.
For v0.3, criteria are the primary units: a pooled kappa is diagnostic only.
Missing ratings and unassessed/not-applicable statuses never become zeroes.
"""

from collections import Counter
import re

from .contracts import require


REVIEW_VERSION = "patient-review/v0.3"
QUALITY_STATUSES = ("assessed", "unassessed", "not_applicable")
OPPORTUNITY_STATUSES = ("occurred", "not_reached", "not_applicable", "unassessed")


def _status_agreement(items, left_index, right_index, field, labels):
    """Count explicit statuses only; a missing reviewer row is a separate gap."""
    matrix = [[0] * len(labels) for _ in labels]
    missing, disagreements = [], []
    for item in items:
        left, right = left_index.get(item), right_index.get(item)
        if left is None or right is None:
            missing.append(item)
            continue
        a, b = left[field], right[field]
        matrix[labels.index(a)][labels.index(b)] += 1
        if a != b:
            disagreements.append(item)
    paired = len(items) - len(missing)
    return {
        "labels": list(labels), "confusion_matrix": matrix,
        "paired_items": paired, "total_items": len(items),
        "missing_reviewer_items": missing,
        "disagreement_items": disagreements,
        "exact_agreement": (paired - len(disagreements)) / paired if paired else None,
        "coverage": paired / len(items) if items else None,
        "denominator": "items with rows from both reviewers; unassessed is an explicit status",
    }


def _summarize(items, left_index, right_index, version):
    paired, incomplete, safety = [], [], []
    safety_missing, safety_disagreements, missing_rows = [], [], []
    for item in items:
        left, right = left_index.get(item), right_index.get(item)
        if left is None or right is None:
            missing_rows.append(item)
        if (left is not None and right is not None
                and left.get("serious_error") is not None and right.get("serious_error") is not None):
            safety.append((left["serious_error"], right["serious_error"]))
            if left["serious_error"] != right["serious_error"]:
                safety_disagreements.append(item)
        else:
            safety_missing.append(item)
        if (left is not None and right is not None
                and left.get("rating") is not None and right.get("rating") is not None):
            paired.append((left["rating"], right["rating"]))
        else:
            incomplete.append(item)
    n = len(paired)
    matrix = [[0] * 3 for _ in range(3)]
    for a, b in paired:
        matrix[a][b] += 1
    kappa, exact, observed, expected = None, None, None, None
    if n:
        a_counts, b_counts = Counter(a for a, _ in paired), Counter(b for _, b in paired)
        observed = sum(abs(a - b) / 2 for a, b in paired) / n
        expected = sum(abs(a - b) / 2 * a_counts[a] * b_counts[b] for a in range(3) for b in range(3)) / n ** 2
        kappa = 1 - observed / expected if expected else None
        exact = sum(a == b for a, b in paired) / n
    result = {
        "total_items": len(items), "paired_rated_items": n, "incomplete_items": incomplete,
        "rating_coverage": n / len(items) if items else None, "confusion_matrix_0_1_2": matrix,
        "exact_agreement": exact, "linear_weighted_cohen_kappa": kappa,
        "observed_disagreement": observed, "expected_disagreement": expected,
        "serious_error_paired_items": len(safety),
        "serious_error_disagreements": len(safety_disagreements),
        "serious_error_unknown_items": len(items) - len(safety),
    }
    if version == REVIEW_VERSION:
        safety_matrix = [[0] * 2 for _ in range(2)]
        for a, b in safety:
            safety_matrix[int(a)][int(b)] += 1
        result.update({
            "missing_reviewer_items": missing_rows,
            "quality_status_agreement": _status_agreement(
                items, left_index, right_index, "quality_status", QUALITY_STATUSES),
            "opportunity_status_agreement": _status_agreement(
                items, left_index, right_index, "opportunity_status", OPPORTUNITY_STATUSES),
            "serious_error_confusion_matrix_false_true": safety_matrix,
            "serious_error_disagreement_items": safety_disagreements,
            "serious_error_missing_label_items": safety_missing,
            "serious_error_exact_agreement": (
                (len(safety) - len(safety_disagreements)) / len(safety) if safety else None),
            "serious_error_coverage": len(safety) / len(items) if items else None,
            "denominators": {
                "ordinal": "both reviewers quality_status=assessed with a 0/1/2 rating",
                "safety": "both reviewers supplied serious_error, independently of quality rating",
                "coverage": "all distinct item_id values present in either reviewer input",
            },
        })
    return result


def rater_agreement(rows, reviewer_a, reviewer_b):
    require(reviewer_a != reviewer_b and all(isinstance(x, str) and x.strip() for x in (reviewer_a, reviewer_b)),
            "two distinct reviewer identities are required")
    require(isinstance(rows, list) and bool(rows), "ratings must be a nonempty list")
    index = {reviewer_a: {}, reviewer_b: {}}
    versions, review_versions, item_criteria = set(), set(), {}
    has_review_set = any(isinstance(row, dict) and "review_set_sha256" in row for row in rows)
    review_sets = set()
    for row in rows:
        require(isinstance(row, dict), "rating row must be an object")
        if has_review_set:
            review_set = row.get("review_set_sha256")
            require(isinstance(review_set, str) and re.fullmatch(r"[0-9a-fA-F]{64}", review_set),
                    "every row requires a valid review_set_sha256 when any row supplies it")
            review_sets.add(review_set.lower())
        reviewer = row.get("reviewer_id")
        require(reviewer in index, "unexpected reviewer: keep adjudication separate from initial ratings")
        item = row.get("item_id")
        require(isinstance(item, str) and item.strip(), "missing item_id")
        require(item not in index[reviewer], "duplicate reviewer/item pair")
        rating = row.get("rating")
        require(rating is None or type(rating) is int and rating in {0, 1, 2}, "rating must be 0/1/2 or null")
        serious = row.get("serious_error")
        require(serious is None or type(serious) is bool, "serious_error must be boolean or null")
        version = row.get("rubric_version")
        require(isinstance(version, str) and version.strip(), "rubric_version is required")
        versions.add(version)
        review_version = row.get("review_version")
        require(review_version is None or review_version == REVIEW_VERSION, "unsupported review_version")
        review_versions.add(review_version)
        if review_version == REVIEW_VERSION:
            criterion = row.get("criterion_id")
            require(isinstance(criterion, str) and criterion.strip(), "v0.3 requires criterion_id")
            require(item not in item_criteria or item_criteria[item] == criterion,
                    "same item_id must refer to the same criterion_id")
            item_criteria[item] = criterion
            quality = row.get("quality_status")
            require(quality in QUALITY_STATUSES, "unsupported quality_status")
            require(row.get("opportunity_status") in OPPORTUNITY_STATUSES, "unsupported opportunity_status")
            require((quality == "assessed") == (rating is not None),
                    "assessed quality requires rating; other quality statuses require null")
            require(quality != "assessed" or row["opportunity_status"] == "occurred",
                    "assessed quality requires an occurred opportunity")
        else:
            require(not any(field in row for field in ("quality_status", "opportunity_status")),
                    "status fields require an explicit v0.3 review_version")
        index[reviewer][item] = row
    require(len(versions) == 1, "do not pool different rubric versions")
    require(len(review_versions) == 1, "do not pool legacy and v0.3 review versions")
    require(len(review_sets) <= 1, "do not compare ratings from different review sets")
    review_version = next(iter(review_versions))
    items = sorted(set(index[reviewer_a]) | set(index[reviewer_b]))
    result = {"reviewers": [reviewer_a, reviewer_b], "rubric_version": next(iter(versions)),
              **_summarize(items, index[reviewer_a], index[reviewer_b], review_version),
              "review_set_identity_assurance": "matching_supplied_sha256" if has_review_set else "absent",
              "limitations": "同分边际导致期望分歧为零时不报告kappa；一致性不能证明评分正确或评审者合格。"}
    if has_review_set:
        result["review_set_sha256"] = next(iter(review_sets))
    if review_version == REVIEW_VERSION:
        groups = {}
        for criterion in sorted(set(item_criteria.values())):
            group_items = [item for item in items if item_criteria[item] == criterion]
            groups[criterion] = _summarize(group_items, index[reviewer_a], index[reviewer_b], review_version)
        result.update({
            "review_version": review_version,
            "primary_agreement": "by_criterion",
            "pooled_metric_role": "diagnostic_only",
            "by_criterion": groups,
            "limitations": (
                "按 criterion_id 分项统计为主；混合不同评分项的总kappa仅供排查。"
                "未评分、不适用和缺少评审记录均不视为零分；状态一致率包含双方均未评分的情况。"
                "输入之外双方均缺失的项目无法从该文件发现，覆盖率分母仅为输入项目并集。"
                "同分边际使期望分歧为零时不报告kappa；小样本指标没有准入或认证含义，"
                "一致性不能证明评分正确或评审者合格。"
            ),
        })
    return result
