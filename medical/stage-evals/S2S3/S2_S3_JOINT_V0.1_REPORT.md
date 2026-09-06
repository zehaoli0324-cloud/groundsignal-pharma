# S2 → S3 Joint Vertical-Slice v0.1 — First-run PASS

> **S2 = Knowledge Search & Source Routing（知识搜索与来源路由）**  
> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> **S3b = Structured Proposition Entailment（结构化命题蕴含判定）**  
> Joint harness: `s2-s3-joint-pipeline-v0.1`  
> Harness commit: `cca5a6bbf5bb56ca30c2a0dc06527d748d87e9a4`  
> Harness blob SHA: `48cf7eeb500ed9ba837f11394991a2e070a61971`  
> Suite freeze commit: `65f6797c736792ea0da743c6f40303bf6f2825df`  
> Suite blob SHA: `55d191267eb754f61348c6a3f54488173a2ea50d`  
> Workflow source commit: `142ceded3094b2961d2e0183a35eca15146ce671`  
> First-run workflow: `34004328424`  
> Raw-result preservation commit: `b31895c35a0875e7fd18c93ba1c97d5ff0a8f416`  
> Dataset SHA-256: `93d7bd2f2e8a53d6f6378f6a31b4821dd554a37480bb8074f98e166dfbb4ea9b`  
> Status: **FIRST-RUN PASS — controlled vertical slice + live DailyMed sidecar**

## 术语表

- **Vertical slice（纵向切片）**：让一个任务真正经过多个 stage，而不是把各 stage 的单测分数简单相加。
- **Source handoff（来源交接）**：S2 选出的来源实际决定进入 S3 的证据 passage，而不是测试时直接把正确证据塞给 S3。
- **Controlled passage bank（受控段落库）**：为了隔离 stage 接口能力而固定的来源段落；可验证路由→证据→语义→蕴含链，但不等于真实互联网检索。
- **DailyMed live sidecar（DailyMed 实时旁路测试）**：在同一 workflow 中额外运行真实网络版 DailyMed 当前版本/关键段落检索，用来验证 S2 的真实外部 retrieval 没有退化。
- **High-risk false support（高风险错误支持）**：真实 gold 不是直接支持，但系统错误输出 `DIRECT_SUPPORT`。

---

## 1. Why this test is different

Previous evidence was split:

```text
S2 routing / retrieval evaluated independently
S3a free-text extraction evaluated independently
S3b structured entailment evaluated independently
```

That leaves a major interface risk:

```text
S2 chooses a source
→ wrong passage crosses boundary
→ S3a extracts a plausible proposition
→ S3b correctly reasons over the wrong proposition
→ individual stages can look good while the chain is wrong
```

The v0.1 joint harness therefore executes the actual controlled handoff:

```text
user query
→ S2 intent classification
→ ranked source IDs
→ select a passage only from a source reachable through S2 ranking
→ S3a v0.5.6.1 free-text extraction
→ canonical propositions
→ S3b v0.2.2 candidate-claim entailment
→ DIRECT_SUPPORT / PARTIAL_SUPPORT / CONTRADICTS / DOES_NOT_SUPPORT
```

No gold proposition is inserted between S3a and S3b.

The harness was committed before the held-out suite was authored and frozen.

---

## 2. Test composition

The frozen suite contains 18 joint tasks spanning:

```text
U.S. current product label / DailyMed
ClinicalTrials.gov trial status and endpoint evidence
FAERS safety-signal / causality / incidence boundaries
PubMed randomized-trial and association evidence
AHA professional guidance
LiverTox DILI reference
FDA pharmacogenomic evidence
generic medical-literature fallback
population-scope overclaim
absence-of-evidence endpoint claims
```

Each task contains source-scoped controlled documents, including distractors, so the S2 ranking influences which text is available to S3.

Preregistered gates:

```text
Intent Accuracy                    >= 90%
Primary Source Accuracy            >= 90%
Source Handoff Accuracy            >= 90%
S3a non-abstention on known cases  >= 95%
S3b Relation Accuracy              >= 90%
End-to-end Accuracy                >= 85%
High-risk False-Support Count       = 0
```

The same workflow also reruns the existing three-case live DailyMed truth-retrieval suite. Combined release requires both controlled handoff and live DailyMed retrieval to pass, plus independently passing S3a/S3b preconditions.

---

## 3. Immutable first-run result

### Controlled S2 → S3 handoff

