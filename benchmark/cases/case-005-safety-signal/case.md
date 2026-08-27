# Case 5 — Safety Attribution

```yaml
case_id: C05
track: B
user_role: Clinical Development / Safety / Portfolio Strategy
```

> Visible task（v0.4 updated 落地生成）。Hidden evaluator / twins 见同目录 hidden 文件，对模型不可见。

## User question

> Asset S 出现严重肝毒性。A 是同靶点，也有类似 warning；B 同靶点但没有。  
> **我们现在最应该把风险归到 molecule、platform 还是 target？这个判断会怎样影响 portfolio 决策？下一步哪条证据最有区分力？**

## Evidence Bundle

- S：数例严重 hepatic event。
- A：同 target；不同 molecule；有 hepatic warning。
- B：同 target；较大暴露；无同类 warning。
- S 与 A 有相似 linker / delivery chemistry。
- B 使用不同 modality。
- spontaneous report 有 signal。
- mechanism hypothesis 未验证。
- 无 regulator class-wide warning。

## Output Constraint

必须：
- 排序至少 2 个 causal hypotheses；
- 指出 negative control；
- 给 portfolio action；
- 给 discriminating evidence。
