#!/usr/bin/env python3
"""AB 一致性计算入口（H-3）——含盲法映射。

关键（实测发现，2026-09-13）：
  A/B 两份 review.json 的 sample_id 命名空间不同（A1-xxx vs B1-xxx），
  且样本顺序被独立打乱 —— sample_id 与 sample_sha256 都不能直接配对。
  唯一的配对桥梁是 coordinator_only/blind-map.json 的 author_id 字段。

因此本工具的正确流程为：
  blind-map:  sample_id -> author_id
  然后按 (author_id, criterion_id, target_turn) 配对 A 与 B 的评分行。

纪律（依据 MILESTONES_M0-M5.md / AP07 INSTRUCTIONS.md）：
- 一致 ≠ 准确。本工具只算一致性，不做临床裁决。
- 样本不足以定义 kappa 时输出 null，不填 0。
- 只读，不修改任何 review.json。
- 不得向评审者暴露此映射（blind-map 属 coordinator_only）。

用法：
    ~/venvs/m1env/bin/python ab_agreement.py \
        --a draft_stage1/A/review.json \
        --b draft_stage1/B/review.json \
        --blind-map coordinator_only/blind-map.json
"""
import argparse
import json
import sys
from collections import Counter

ORDINAL = {"pass": 2, "insufficient": 1, "fail": 0}
EXCLUDED = {"unassessed", "not_applicable", "not_observed"}


