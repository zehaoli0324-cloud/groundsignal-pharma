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
| S5 | Controlled Case / Benchmark Factory | **v0.8.1 DEVELOPMENT MATRIX PASS / INDEPENDENT RELEASE BLOCKED** | immutable v0.8 F28/F31 FAIL; expanded v0.8.1 blocks 18/18 attacks and allows 18/18 clean near-neighbours | explicitly freeze, then new independent fresh; gold remains separate |
| S6 | Model / RAG / Agent Harness | Scaffold + fixture proof | reproducible runner, evidence injection, CI fixture | dedicated S6 eval only after S5 bounded release |
| S7 | Evaluation & Safety Gate | Protocol only | rubric v0.2 + regression gate protocol | human/Judge calibration + real model runs |
| S8 | Failure Diagnosis | Scaffold | taxonomy + intervention router | multi-model × multi-case clusters |
| S9 | Intervention / Post-training Data | Interface only | export schema + S5 boundary | real training/intervention experiment |
| S10 | Candidate + Held-out Regression | Fixture contract | baseline-vs-candidate schema | real post-intervention held-out result |

## 2. Why S5 is still the active blocker

S3a/S3b and S4 already have bounded independent evidence. S5 is the first stage whose output can
change later training data, so contamination, identity, authority and provenance failures are release-critical.
S5 v0.7 first observation remains an immutable FAIL. v0.7.3 added exposed regression and
development calibration evidence. After its merge freeze, v0.8 supplied genuinely fresh evidence
and also failed: cross-language lineage was allowed and a multi-protected-source mosaic stopped at
review without closing the export boundary.
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
v0.7.3           broader hard negatives + algorithm/cost calibration        DEVELOPMENT PASS
v0.8 fresh       F28 cross-language + F31 multi-source mosaic                FAIL
v0.8.1           36-case multilingual + mosaic development matrix             DEVELOPMENT PASS
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

## 5. S5 v0.7.3 development calibration checkpoint

`v0.7.3` is **not fresh**. It preserves v0.7.2 and expands only public/exposed development data.

```text
v0.7 first-observation blob                       preserved
v0.7.2 two-negative hard-negative expansion       23/36 false BLOCK (preserved dev FAIL)
calibration families                               15
protected / allowed-dev references                 30 / 45
attributable contamination / clean                 163 / 62
selected hybrid recall                             163/163 = 1.00
selected hybrid clean false-block                  0/62 = 0.00
learned pair grouped-CV recall                     158/163 = 0.9693
p95 latency                                        158.537 ms/candidate
F24-F27 builder / exporter                         all BLOCKED / BLOCKED
v0.7.3 development calibration + regression        PASS
```

Selected development candidate: `s5-lineage-exclusive-anchor-v0.7.3`. It subtracts content already
available in dev before treating fields/spans as protected-only lineage evidence. Exact-core, lexical,
TF-IDF vector and grouped learned-pair comparators are reported separately. A neural cross-encoder was
not used because no frozen reproducible artifact is present.

This larger slice is still synthetic/exposed development calibration and cannot establish unseen
generalization.

Raw metrics: `medical/stage-evals/S5/calibration-v0.7.3.json` and `regression-v0.7.3.json`.
Implementation/report: `medical/stage-evals/S5/S5_V0.7.3_LINEAGE_CALIBRATION_REPORT.md`.
Algorithm handoff: `docs/20-s5-v07-algorithm-handoff.md` + GitHub Issue #1.

## 6. S5 v0.8 post-freeze first observation — immutable FAIL

The v0.8 protocol and fixtures were authored only after freeze commit
`62b791cef47d1f5c7296220557db970d618b7bcf` was merged and its CI passed. All six target blobs
matched the freeze; all preconditions passed.

