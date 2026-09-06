# S3a v0.5.6.1 Frame/Event Registry Reconciliation — Independent Fresh PASS

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Version: `s3a-compositional-frame-v0.5.6.1`  
> Parser commit: `4b7aaabe490e3e477d1d1441b55c5ee656675e1f`  
> Parser blob SHA: `dc05a6eaccf02592652d0a48b9a712186e5b6507`  
> Exposed-development workflow: `34003954688`  
> Development raw preservation commit: `5726085158892af66892032ca078c49ea5433c87`  
> Fresh-suite freeze commit: `2147ee2d519305ba2bb2be0576a2e316e405b71f`  
> Fresh-suite blob SHA: `d24ddd0d1de4e5574024bd44f7f1764f1d9382c5`  
> Fresh workflow source commit: `ce211d57253c81ba627dad3b62fd9722e3343501`  
> Fresh first-run workflow: `34004097408`  
> Fresh raw preservation commit: `53f3fde6e8f2ef47975956b5e33c14e047a21a22`  
> Dataset SHA-256: `1d6b8e5fa9c10702618e1421fd0b600df49e6f573b51411acff355cdf5b995d2`  
> Status: **INDEPENDENT FRESH PASS**

## 术语表

- **Fresh held-out（新鲜留出集）**：实现冻结后才定义、首次观察永久保存的独立测试集。
- **Typed reference graph（类型化指代图）**：把 `same value`、共享前置条件等指代关系按标量、范围、阈值等类型约束后再链接。
- **Endpoint discourse state（终点篇章状态）**：把前一句声明的试验终点实体安全传递到相邻句的 `the endpoint / the outcome` 指代，再解析证据和否定作用域。
- **Critical Proposition Recall（关键命题召回率）**：安全或决策关键 gold proposition 被正确抽取的比例。
- **Abstention（弃权）**：遇到当前封闭本体无法安全表达的高风险语义时拒绝生成机器真值。
- **High-risk false positive（高风险假阳性）**：不足或负向证据被错误升级成正向临床/研究结论。

---

## 1. Development gate before fresh

v0.5.6 first introduced typed reference compatibility and endpoint discourse state. Its proposition, abstention and trace gates passed, but the semantic safety gate found one remaining conditional-rule broadening caused by inconsistent event registries.

That first v0.5.6 development FAIL was preserved in:

`medical/stage-evals/S3/S3A_V0.5.6_DEV_FAIL_REPORT.md`

v0.5.6.1 then reconciled realized management frames with the event registry. The repair remained structural:

```text
semantic frame recognized
→ map frame back to sentence/event ownership
→ attach shared preposed condition only if target-compatible
→ run scalar/range/threshold reference compatibility
→ run local non-renal variable veto
→ retain endpoint discourse state
→ compile propositions
```

No benchmark item IDs are used in parser logic.

The v0.5.6.1 exposed development workflow `34003954688` passed all four gates:

```text
all exposed proposition suites       PASS
abstention safety                    PASS
semantic safety error gate           PASS
trace contract                       PASS
combined development release         PASS
fresh validation                  NOT RUN
```

Only after this pass was the new fresh suite frozen.

---

## 2. Freshness contract

The fresh suite contains 34 controlled capability cases:

```text
known / representable cases        28
mandatory abstention cases          6
```

It was authored after the parser was frozen. The workflow verified before first execution:

```text
parser commit      4b7aaabe490e3e477d1d1441b55c5ee656675e1f
parser blob        dc05a6eaccf02592652d0a48b9a712186e5b6507
suite freeze       2147ee2d519305ba2bb2be0576a2e316e405b71f
suite blob         d24ddd0d1de4e5574024bd44f7f1764f1d9382c5
safety evaluator   419bd6f0af79ba3b8665ff5dc09995c9f37d4e82
```

The suite stresses newly worded combinations of:

- shared preposed eGFR conditions;
- finite-verb event morphology such as `initiate`;
- scalar/range reference compatibility;
- non-renal local variable conflict vetoes;
- cross-sentence population continuity;
- endpoint declaration / achievement / evidence-for-achievement separation;
- cross-sentence endpoint anaphora;
- causality and incidence boundaries;
- guideline currentness and supersession;
- trial support and association direction/polarity;
- diagnosis classification;
- unsupported high-risk pharmacogenomic, physiologic, interaction and compound management rules.

This is controlled synthetic capability data. It is not real user data, clinical validation, training data, or expert-reviewed clinical gold.

---

## 3. Immutable first fresh observation

### Proposition extraction

```text
gold propositions                         45
predicted propositions                    46
true positives                            45
Precision                              97.83%   PASS
Recall                                100.00%
F1                                     98.90%   PASS
Critical Proposition Recall           100.00%   PASS
Polarity Accuracy                     100.00%   PASS
Population Accuracy                   100.00%   PASS
Condition Binding Accuracy            100.00%   PASS
```

There were no missing gold propositions.

The only extra prediction occurred in `S3A561F-016`:

```text
The registry lists a prespecified primary endpoint,
but no efficacy result is posted.
```

Gold required only the endpoint declaration. The parser additionally emitted a conservative negative evidence proposition indicating that endpoint achievement is not established.

This lowers precision slightly but does **not** create a positive endpoint-success escalation and does not trigger the high-risk false-positive gate.

### Abstention safety

```text
mandatory abstention cases               6
correct mandatory abstentions             6
required-abstention accuracy         100.00%   PASS
known representable cases                28
known false abstentions                    0
known-case abstention rate             0.00%   PASS
```

### Semantic safety error gate

```text
mandatory silent non-abstention           0
mandatory partial truth emission          0
high-risk semantic false positives        0
Safety error gate                      PASS
```

### Trace contract

The fresh workflow also passed the required trace contract. Every output preserved scope nodes, semantic frames, proposition output, abstention state and non-empty frame provenance/scope trace.

### Combined release

```text
proposition gate                    PASS
abstention gate                     PASS
semantic safety error gate          PASS
trace gate                          PASS
combined fresh release              PASS
```

Raw first-run outputs are permanently stored under:

`medical/stage-evals/S3/runs/s3a-v0561-fresh-first-run/`

From this point forward this suite is exposed regression data and must not be described as fresh again.

---

## 4. Interpretation

This is the first independent fresh S3a result in the current lineage that passes the preregistered proposition, abstention, semantic-safety and trace gates simultaneously.

It supports the following narrower claim:

> The current deterministic S3a prototype can reliably map the tested controlled free-text semantic families into the current canonical proposition ontology, including shared scope, typed reference compatibility, endpoint discourse state and conservative abstention.

It does **not** establish unrestricted clinical free-text extraction. Important untested or under-tested areas still include broader clinical terminology, long documents, tables, cross-document coreference, multiple drugs/interventions in one passage, richer temporal relations, dosage arithmetic, and real-world noisy source text.

---

## 5. Release consequence

S3a may now move from `HARD FAIL` to:

> **CONDITIONAL PASS — independently fresh-validated controlled semantic extraction prototype.**

S3b remains independently `CONDITIONAL PASS` on structured propositions. Therefore the next required proof is an end-to-end / cross-stage vertical slice in which S2 routing/source handoff feeds free text into S3a and then into S3b without gold propositions inserted between stages.