def load_blind_map(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {sid: (v.get("author_id"), v.get("stage")) for sid, v in d.items()}


def load_rows(path, blind_map):
    """返回 {(author_id, criterion_id, target_turn): row}。"""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    out, unmapped = {}, []
    for r in d.get("rows", []):
        sid = r.get("sample_id")
        if sid not in blind_map:
            unmapped.append(sid)
            continue
        author_id, stage = blind_map[sid]
        key = (author_id, r.get("criterion_id"), r.get("target_turn"))
        if key in out:
            # 同一 key 重复 -> 记录冲突而非静默覆盖
            out[key] = {"__conflict__": True, "first": out[key], "second": r}
        else:
            out[key] = r
    return d, out, unmapped


def weighted_kappa(pairs):
    n = len(pairs)
    if n == 0:
        return None, "no comparable rows"
    if len({p[0] for p in pairs}) == 1 and len({p[1] for p in pairs}) == 1 and len(pairs) < 2:
        return None, "single observation"
    obs = [[0] * 3 for _ in range(3)]
    for a, b in pairs:
        obs[a][b] += 1
    w = [[abs(i - j) / 2.0 for j in range(3)] for i in range(3)]
    po = sum(obs[i][j] * (1 - w[i][j]) for i in range(3) for j in range(3)) / n
    row_m = [sum(obs[i]) / n for i in range(3)]
    col_m = [sum(obs[i][j] for i in range(3)) / n for j in range(3)]
    pe = sum(row_m[i] * col_m[j] * (1 - w[i][j]) for i in range(3) for j in range(3))
    if pe >= 1.0:
        return None, f"pe={pe:.4f} -> kappa undefined (no marginal variance)"
    return (po - pe) / (1 - pe), "linear weighted, ordinal pass>insufficient>fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--blind-map", required=True, dest="blind_map")
    args = ap.parse_args()

    bm = load_blind_map(args.blind_map)
    da, ra, ua = load_rows(args.a, bm)
    db, rb, ub = load_rows(args.b, bm)

    print(f"blind-map: {args.blind_map} ({len(bm)} entries)")
    print(f"A: {args.a} (rows={sum(len(v.get('rows',[])) for v in [da])}, status={da.get('submission_status')})")
    print(f"B: {args.b} (rows={sum(len(v.get('rows',[])) for v in [db])}, status={db.get('submission_status')})")
    if ua:
        print(f"⚠ A 中无 blind-map 映射的 sample_id: {sorted(set(ua))[:5]} (x{len(ua)})")
    if ub:
        print(f"⚠ B 中无 blind-map 映射的 sample_id: {sorted(set(ub))[:5]} (x{len(ub)})")

    common = sorted(set(ra) & set(rb))
    only_a = sorted(set(ra) - set(rb))
    only_b = sorted(set(rb) - set(ra))
    print(f"\n配对后共同 (author_id, criterion, turn) = {len(common)} | 仅A = {len(only_a)} | 仅B = {len(only_b)}")

    conflicts = [k for k in common if isinstance(ra[k], dict) and ra[k].get("__conflict__")]
    if conflicts:
        print(f"⚠ A 侧有 {len(conflicts)} 组合键冲突（同 author+criterion+turn 出现多次）")

    # 未评行检查
    unass = [k for k in common
             if not isinstance(ra[k], dict) or not isinstance(rb[k], dict)
             or ra[k].get("judgment") in EXCLUDED or rb[k].get("judgment") in EXCLUDED]
    if unass:
        st = Counter()
        for k in unass:
            ja = ra[k].get("judgment") if isinstance(ra[k], dict) else "?"
            jb = rb[k].get("judgment") if isinstance(rb[k], dict) else "?"
            st[(ja, jb)] += 1
        print(f"\n⚠ 未评/不适用 = {len(unass)} 行（不参与 kappa）分布：")
        for (ja, jb), c in st.most_common():
            print(f"    A={ja:15s} B={jb:15s} x{c}")

    pairs, disagreements, agree = [], [], 0
    for k in common:
        ra_k, rb_k = ra[k], rb[k]
        if not isinstance(ra_k, dict) or not isinstance(rb_k, dict):
            continue
        ja, jb = ra_k.get("judgment"), rb_k.get("judgment")
        if ja in EXCLUDED or jb in EXCLUDED:
            continue
        if ja not in ORDINAL or jb not in ORDINAL:
            continue
        pairs.append((ORDINAL[ja], ORDINAL[jb]))
        if ja == jb:
            agree += 1
        else:
            disagreements.append({
                "author_id": k[0], "criterion_id": k[1], "target_turn": k[2],
                "judgment_a": ja, "judgment_b": jb,
                "rule_ambiguity": bool(ra_k.get("rule_ambiguity") or rb_k.get("rule_ambiguity")),
                "medical_dispute": bool(ra_k.get("medical_dispute") or rb_k.get("medical_dispute")),
            })

    kappa, note = weighted_kappa(pairs)
    simple = (agree / len(pairs)) if pairs else None

    print(f"\n可比行 = {len(pairs)} | 一致 = {agree} | 分歧 = {len(disagreements)}")
    print(f"简单一致率 = {simple:.4f}" if simple is not None else "简单一致率 = null")
    print(f"线性加权 kappa = {kappa:.4f}" if kappa is not None else f"线性加权 kappa = null ({note})")

    for d in disagreements:
        flags = " ".join(f for f, on in [("RULE_AMBIGUITY", d["rule_ambiguity"]),
                                          ("MEDICAL_DISPUTE", d["medical_dispute"])] if on)
        print(f"  {d['author_id']} {d['criterion_id']}@{d['target_turn']}: A={d['judgment_a']} B={d['judgment_b']} {flags}")

    if not pairs:
        note2 = "all rows unassessed/unsubmitted" if unass else "no comparable rows"
        print(f"\n结论：一致性不可计算（kappa=null）——{note2}。")
        print("这是预期状态：医生侧尚未填写。不是错误。")

    print("\n" + json.dumps({
        "comparable_rows": len(pairs),
        "agreements": agree,
        "disagreements": len(disagreements),
        "simple_agreement": simple,
        "weighted_cohen_kappa": kappa,
        "kappa_note": note,
        "unassessed_rows": len(unass),
        "unmapped_a": len(ua), "unmapped_b": len(ub),
        "conflict_keys": len(conflicts),
        "disagreement_detail": disagreements,
        "note": "一致 != 准确；本报告为一致性计算，非临床裁决；clinical_approval 不在此处设置",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