```text
n items                              18
S2 Intent Accuracy                94.44%   PASS
S2 Primary Source Accuracy        94.44%   PASS
Source Handoff Accuracy          100.00%   PASS
S3a known-case non-abstention     100.00%   PASS
S3b Relation Accuracy             100.00%   PASS
End-to-end Accuracy                94.44%   PASS
High-risk False-Support Count          0   PASS
```

Failure attribution:

```text
S2_INTENT             1
S2_SOURCE             0
S2_SOURCE_HANDOFF     0
S3A                    0
S3B                    0
```

Seventeen of eighteen tasks therefore completed the entire chain with all preregistered decisions correct.

### Live DailyMed sidecar

The existing real-network DailyMed test also passed in the same workflow:

```text
n tests                                   3
source availability                   100%
current-version consistency            100%
critical-passage Recall@1              100%
critical-passage Recall@3              100%
infrastructure failures                   0
release gate                           PASS
```

This sidecar is not used to inflate the 18-item controlled chain score. It is reported separately because it tests a different failure mode: current external source retrieval/versioning rather than semantic handoff.

### Combined gate

```text
controlled joint handoff               PASS
S2 live DailyMed sidecar               PASS
S3a independent fresh precondition     PASS
S3b independent fresh precondition     PASS
combined release                       PASS
```

Raw results are permanently stored under:

`medical/stage-evals/S2S3/runs/s2-s3-joint-v01-first-run/`

This first observation must not be overwritten or relabeled after future development.

---

## 4. The one observed failure: negated S2 intent feature

`S2S3-013` intentionally asked for general medical evidence and explicitly said the task did **not** involve regulatory information, product labels, or trial registration.

The current S2 router still predicted:

```text
TRIAL_REGISTRY_STATUS
```

because its feature detector currently performs positive substring matching. The phrase `试验注册` is detected even when it occurs inside a negated construction such as `不涉及……试验注册`.

This is a real S2 capability defect:

> **negated intent feature is treated as positive routing evidence.**

It should be represented as a scope problem rather than patched with one Chinese phrase. A future S2 version should detect feature polarity / exclusion scope before intent scoring.

Importantly, this did not become a high-risk false support in the current test. S3a and S3b both produced the correct semantic/entailment result once an appropriate passage was available, and the end-to-end evaluator still marks the task incorrect because the S2 intent and primary source decisions were wrong.

### Metric caveat

`Source Handoff Accuracy = 100%` means the controlled selector eventually found the expected source somewhere in S2's ranked source list and available document bank. It does **not** erase the wrong top-ranked source on `S2S3-013`; that error is separately captured by Primary Source Accuracy and End-to-end Accuracy.

Future joint suites should include more distractor documents corresponding to plausible second/third source choices so source-ranking degradation is even harder to mask.

---

## 5. What this result now supports

The evidence stack is now:

```text
S2 v0.3 independent routing       CONDITIONAL PASS
S2 live DailyMed retrieval        PASS on current 3-case slice
S3a v0.5.6.1 independent fresh   PASS
S3b v0.3 independent fresh        CONDITIONAL PASS / 40 of 40
S2→S3 joint vertical slice        PASS / 17 of 18 end-to-end
high-risk false support           0
```

This is enough to retire the previous claim that S3 is an unconditional `HARD FAIL`.

A more accurate status is:

> **S3 = CONDITIONAL PASS on the current controlled free-text → proposition → entailment vertical slice.**

This does not justify unrestricted automatic medical truth ingestion. The joint test uses a controlled source passage bank for most source families, and the real-network passage test is currently only the DailyMed three-case sidecar. Broader real-source passage retrieval, terminology normalization, long/noisy documents and a dedicated S4 ingestion evaluation remain missing.

Therefore:

```text
S2                               CONDITIONAL PASS
S3a                              CONDITIONAL PASS / independent fresh
S3b                              CONDITIONAL PASS / independent fresh
S2→S3 controlled vertical slice  PASS
S3 overall                       CONDITIONAL PASS
S4 automatic KG ingestion        STILL BLOCKED
```

---

## 6. Next priority

The next S2-focused repair should be a **negation-aware intent router**:

```text
feature mention
→ local scope / polarity
→ positive feature vs excluded/negated feature
→ intent scoring
→ source ranking
```

Then run a new S2 held-out stressing:

- `not X / 不涉及 X / 不要 X` source exclusions;
- positive and negative source constraints in the same query;
- fallback literature requests containing regulator/trial words only as exclusions;
- multiple candidate source families;
- source top-1 vs acceptable top-k separation.

After that, the most valuable broader system proof is a larger real-source S2→S3 passage-level held-out rather than further tuning S3 on the current controlled ontology.
