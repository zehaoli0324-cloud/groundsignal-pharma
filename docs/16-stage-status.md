# GroundSignal Medical — 10-stage 状态总览

> Updated: 2026-09-07
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
| S5 | Controlled Case / Benchmark Factory | **v0.9 FRESH FAIL / INDEPENDENT RELEASE BLOCKED** | frozen v0.8.1; v0.9 F32 false allow + numeric clean false block; all preconditions pass | exposed v0.9.1 repair, then a new post-freeze fresh suite; gold remains separate |
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
pre-freeze control-plane artifacts                  9/9 VERIFIED
candidate frozen                                        yes
freeze commit                              b5dffbe366904a46d3b6a44172a4f1626daa8924
v0.9 fresh authoring admission       ALLOW_AFTER_VERIFIED_FREEZE
v0.9 admission adversarial scenarios                  13/13 PASS
freeze receipt materializer scenarios                   9/9 PASS
canonical freeze receipt                       present / valid
v0.9 fresh attacks / clean controls                    5 / 4
v0.9 attack decisions                     4 BLOCK / 1 ALLOW
v0.9 clean decisions                      3 ALLOW / 1 BLOCK
v0.9 independent fresh gate                              FAIL
builder / exporter regression                     PASS / PASS
fresh evidence                                  yes (v0.9 FAIL)
```

The repair combines an inspectable multilingual concept mapping, protected identifier evidence and
multi-reference aggregation. It does not convert every `REVIEW` into `BLOCK`. The expanded 36-case
development matrix passes without false block/review; it is synthetic exposed evidence, not fresh.
The pre-freeze attestation pins the candidate's runtime, transitive compatibility files and evidence
outputs with Git blob SHA-1 plus SHA-256. PR #4 was explicitly approved and squash merged as
`b5dffbe366904a46d3b6a44172a4f1626daa8924`; the canonical receipt now binds that commit to all
22 candidate and 9 control-plane pins. The admission guard allowed v0.9 authoring, and now verifies
all 18 committed fresh JSON assets plus a protocol naming the same freeze commit. The immutable first
observation is FAIL; authoring admission is not release approval.
Its deterministic adversarial suite covers 13 states: missing/malformed/self-asserted receipts,
unavailable or unmerged commits, pre-freeze assets, the simulated valid transition, and missing,
mismatched or matching post-freeze protocols, an incorrect control-plane pin, and preseeded receipt/fresh trees. The positive transition uses mocked Git history and is
explicitly development process evidence—not a real freeze, fresh result or release signal.
The receipt materializer adds the inverse transition: it refuses invalid approval references,
unavailable/non-canonical commits and any drift in the 22 pinned artifacts. Only the exact
`origin/main` tip can yield a receipt, and even that receipt records `fresh_evidence=false`,
`gold_approved=false`, S5 release blocked and S6 trust blocked. Its 9/9 tests use simulated Git state;
the pre-freeze baseline remains immutable development-process evidence.
The separate control-plane attestation pins the admission guard, receipt materializer, both test
runners, their committed evidence, the current admission decision, the candidate attestation and its
own verifier. All 9/9 paths and 10/10 boundary assertions pass. This prevents a green candidate hash
from hiding drift in the code that decides whether later fresh authoring is authorized. It remains a
pre-freeze development attestation. The canonical receipt, rather than rewriting this historical
record, establishes `control_plane_frozen=true` at the merge commit.
Receipt schema v0.3 binds both attestations at one canonical freeze commit. The materializer
requires all 22 candidate and all 9 control-plane blobs to match; the admission guard rejects legacy
or partial receipts, control-plane hash/count mismatches and pinned gate-byte drift. It also requires
the freeze commit itself to contain neither a receipt nor the v0.9 fresh tree, preserving chronology.

## 8. Current release decision

```text
S3 bounded conditional evidence            established
S4 bounded independent evidence            established
S5 v0.7 independent first observation      FAIL (immutable)
S5 v0.7.3 development calibration          PASS (not fresh)
S5 v0.8 independent first observation      FAIL (immutable)
S5 v0.8.1 exposed repair                   PASS (not fresh)
S5 v0.9 independent first observation      FAIL (immutable)
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
6. preserve the canonical-main freeze receipt for `b5dffbe366904a46d3b6a44172a4f1626daa8924`
7. preserve the immutable v0.9 first-observation FAIL
8. repair F32 unseen-script recall and numeric near-neighbour precision only as exposed v0.9.1 evidence
9. explicitly freeze the repaired implementation before creating another independent fresh suite
10. require an independent fresh PASS and separate Gold review before any bounded release or S6 evaluation
