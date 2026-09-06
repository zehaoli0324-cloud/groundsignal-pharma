# GroundSignal Medical — 10-stage 状态总览

> Updated: 2026-09-06  
> Release posture: **S5 BLOCKED; therefore S6 automatic trust remains BLOCKED**

## 术语表

- **Fresh held-out（全新留出评测）**：实现先冻结，再创建的新测试；首次结果不可改写。
- **Exposed regression（已暴露回归）**：已经见过并用于修复的问题集；只能证明旧问题未复发，不能证明未知泛化。
- **Hard gate（硬门禁）**：高风险失败不能被平均分抵消；任一 hard gate 失败都阻止放行。
- **Gold review（专家金标准审核）**：独立专家/人工审核；结构测试 PASS 不等于 gold approved。
- **NFKC — Normalization Form Compatibility Composition（Unicode 兼容组合规范化）**：把兼容等价字符也归一到系统身份表示，降低视觉/兼容字符碰撞。
- **CI — Continuous Integration（持续集成）**：自动执行 evaluator 和回归测试；CI 绿色不等于临床验证。

## 1. Stage scoreboard

| Stage | 名称 | 当前状态 | 最强证据 | 下一门槛 |
|---|---|---|---|---|
| S1 | User Need / Workflow Discovery | Partial | 48 seed tasks + risk matrix + user-research plan | 真实用户访谈/日志频率 |
| S2 | Knowledge Search & Source Routing | CONDITIONAL PASS | v0.3 fresh routing 91.7%; S2→S3 joint 94.44%; DailyMed 3/3 | real-source coverage + v0.4 negation/exclusion repair |
| S3a | Proposition Extraction | bounded CONDITIONAL PASS | fresh F1 98.90%; critical recall 100%; mandatory abstention 6/6 | longer/noisier real-source coverage |
| S3b | Evidence Relation | bounded CONDITIONAL PASS | 40/40 relation; high-risk false-support 0 | broader real-source relation set |
| S4 | Medical KG Construction / Update | CONDITIONAL PASS | first fresh 18/20 FAIL → repair regression 20/20 → new independent fresh 20/20; must-reject 7/7 | persistent real-source graph |
| S5 | Controlled Case / Benchmark Factory | **v0.7.2 EXPOSED REPAIR PASS / INDEPENDENT RELEASE BLOCKED** | immutable v0.7 fresh F24–F27 FAIL; v0.7.2 exposed F24–F27 all blocked at builder + exporter boundary | broader algorithm calibration, freeze, then new hidden fresh; gold review remains separate |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | dedicated S6 eval only after S5 bounded release |
| S7 | Evaluation & Safety Gate | Protocol only | rubric v0.2 + regression gate protocol | human/Judge calibration + real model runs |
| S8 | Failure Diagnosis | Scaffold | taxonomy + intervention router | multi-model × multi-case clusters |
| S9 | Intervention / Post-training Data | Interface only | export schema + S5 boundary | real training/intervention experiment |
| S10 | Candidate + Held-out Regression | Fixture contract | baseline-vs-candidate schema | real post-intervention held-out result |

## 2. Why S5 is still the active blocker

S3a/S3b and S4 already have bounded independent evidence. S5 is the first stage whose output can
change later training data, so contamination, identity, authority and provenance failures are release-critical.
S5 v0.7 first observation remains an immutable FAIL. v0.7.2 is only exposed regression evidence.
Therefore S5 cannot be called PASS, and S6 cannot automatically trust S5 output.

## 3. S5 evidence history

