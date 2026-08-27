# Optimization Cards

> 每个共性 failure cluster 最终形成一个 Optimization Card：从 observed behavior → user experience → capability gap hypothesis → intervention → metrics → regression。

## 已落地

- [STALE_KNOWLEDGE（真实案例：玛仕度肽）](./STALE_KNOWLEDGE.md)

## 模板（新 cluster 激活时复制此结构）

```yaml
failure_cluster: <CLUSTER_NAME>

observed_behavior:
  - case_XX: <具体行为>
  - case_YY: <具体行为>

user_experience:
  - <用户感受到什么>

capability_gap_hypothesis:
  - <根因假设（Observed Failure ≠ Capability Gap，需多 case 支持）>

intervention_candidates:
  - data: <数据干预>
  - sft_preference: <SFT / preference 干预>
  - prompt_product: <prompt / 产品干预>
  - retrieval_tool: <检索 / 工具干预>

success_metrics:
  - <指标>

regression_cases:
  - <回归用 case>
```
