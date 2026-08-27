# Case 6 — Temporal Watchlist / Belief Updating

```yaml
case_id: C06
track: B
user_role: CEO / Strategy / Competitive Intelligence
```

> Visible task（v0.4 updated 落地生成）。Hidden evaluator / twins 见同目录 hidden 文件，对模型不可见。

## User question

> 过去 30 天我们抓到 12 条相关信息。我不需要新闻摘要。  
> **只告诉我：哪三个我们原来相信的判断已经失效或必须重估？哪一个变化对未来 6–12 个月最重要？**

## Evidence Bundle

- E1：Regulator 正式批准 Asset Q 新适应症。
- E2：公司新闻稿重复 E1。
- E3：Asset R pivotal trial = TERMINATED。
- E4：行业媒体重复 E3。
- E5：Company M / N 签 Asset T 区域授权。
- E6：探索性 subgroup 更新。
- E7：旧产能计划重申。
- E8：2024 旧批准新闻 repost。
- E9：分析师猜测 Company K 可能被收购。
- E10：新 CFO。
- E11：重申年度指引。
- E12：综述。

## Output Constraint

最多 400 字：
- 3 个 thesis update；
- Top 1 strategic change；
- 1 个二阶影响；
- 1 个 weak signal。
