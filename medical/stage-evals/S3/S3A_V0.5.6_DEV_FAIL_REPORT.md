# S3a v0.5.6 Typed Reference Graph + Endpoint Discourse State — Development FAIL

> **S3a = Semantic Proposition Extraction（语义命题抽取）**  
> Version: `s3a-compositional-frame-v0.5.6`  
> Parser last-change commit: `ad17cc07f38206dd943b32a4c2abf4e95ca1ce10`  
> Workflow source commit: `1df0c2a828b779938f8e6507b2970eac2f85df4a`  
> Workflow: `34003837565`  
> Raw-result preservation commit: `2fe0239300a263c5bb25c7a50958b7ad1f41f733`  
> Status: **DEVELOPMENT FAIL — fresh validation NOT RUN**

## 1. Evaluation contract

No new fresh held-out was created. All historical fresh results and historical gold remain unchanged. v0.5.6 was evaluated only on previously exposed suites. The v0.5.5 semantic safety evaluator was reused unchanged.

Release requires all four development gates:

```text
all exposed proposition suites = PASS
abstention safety              = PASS
semantic safety error gate     = PASS
trace contract                 = PASS
```

## 2. What v0.5.6 changed

v0.5.6 added three structural components:

```text
1. typed reference compatibility for scalar / range / threshold anaphora
2. event-local variable-conflict veto for inherited renal conditions
3. endpoint entity discourse state across adjacent sentences before evidence/achievement arbitration
```

No benchmark item IDs are used in parser logic.

## 3. First development observation

The proposition gate now passes across every exposed suite. In particular:

```text
v0.5.2 exposed
F1                       98.63%
Critical Recall          98.18%
Population              100.00%
Condition                 98.63%
Gate                       PASS
```

The only remaining v0.5.2 mismatch is the already documented historical ambiguity in `S3A52-037`: the antecedent says `below eGFR 42`, while the frozen gold interprets `same eGFR` as `eGFR = 42`. v0.5.6 preserves the antecedent `<42` operator and does not hardcode the benchmark label.

On the v0.5.4 fresh-now-exposed suite:

```text
gold propositions          61
true positives              61
Precision                100%
Recall                   100%
F1                       100%
Critical Recall          100%
Population               100%
Condition                100%
Gate                      PASS
```

The prior cross-sentence endpoint false-positive escalation is fixed.

Abstention remains fully passing on the exposed safety suites, and the trace contract remains passing.

## 4. Why combined release still fails

The unchanged semantic safety evaluator detects one remaining high-risk condition-stripping error in exposed `S3A4-021`:

```text
At eGFR below 25,
patients already taking the drug should discontinue it,
whereas patients being newly started should not initiate it.
```

The first discontinuation event receives `eGFR <25`. The second initiation event is correctly recognized as a separate management proposition but loses the same preposed condition, yielding an unconditional positive `INITIATION_NOT_RECOMMENDED` proposition.

This is unsafe because a conditional critical rule is broadened into an unconditional rule.

### Root cause

This is not a reference-type problem. The second event uses the finite verb `initiate`, while the older event registry used by the shared-condition linker focuses on `initiation / starting / beginning / commencing`. Therefore the semantic frame exists, but the event-node list used for shared-scope linking does not contain the same event.

The architecture is internally inconsistent:

```text
frame recognizer recognizes event
but
scope-link event registry does not recognize event
→ shared condition cannot attach
```

The repair should therefore reconcile frame events with sentence/clause event ownership rather than add an item-specific phrase rule.

## 5. Frozen decision

```text
all exposed proposition suites       PASS
abstention safety                    PASS
semantic safety error gate           FAIL
trace contract                       PASS
combined development release         FAIL
fresh validation                  NOT RUN
```

No new fresh suite may be frozen from v0.5.6.

## 6. Next target

Use **S3a v0.5.6.1 Frame/Event Registry Reconciliation**:

```text
1. derive shared-condition targets from actual management frames as well as event-registry nodes
2. map frame source spans back to sentence ownership
3. apply one preposed typed condition only when target clause has no local variable conflict
4. run typed reference compatibility after this reconciliation
5. retain endpoint discourse state and v0.5.5 semantic safety evaluator unchanged
```

Only if all four exposed gates pass should a brand-new fresh held-out be frozen.
