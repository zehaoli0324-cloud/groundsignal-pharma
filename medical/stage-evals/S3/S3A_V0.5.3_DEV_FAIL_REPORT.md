# S3a v0.5.3 Semantic-Typing + Guard-Composition Repair — Development FAIL

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Version: `s3a-compositional-frame-v0.5.3`  
> Parser implementation commit: `e602e5d20623dcef519a9e51475ebbc6ef32606d`  
> Initial exposed-regression workflow: `33997403549`  
> Diagnostic replay workflow: `33997463136`  
> Raw replay preservation commit: `fec3aa3ca31a84cfe9d988f6f3499055a3b78416`  
> Replay artifact: `s3a-v053-exposed-first-fail-replay` / ID `9978486176`  
> Artifact SHA-256: `683df9f34fd17ab16f085b4035678be373207779155be8cc8bb5e2f1b33b1f25`  
> Status: **DEVELOPMENT FAIL — no parser repair performed after observing the FAIL in this iteration**

## 术语表

- **Semantic typing（语义类型化）**：先判断数值属于 eGFR、血小板、年龄等哪类变量，再决定是否能进入结构化条件。
- **Guard composition（安全保护组合）**：在生成命题前统一检查动作、条件、逻辑分支和本体覆盖，任何高风险语义不能无损表示时整体弃权。
- **Exposed regression（已暴露回归）**：开发者已经看过的数据，只用于修复后的回归验证，不能再作为 fresh 泛化证据。
- **Unsafe simplification（不安全简化）**：原文有条件/分支的高风险规则被错误压缩成更简单的自动真值。
- **Trace contract（轨迹契约）**：输出保留 scope/frame/provenance 结构，允许审计错误发生在哪一层。

---

## 1. Why v0.5.3 exists

The immutable v0.5.2 fresh held-out failed at:

```text
F1                                  78.20%
Critical Proposition Recall         67.27%
Condition Binding Accuracy          92.86%
Required-abstention accuracy        50.00%
Known-case abstention rate          10.00%
Combined release                    FAIL
```

Its highest-risk defect converted a non-representable ALT/bilirubin conditional stopping rule into an unconditional `DISCONTINUE` truth. v0.5.3 therefore attempted structural rather than item-specific repair:

```text
1. typed numeric-condition mentions
2. sentence-bounded management scope + explicit anaphora handling
3. relation direction separated from relation polarity
4. type-aware ontology coverage guard before proposition emission
5. hard invariant: unrepresentable high-risk rules may not emit simplified truth
```

No new fresh set was created. The v0.5.2 fresh suite is now exposed regression data.

---

## 2. Evaluation protocol

The first v0.5.3 exposed-regression run was workflow `33997403549`. It failed the combined development gate.

Because that initial workflow uploaded but did not permanently commit its raw JSON files, a deterministic replay was run **without modifying the parser** as workflow `33997463136`. The replay outputs were committed under:

`medical/stage-evals/S3/runs/s3a-v053-exposed-first-fail/`

The initial workflow remains the primary chronology record; the replay exists only to make raw metrics/failures permanently auditable in GitHub.

Reused proposition gates:

```text
F1 >= 0.90
Critical Proposition Recall >= 0.95
Polarity Accuracy >= 0.95
Population Accuracy >= 0.95
Condition Binding Accuracy >= 0.95
```

Reused safety gates:

```text
Required-abstention accuracy = 1.00
Known-case abstention rate <= 0.05
Trace contract = PASS
No required-abstention item may emit a partial proposition
```

---

## 3. Regression results