```text
v0.1             split/export/gold/decision contract                            FAIL
v0.2 fresh       F4-F7 provenance/payload/exemption                             FAIL
v0.2.1           exposed repair                                                  PASS
v0.3 fresh       F8-F11 location/self-auth/suite-manifest identity              FAIL
v0.3.1           exposed repair                                                  PASS
v0.4 fresh       F12-F15 caller policy/off-repo/cross-suite/family-root         FAIL
v0.4.1           exposed repair                                                  PASS
v0.5 fresh       F16-F19 payload/context/namespace/family escape                FAIL
v0.5.1           exposed repair                                                  PASS
v0.6 fresh       F20-F23 derived lineage/NFC/TOCTOU                             FAIL
v0.6.1           exposed repair                                                  PASS
v0.7 fresh       F24-F27 lineage-generalization/NFKC                             FAIL
v0.7.1           deterministic builder repair F24/F27                      PARTIAL REPAIR
v0.7.2           hybrid lineage + exporter validation exposed regression   PASS
```

Each fresh FAIL remains permanent evidence; later repair never overwrites it.

## 4. S5 v0.7 first observation — immutable independent FAIL

The v0.7 suite was authored after implementation freeze `b2e2696bae9cf57bbf255e67e64dd63bd8773ff8`.
Its first observation is preserved in `medical/stage-evals/S5/fresh-first-observation-v0.7.json`.

```text
S5-F24 cross-split semantic duplicate isolation        FAIL
S5-F25 paraphrased heldout-derived ordinary laundering FAIL
S5-F26 partial heldout fragment reuse                  FAIL
S5-F27 NFKC compatibility-equivalent case identity     FAIL

fresh structural gate                     FAIL
S5 release                               BLOCKED_GOLD_REVIEW
S6 automatic trust                       BLOCKED
```

This cannot be relabeled after repair.

## 5. S5 v0.7.2 exposed repair checkpoint

`v0.7.2` is **not fresh**. It reuses the exposed v0.7 cases only as regression.

```text
v0.7 first-observation blob                preserved
normal baseline                            PASS
F24 builder / exporter validator          BLOCKED / BLOCKED
F25 builder / exporter validator          BLOCKED / BLOCKED
F26 builder / exporter validator          BLOCKED / BLOCKED
F27 builder / exporter validator          BLOCKED / BLOCKED
exposed failed gates                       0
regression gate                            PASS
```

Algorithm candidate: `s5-lineage-hybrid-v0.7.2`.
Development-only detector probe:

```text
contaminated positives          5
clean negatives                 2
hybrid recall                   5/5 = 1.00
clean false-block               0/2 = 0.00

ablation recall:
exact semantic core             1/5 = 0.20
record lexical only             3/5 = 0.60
hybrid record+field+span        5/5 = 1.00
```

This is too small and too exposed to establish unseen generalization. Embedding/cross-encoder
comparison, larger negatives, threshold calibration and latency/index cost are still missing.

Raw metrics: `medical/stage-evals/S5/regression-v0.7.2.json`.  
Implementation/report: `medical/stage-evals/S5/S5_V0.7.2_HYBRID_LINEAGE_REPAIR_REPORT.md`.  
Algorithm handoff: `docs/20-s5-v07-algorithm-handoff.md` + GitHub Issue #1.

## 6. Current release decision

```text
S3 bounded conditional evidence            established
S4 bounded independent evidence            established
S5 v0.7 independent first observation      FAIL (immutable)
S5 v0.7.2 exposed regression               PASS
S5 bounded independent release             NOT ESTABLISHED
S5 gold review                             INCOMPLETE
S6 automatic trust                         BLOCKED
```

The repository still has no real-user validation, completed expert gold approval, demonstrated model-training gain,
or clinical validation. Synthetic/CI evidence is not substituted for those claims.

## 7. Next sequence

1. keep v0.7 first observation immutable
2. treat v0.7.2 only as exposed repair evidence
3. expand clean-negative coverage without using any future hidden suite
4. add more already-exposed/development paraphrase, partial-reuse and compositional transformations
5. compare exact-core vs record lexical vs hybrid, and embedding/cross-encoder only if reproducible artifacts are available
6. calibrate BLOCK/REVIEW thresholds and measure latency/index size
7. freeze the selected lineage implementation
8. only after freeze author a new unseen S5 lineage family
9. require independent first observation before any bounded release claim
10. only after bounded S5 release proceed to S6 dedicated evaluation
