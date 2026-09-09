"""Two-rater ordinal agreement, with missing ratings and degenerate margins.

Linear weighted Cohen's kappa uses disagreement |a-b|/2 for ratings 0,1,2.
It describes annotation consistency, not clinical validity or rater expertise.
Serious-error labels are independent from this ordinal quality scale.
"""

from collections import Counter

from .contracts import require


def rater_agreement(rows, reviewer_a, reviewer_b):
    require(reviewer_a != reviewer_b and all(isinstance(x, str) and x.strip() for x in (reviewer_a, reviewer_b)),
            "two distinct reviewer identities are required")
    require(isinstance(rows, list) and bool(rows), "ratings must be a nonempty list")
    index = {reviewer_a: {}, reviewer_b: {}}
    versions = set()
    for row in rows:
        require(isinstance(row, dict), "rating row must be an object")
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
        index[reviewer][item] = row
    require(len(versions) == 1, "do not pool different rubric versions")
    items = sorted(set(index[reviewer_a]) | set(index[reviewer_b]))
    paired, incomplete, safety = [], [], []
    for item in items:
        left, right = index[reviewer_a].get(item), index[reviewer_b].get(item)
        if left is not None and right is not None:
            if left.get("serious_error") is not None and right.get("serious_error") is not None:
                safety.append((left["serious_error"], right["serious_error"]))
            if left.get("rating") is not None and right.get("rating") is not None:
                paired.append((left["rating"], right["rating"]))
                continue
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
    return {"reviewers": [reviewer_a, reviewer_b], "rubric_version": next(iter(versions)),
            "total_items": len(items), "paired_rated_items": n, "incomplete_items": incomplete,
            "rating_coverage": n / len(items), "confusion_matrix_0_1_2": matrix,
            "exact_agreement": exact, "linear_weighted_cohen_kappa": kappa,
            "observed_disagreement": observed, "expected_disagreement": expected,
            "serious_error_paired_items": len(safety),
            "serious_error_disagreements": sum(a != b for a, b in safety),
            "serious_error_unknown_items": len(items) - len(safety),
            "limitations": "同分边际导致期望分歧为零时不报告kappa；一致性不能证明评分正确或评审者合格。"}