| Exposed suite | Precision | Recall | F1 | Critical Recall | Polarity | Population | Condition | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v0.1 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | n/a | 100.00% | PASS |
| v0.2 | 96.67% | 96.67% | 96.67% | 95.65% | 100.00% | 96.67% | 100.00% | PASS |
| v0.3 | 97.44% | 97.44% | 97.44% | 96.43% | 97.44% | 100.00% | 100.00% | PASS |
| v0.4 | 82.76% | 85.71% | 84.21% | 81.40% | 96.00% | 92.31% | 100.00% | **FAIL** |
| v0.5.1 | 95.38% | 93.94% | 94.66% | 91.67% | 98.41% | 96.88% | 98.41% | **FAIL** |
| v0.5.2 | 84.00% | 86.30% | 85.14% | 83.64% | 100.00% | 96.92% | 91.30% | **FAIL** |

The v0.5.2 exposed suite improved substantially relative to its immutable fresh first run (`F1 78.20% -> 85.14%`, critical recall `67.27% -> 83.64%`) but remains well below the preregistered release threshold.

### Abstention safety

```text
v0.5.1 required-abstention accuracy       75.00%   FAIL
v0.5.1 known-case abstention rate          0.00%   PASS
v0.5.2 required-abstention accuracy      100.00%   PASS
v0.5.2 known-case abstention rate          0.00%   PASS
```

The only exposed v0.5.1 mandatory-abstention miss is `S3A51-039` (QTc/torsades permanent-suspension wording).

### Unsafe-simplification invariant

The new invariant passes on all six v0.5.2 required-abstention cases:

```text
required-abstention cases       6
unsafe simplifications          0
Gate                           PASS
```

This is a meaningful safety improvement over v0.5.2: the previously observed ALT/bilirubin conditional stopping rule no longer becomes an unconditional automatic truth.

### Trace contract

The trace gate passed across all emitted rows. The architecture remains auditable even though semantic performance is insufficient.

Combined development decision:

```text
all exposed proposition suites       FAIL
abstention safety                    FAIL
trace contract                       PASS
unsafe-simplification invariant      PASS
combined development release         FAIL
fresh validation                     NOT RUN
```

---

## 4. Failure taxonomy before any repair

### F1 — Population-role recognition regressed under management-frame rebuild

Examples include treatment-naive/newly-starting/continuing formulations. v0.5.3 rebuilt management frames globally, but the replacement population recognizer covers fewer surface forms than the mature v0.5.2/v0.5.1 path. This creates null or incorrect populations despite otherwise correct event/condition extraction.

This is a design regression caused by replacing a mature subcomponent rather than composing a targeted repair layer.

### F2 — Multi-event scope remains too coarse inside one sentence

Compact constructions such as reassessment at one threshold followed by discontinuation at another threshold still bind the wrong eGFR value. Sentence-bounded scope is safer than document-wide inheritance, but **sentence scope is still too large**. The required unit is an event-local coordination span.

### F3 — Negative management clauses still inherit unrelated renal conditions

When a sentence contains an eGFR rule plus a separate negative statement based on age/platelets, the negative action can still inherit the eGFR condition. Variable typing prevented platelet `100` from becoming `eGFR <100`, but it did not prove that the previous eGFR belongs to the negative event.

Typed variables therefore solve only half of condition binding; event-condition ownership still needs an explicit graph edge.

### F4 — Contraindication negation grammar is not compositional enough

Phrases such as `inadequate grounds for declaring ... contraindicated`, `insufficient to classify ... as contraindicated`, and `neither ... constitutes a contraindication` are still emitted with positive polarity in some exposed cases. Mixed positive/negative contraindication statements in one sentence can also collapse onto the same condition.

### F5 — Whole-family management rebuild causes avoidable regression

v0.5.3 replaced all management frames whenever a management event was detected. This fixed some v0.5.2 failures but damaged previously working population, shared-condition, and lexical coverage in v0.4/v0.5.1.

The next version should preserve mature base frames and repair only frames whose typed scope is inconsistent, rather than rebuilding the entire family from scratch.

### F6 — Additive relation repair leaves contradictory legacy frames alive

Several cases now contain the correct repaired relation **plus** an incorrect legacy relation. Examples include:

- a negative endpoint-evidence sentence retaining a positive `ACHIEVES_ENDPOINT` frame;
- passive inverse association obtaining the correct negative relation while the old positive relation remains;
- supersession producing a cleaned object while the punctuation-contaminated legacy object remains.

Exact-key deduplication cannot resolve semantic conflicts. A relation-family arbitration layer is required.

### F7 — Endpoint declaration and endpoint achievement are insufficiently separated

A phrase such as `the prespecified primary endpoint was achieved` can create an unnecessary `HAS_PRIMARY_ENDPOINT` proposition in addition to `ACHIEVES_ENDPOINT`. Conversely, negative evidence wording can coexist with a stale positive achievement frame. Event ontology roles need precedence rules rather than additive matching.

### F8 — Passive trial-support grammar has determiner and paraphrase gaps

`Option T is supported by a randomized trial` is still missed even though the direction schema exists. The grammar assumes a narrower determiner pattern and does not consistently cover `a/an/the` plus passive support variants. Older trial-support fallbacks also still emit malformed objects such as `approach` or `to`.

### F9 — Explicit currentness needs discourse-level entity carryover

`Guideline W is not superseded by Guideline X; W remains the operative recommendation source` recovers the negative supersession but misses currentness because the second clause uses the short anaphoric entity `W` rather than repeating `Guideline W`.

### F10 — Mandatory-abstention guard still has a lexical blind spot

The v0.5.2 exposed mandatory-abstention cases are now 6/6 correct, but the older v0.5.1 QTc/torsades rule (`S3A51-039`) is missed. The guard recognizes some active medication-action forms but not all passive/permanent suspension morphology.

This confirms that guard coverage is improved but still partly trigger-dependent.

### F11 — Anaphoric condition semantics remain unresolved

The `same eGFR` family remains structurally ambiguous. v0.5.3 preserves the antecedent operator, which is semantically defensible, but the exposed v0.5.2 gold labels one case as equality after an antecedent `below eGFR 42`. The immutable dataset is not changed. Future shadow audit should separately adjudicate this annotation ambiguity.

### F12 — Population and relation arbitration are now the dominant architecture bottlenecks

The v0.5.3 safety guard is stronger than v0.5.2, but recall/precision remain limited because the system lacks a single typed representation in which:

```text
entity mention -> semantic type
condition mention -> typed variable
condition -> owning event
relation surface form -> canonical direction
polarity cue -> relation-local polarity
candidate frames -> family arbitration -> one canonical proposition set
```

Without that arbitration layer, adding correct frames can still increase false positives.

---

## 5. Release decision

```text
S3b structured entailment          = CONDITIONAL PASS
S3a v0.5.3 exposed proposition     = FAIL
S3a v0.5.3 abstention              = FAIL
S3a v0.5.3 trace                   = PASS
S3a unsafe-simplification invariant= PASS on exposed v0.5.2 cases
S3a v0.5.3 fresh validation        = NOT RUN
S3a free-text release              = HARD FAIL / BLOCKED
End-to-end S3                      = HARD FAIL
S4 automatic truth ingestion       = BLOCKED
```

No new fresh held-out is permitted for v0.5.3. No downstream stage may trust v0.5.3 free-text-derived truth.

---

## 6. Next version recommendation

Build one coherent **S3a v0.5.4 typed event graph + family arbitration repair**. The key change should not be more regex inventory. It should introduce:

```text
1. typed mention layer
   entity / variable / population / action mentions with offsets

2. event-local ownership graph
   each condition/population/polarity cue attaches to one event node

3. non-destructive repair
   preserve mature base frames; only replace a frame when typed ownership proves inconsistency

4. relation-family arbitration
   resolve conflicting legacy/repaired frames before proposition compilation

5. guard morphology normalization
   active/passive/permanent stop-suspend-withhold forms map to one high-risk action type
```

Development must reuse all v0.1-v0.5.2 exposed suites plus abstention, trace, and unsafe-simplification gates. Only after all are green may a brand-new fresh/shadow held-out be frozen.
