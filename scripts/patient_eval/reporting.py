"""Escaped offline reports and family-clustered paired exploratory statistics."""

from collections import defaultdict
from html import escape
import json
import math
import random


def paired_family_comparison(rows: list[dict], baseline: str, candidate: str,
                             seed: int = 7, resamples: int = 2000) -> dict:
    """Compare complete matched pairs, assigning every family equal weight.

    Unmatched records and duplicate keys are errors, so missing target failures
    cannot silently disappear. Supply outcome scores including target failures;
    independently invalid measurements must be resolved before calling this.
    Scores are *not* clinical safety decisions. Keep serious errors separate.
    """
    if not isinstance(baseline, str) or not baseline or not isinstance(candidate, str) or not candidate:
        raise ValueError("baseline and candidate must be non-empty platform names")
    if baseline == candidate:
        raise ValueError("baseline and candidate must be different")
    if type(resamples) is not int or resamples < 100:
        raise ValueError("resamples must be an integer of at least 100")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    selected = [row for row in rows if isinstance(row, dict) and row.get("platform") in {baseline, candidate}]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("rows must contain objects")
    if not selected:
        raise ValueError("no rows for the requested platforms")
    index = {baseline: {}, candidate: {}}
    lanes, protocols = set(), set()
    for row in selected:
        for field in ("family_id", "scenario_id", "variant", "protocol_id"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{field} must be a non-empty string")
        repeat = row.get("repeat_id")
        if type(repeat) not in (str, int) or (isinstance(repeat, str) and not repeat.strip()):
            raise ValueError("repeat_id must be a non-empty string or integer")
        lane = row.get("comparison_lane")
        if lane not in {"fixed_prefix", "free_dialogue"}:
            raise ValueError("invalid comparison_lane")
        score = row.get("score")
        if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("score must be a finite number in [0, 1]")
        lanes.add(lane)
        protocols.add(row["protocol_id"])
        key = (row["family_id"], row["scenario_id"], row["variant"], str(repeat), lane, row["protocol_id"])
        if key in index[row["platform"]]:
            raise ValueError("duplicate platform/pair key")
        index[row["platform"]][key] = float(score)
    if len(lanes) != 1:
        raise ValueError("do not pool fixed-prefix and free-dialogue comparisons")
    if len(protocols) != 1:
        raise ValueError("run each comparison protocol separately")
    missing_baseline = set(index[candidate]) - set(index[baseline])
    missing_candidate = set(index[baseline]) - set(index[candidate])
    if missing_baseline or missing_candidate:
        raise ValueError(f"unmatched pairs: missing baseline={len(missing_baseline)}, candidate={len(missing_candidate)}")
    grouped = defaultdict(list)
    for key in sorted(index[baseline]):
        grouped[key[0]].append(index[candidate][key] - index[baseline][key])
    family_deltas = {family: sum(values) / len(values) for family, values in sorted(grouped.items())}
    effects = list(family_deltas.values())
    estimate = sum(effects) / len(effects)
    interval = None
    if len(effects) >= 2:
        rng = random.Random(seed)
        draws = sorted(sum(rng.choice(effects) for _ in effects) / len(effects) for _ in range(resamples))

        def percentile(probability):
            position = probability * (len(draws) - 1)
            lower, upper = math.floor(position), math.ceil(position)
            return draws[lower] + (draws[upper] - draws[lower]) * (position - lower)

        interval = [percentile(0.025), percentile(0.975)]
    return {
        "baseline": baseline, "candidate": candidate,
        "comparison_lane": next(iter(lanes)), "protocol_id": next(iter(protocols)),
        "paired_sessions": len(index[baseline]), "family_count": len(effects),
        "family_mean_deltas": family_deltas, "mean_delta": estimate,
        "confidence_interval_95": interval,
        "bootstrap_unit": "family", "family_weighting": "equal",
        "seed": seed, "resamples": resamples if interval is not None else 0,
        "excluded_other_platform_rows": len(rows) - len(selected),
        "exploratory": True,
        "limitations": (
            "仅一个独立案例家族，不报告置信区间。"
            if interval is None else
            "区间仅重采样当前独立案例家族；小样本尤其不稳定，不能代表真实患者总体。"
        ),
        "safety_note": "均值改善不能抵消严重错误；结果依赖评分完整性和输入配对协议。",
    }


def _text(value):
    return escape(str(value), quote=True)


def _json(value):
    return _text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _criterion_items(score):
    values = score.get("criterion_results", [])
    if isinstance(values, dict):
        return [dict(value, criterion_id=key) if isinstance(value, dict)
                else {"criterion_id": key, "result": value} for key, value in values.items()]
    return values if isinstance(values, list) else []


def render_report(bundle: dict) -> str:
    """Render a self-contained development report; every supplied value is escaped."""
    if not isinstance(bundle, dict) or bundle.get("scope") != "development_only":
        raise ValueError("the current report supports development_only scope")
    sessions, scores, diagnoses = (bundle.get(key, []) for key in ("sessions", "scores", "diagnoses"))
    if any(not isinstance(items, list) or any(not isinstance(item, dict) for item in items)
           for items in (sessions, scores, diagnoses)):
        raise ValueError("sessions, scores and diagnoses must be lists of objects")
    title = _text(bundle.get("title", "患者多轮评测 · 开发报告"))
    critical = sum(score.get("critical_failure") is True for score in scores)
    unknown_critical = sum(score.get("critical_failure") is None for score in scores)
    incomplete = sum(score.get("evaluation_complete") is not True for score in scores)
    invalid = sum(session.get("status") == "measurement_invalid" for session in sessions)
    target_errors = sum(session.get("status") == "target_error" for session in sessions)
    parts = [
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<title>{title}</title>',
        '<style>body{font:16px/1.65 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#182434;background:#fafbfd}h1,h2,h3{line-height:1.3}section{background:white;border:1px solid #d6dfeb;border-radius:8px;padding:20px;margin:20px 0}table{width:100%;border-collapse:collapse;table-layout:fixed}td,th{border:1px solid #d6dfeb;padding:9px;vertical-align:top;overflow-wrap:anywhere;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f4f8;padding:12px}blockquote{margin:8px 0;padding:10px 14px;border-left:4px solid #55779a;white-space:pre-wrap;overflow-wrap:anywhere}.note{background:#fff4d7;padding:14px;border-radius:6px}.critical{color:#a12323;font-weight:600}summary{cursor:pointer}</style>',
        f'</head><body><h1>{title}</h1>',
        '<p class="note">范围：开发验证。未评估项不能计为通过；严重错误单列，不能被平均分抵消。黑盒记录只能支持可见行为和待验证的归因假设，不能证明平台内部算法或工程根因。</p>',
        '<section><h2>观察到的结果</h2>',
        f'<p>会话 {_text(len(sessions))} 条；评分 {_text(len(scores))} 条；未完成全部评分 {_text(incomplete)} 条。</p>',
        f'<p class="critical">已记录严重错误 {_text(critical)} 条；严重错误是否存在尚未确定 {_text(unknown_critical)} 条。</p>',
        f'<p>目标服务失败 {_text(target_errors)} 条；独立测量无效 {_text(invalid)} 条。目标服务失败必须保留在任务结果中，不能当作测量无效删除。</p>',
        '</section>',
    ]
    for score in scores:
        parts.extend([
            f'<section><h2>评分：{_text(score.get("session_id", "未标识会话"))}</h2>',
            f'<p>评估完成：{_text(score.get("evaluation_complete", "未知"))}；覆盖率：{_text(score.get("assessment_coverage", "未知"))}；严重错误：{_text(score.get("critical_failure", "未知"))}。</p>',
            '<table><thead><tr><th>判据</th><th>结果</th><th>证据与原因</th></tr></thead><tbody>',
        ])
        for item in _criterion_items(score):
            if not isinstance(item, dict):
                item = {"result": item}
            parts.append(f'<tr><td>{_text(item.get("criterion_id", "未知"))}</td><td>{_text(item.get("outcome", item.get("result", "未评")))}</td><td><pre>{_json(item)}</pre></td></tr>')
        parts.extend(['</tbody></table>', f'<details><summary>完整评分记录</summary><pre>{_json(score)}</pre></details></section>'])
    parts.append('<section><h2>缺陷归因与证据强度</h2>')
    if not diagnoses:
        parts.append('<p>未提供归因记录。不能由单个错误回答直接断言内部算法或工程缺陷。</p>')
    for diagnosis in diagnoses:
        parts.append(f'<pre>{_json(diagnosis)}</pre>')
    parts.append('</section>')
    if bundle.get("controls"):
        parts.extend(['<section><h2>受控回放原始记录</h2><p>下列记录保留被改变的输入、控制会话及审核依据，便于复核归因。</p>',
                      f'<details><summary>查看控制材料</summary><pre>{_json(bundle["controls"])}</pre></details></section>'])
    if "comparison" in bundle:
        parts.extend(['<section><h2>配对比较</h2><p>按案例家族聚类；不同对话协议分别分析。平台差异不是内部根因证明。</p>', f'<pre>{_json(bundle["comparison"])}</pre></section>'])
    for session in sessions:
        parts.extend([
            f'<section><h2>原文证据：{_text(session.get("session_id", "未标识会话"))}</h2>',
            f'<p>平台：{_text(session.get("platform", "未知"))}；观测范围：{_text(session.get("observability", "未知"))}；状态：{_text(session.get("status", "未知"))}。</p>',
        ])
        for turn in session.get("turns", []):
            if isinstance(turn, dict):
                parts.append(f'<p><strong>{_text(turn.get("turn_id", ""))} · {_text(turn.get("role", ""))}</strong></p><blockquote>{_text(turn.get("content", ""))}</blockquote>')
        parts.extend([f'<details><summary>采集与评估记录</summary><pre>{_json(session)}</pre></details>', '</section>'])
    parts.append('</body></html>')
    return "\n".join(parts)