```text
S5-F28 cross-language lineage          ALLOW   FAIL
S5-F29 semantic abstraction            BLOCK   PASS
S5-F30 cross-field flattening           BLOCK   PASS
S5-F31 multi-protected mosaic          REVIEW  FAIL
clean English same-domain              REVIEW  strict-control FAIL
clean Chinese same-domain               ALLOW  PASS

fresh structural gate                         FAIL
S5 release                      BLOCKED_GOLD_REVIEW
S6 automatic trust                           BLOCKED
```

The clean English control was not blocked from export, but its `REVIEW` result failed the pre-frozen
strict `ALLOW` requirement. This also means that changing every review into a hard block is not an
acceptable repair by itself.

Evidence: `medical/stage-evals/S5/fresh-first-observation-v0.8.json` and
`medical/stage-evals/S5/S5_V0.8_FRESH_LINEAGE_REPORT.md`.

## 7. S5 v0.8.1 exposed repair

v0.8.1 preserves the v0.8 first observation and uses it only as exposed regression evidence.

```text
legacy v0.7.3 development contamination       163/163 BLOCK
legacy v0.7.3 clean controls                    62/62 ALLOW
v0.8 exposed F28-F31                              4/4 BLOCK
v0.8 exposed clean controls                        2/2 ALLOW
broader translation attacks                      12/12 BLOCK
noisy multi-reference mosaics                      6/6 BLOCK
multilingual clean near-neighbours                18/18 ALLOW
pre-freeze pinned artifacts                       22/22 VERIFIED
candidate frozen                                         no
v0.9 fresh authoring admission             BLOCKED_NOT_FROZEN
v0.9 admission adversarial scenarios                  10/10 PASS
builder / exporter regression                     PASS / PASS
fresh evidence                                           no
```

The repair combines an inspectable multilingual concept mapping, protected identifier evidence and
multi-reference aggregation. It does not convert every `REVIEW` into `BLOCK`. The expanded 36-case
development matrix passes without false block/review; it is synthetic exposed evidence, not fresh.
The pre-freeze attestation also pins the candidate's runtime, transitive compatibility files and
evidence outputs with Git blob SHA-1 plus SHA-256. All 22 paths verify, while the attestation
explicitly records `candidate_frozen=false` and a null freeze commit.
The next-fresh admission guard therefore permits no v0.9 asset. A negative injection test confirms
that even one file under the reserved fresh root fails CI unless a canonical-main freeze receipt is
present, its 22 pinned artifacts match, and the new protocol names that exact freeze commit.
Its deterministic adversarial suite covers 10 states: missing/malformed/self-asserted receipts,
unavailable or unmerged commits, pre-freeze assets, the simulated valid transition, and missing,
mismatched or matching post-freeze protocols. The positive transition uses mocked Git history and is
explicitly development process evidence—not a real freeze, fresh result or release signal.

## 8. Current release decision

```text
S3 bounded conditional evidence            established
S4 bounded independent evidence            established
S5 v0.7 independent first observation      FAIL (immutable)
S5 v0.7.3 development calibration          PASS (not fresh)
S5 v0.8 independent first observation      FAIL (immutable)
S5 v0.8.1 exposed repair                   PASS (not fresh)
S5 bounded independent release             NOT ESTABLISHED
S5 gold review                             INCOMPLETE
S6 automatic trust                         BLOCKED
```

The repository still has no real-user validation, completed expert gold approval, demonstrated model-training gain,
or clinical validation. Synthetic/CI evidence is not substituted for those claims.

## 9. Next sequence

1. keep v0.7 first observation immutable
2. treat v0.7.3 only as development/exposed evidence
3. keep the v0.7.3 target and v0.8 first observation immutable
4. treat v0.8.1 only as exposed repair evidence
5. retain the passing 36-case multilingual/mosaic development matrix as exposed evidence
6. freeze the selected implementation and record a canonical-main freeze receipt
7. only after the admission guard opens, create another independent fresh suite
8. require an independent fresh PASS before any bounded release claim
9. keep gold review as a separate release blocker
10. only after bounded S5 release proceed to S6 dedicated evaluation
