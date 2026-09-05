# S3a v0.5 Compositional Frame Parser — Development Regression Report

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Implementation: `s3a-compositional-frame-v0.5.0`  
> Implementation commit: `35d484cb4b385363b06d048ef64628ef654aa991`  
> Regression workflow: `33985834584`  
> Artifact: `s3a-v05-exposed-regression` (artifact ID `9975114671`, 90-day retention)  
> Status: **DEVELOPMENT FAIL / NOT ELIGIBLE FOR FRESH FREEZE**

## 术语表

- **Regression（回归测试）**：在已经暴露的数据上检查新实现是否破坏既有能力；不能证明新数据泛化。
- **Critical Proposition Recall（关键命题召回率）**：安全关键命题中被正确抽取的比例。
- **Scope graph（作用域图）**：显式记录句子、子句、条件、人群、否定和模态作用域的中间结构。
- **Frame-local binding（逐框架局部绑定）**：每个语义事件独立绑定 population、condition 和 polarity，而非整段文本共享。
- **Trace contract（轨迹契约）**：每个输出 frame 必须保留可审计的中间结构和 provenance（来源链）。

---

## 1. What v0.5 changed

v0.5 is a material architecture change from v0.4. The parser now introduces a clause/scope graph before proposition compilation:

```text
free text
→ sentence segmentation
→ clause graph
→ sentence shared-context inventory
→ frame-local population / condition binding
→ event-family recognition
→ directed argument canonicalization
→ local negation / modality
→ canonical frame
→ proposition compilation
→ unresolved-critical abstention
```

The implementation deliberately reused only exposed v0.1-v0.4 data during development. No new fresh held-out was created in this iteration.

---

## 2. Exposed regression results

The preregistered development gates were:

```text
F1 >= 90%
Critical Proposition Recall >= 95%
Polarity Accuracy >= 95%
Population Accuracy >= 95%
Condition Binding Accuracy >= 95%
```

Observed results:

| Exposed suite | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---|
| v0.1 | 95.24% | **93.75%** | 100.00% | n/a | 95.24% | **FAIL** |
| v0.2 | 96.67% | 95.65% | 96.67% | 100.00% | 100.00% | PASS |
| v0.3 | 97.44% | 96.43% | 97.44% | 100.00% | 100.00% | PASS |
| v0.4 | **100.00%** | **100.00%** | **100.00%** | **100.00%** | **100.00%** | PASS |

The aggregate development gate is **FAIL** because every exposed suite must remain above its safety threshold, and v0.1 Critical Proposition Recall is 93.75% (<95%).

The fact that the previously failed v0.4 suite now reaches 56/56 propositions and 100% on all five measured dimensions is useful development evidence, but it is exposed regression evidence only.

---

## 3. Failure taxonomy

### A. `CONDITION_SCOPE_INHERITANCE_ERROR`

Exposed item `S3A-003` contains two different thresholds in one sentence:

```text
existing user under eGFR 45 → reassess benefit/risk
;
discontinuation only under 30
```

The second clause contains a bare comparative (`under 30`) without repeating the token `eGFR`. v0.5 failed to parse that clause-local comparator, then inherited the earlier sentence-level `<45` condition. The discontinuation frame was therefore emitted with `<45` instead of `<30`.

This is not a numeric-arithmetic problem. It is a scope-resolution problem: a local comparative must override sentence-level inheritance even when the biomedical variable is elided.

### B. `NEGATION_SCOPE_GAP`

Two exposed constructions still flip contraindication polarity:

```text
Condition M alone is not a contraindication ...
The medicine is not contraindicated merely because ...
```

Both should compile to:

```text
CONTRAINDICATED polarity = NEGATIVE
```

but v0.5 emitted positive contraindication frames. The generic negation grammar covers `does not`, `cannot`, insufficient/inadequate evidence, etc., but misses copular/passive `is not a contraindication` and `is not contraindicated` forms.

This is safety-critical because a wrong-positive contraindication can propagate downstream even when S3b entailment is correct.

### C. `LEGACY_TRACE_ADAPTER_GAP`

The v0.5 workflow also failed its audit trace contract for several frames supplied by the v0.4 fallback layer. Those legacy frames contained the required semantic content but did not contain the new `scope_trace` field.

Observed affected records included:

```text
S3A-007
S3A2-001
S3A2-002
S3A2-012
```

The architecture currently allows a v0.4 fallback for event families v0.5 does not recognize, but fallback frames must be adapted into the v0.5 trace schema with explicit provenance (for example `trigger_family = v0.4_fallback`) before they are auditable.

---

## 4. What did work

Three points are important:

1. The new compositional parser recovered the entire formerly-failing exposed v0.4 suite: 56/56 propositions, including population, polarity and condition scope.
2. Exposed v0.2 and v0.3 both pass the release thresholds despite one polarity error each.
3. The remaining failure modes are localized to scope/trace mechanics rather than a broad collapse in proposition recognition.

These observations justify continuing the v0.5 architecture, but they do **not** justify a PASS or a fresh-validation claim.

---

## 5. Release decision

```text
S3a v0.5 exposed regression      = FAIL
S3a v0.5 trace contract          = FAIL
S3a v0.5 fresh validation        = NOT RUN
S3a free-text release            = HARD FAIL / BLOCKED
S3b structured entailment        = CONDITIONAL PASS
End-to-end S3                    = HARD FAIL
```

Therefore:

```text
free text
→ automatic canonical truth
→ unrestricted Knowledge Graph insertion
```

remains blocked.

No fresh held-out should be constructed from this implementation commit.

---

## 6. Next version target

The next implementation should be a narrow architectural repair (`v0.5.1` or equivalent), not a fresh-test iteration. It should:

1. recognize clause-local bare comparatives such as `under 30` when the biomedical variable is recoverable from sentence context, while preventing an earlier threshold from leaking across the clause boundary;
2. generalize target-local negation for copular/passive constructions such as `is not a contraindication` and `is not contraindicated`;
3. wrap every v0.4 fallback frame with v0.5 trace/provenance metadata instead of allowing unadapted legacy frames into the final trace;
4. rerun only exposed v0.1-v0.4 regressions and the trace contract;
5. freeze a new fresh v0.5 held-out only after all exposed development gates are green and the frozen implementation is recorded.

This report is the permanent audit record for the first v0.5 development regression run.