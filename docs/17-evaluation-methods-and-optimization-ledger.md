# GroundSignal Medical — 评估方法与优化结果总账

> Updated: 2026-09-06  
> Scope: GroundSignal Medical 10-stage system  
> 原则：**平均分用于描述能力，hard gate（硬门禁）用于决定是否允许下游信任。二者不能互相替代。**

## 1. 术语表

- **CI — Continuous Integration（持续集成）**：自动执行 evaluator、回归和历史证据保护。CI 绿色不等于临床验证。
- **Held-out（留出集）**：不参与当前实现调参的数据。
- **Fresh held-out（全新留出集）**：实现先冻结，之后才创建 evaluator/案例/攻击组合；首次结果永久保留。
- **Exposed regression（已暴露回归）**：已经见过并用于修复的失败集，只证明旧漏洞没有回来，不能证明未知泛化。
- **Hard gate（硬门禁）**：高风险错误、数据泄漏、身份/来源完整性等不可由平均分抵消的条件。
- **Gold review（专家金标准审核）**：独立的人类/专家批准层；结构性测试 PASS 不等于 gold approved。
- **TOCTOU — Time Of Check To Time Of Use（检查时与使用时竞态）**：校验对象和实际使用对象之间发生替换，导致“校验的是 A，使用的是 B”。
- **NFC — Normalization Form C（Unicode 标准组合规范化）**：把视觉/语义等价但编码方式不同的字符统一为规范形式，用于稳定身份比较。

## 2. 当前采用的评估闭环

```text
stage-specific eval 定义
        ↓
实现 freeze（commit + 关键 Git blob）
        ↓
freeze 后创建 fresh suite
        ↓
正常 baseline / 旧回归前置检查
        ↓
新的 adversarial hard gates
        ↓
首次结果永久保存
   ┌────┴────┐
 FAIL       PASS
  ↓           ↓
报告+taxonomy  bounded evidence only
+stage status   （仍受其他 gate 限制）
  ↓
下一版本结构修复
  ↓
旧失败 exposed regression
  ↓
再次 freeze → 再做全新 fresh
```

关键纪律：fresh FAIL 不能在修复后改名为 fresh PASS；任何失败必须先保存 raw metrics、失败案例和 failure taxonomy；修复优先改身份模型、数据表示、算法或状态机，不按单个案例硬编码。

## 3. 证据等级

从弱到强：

```text
fixture / development check
→ exposed regression
→ post-freeze independent fresh observation
→ repeated fresh evidence across new failure families
→ real-source + human/Judge calibrated + real-model evidence
→ production / clinical validation（当前没有声称达到）
```

因此“100%”必须带上测试范围。一个 20/20 的 synthetic fresh slice 不能解释为整个医疗系统 100% 正确。

## 4. 10-stage 评估现状

| Stage | 主要评估对象 | 当前最强证据 | 状态与缺口 |
|---|---|---|---|
| S1 User Need / Workflow Discovery | 用户问题、风险频率、真实工作流 | 48 seed tasks + high-risk matrix + user-research plan | Partial；没有真实访谈/日志频率证据 |
| S2 Knowledge Search & Source Routing | 意图路由、来源选择、检索 | v0.3 fresh routing 91.7%；S2→S3 94.44%；DailyMed 3/3 | CONDITIONAL PASS；v0.4 negation/exclusion development FAIL 暴露，真实来源覆盖仍小 |
| S3a Proposition Extraction | 原子医学命题抽取 | fresh F1 98.90%；critical recall 100%；mandatory abstention 6/6 | bounded CONDITIONAL PASS；长/噪声/多源文本不足 |
| S3b Evidence Relation | 支持/反驳/证据不足关系 | 40/40，relation accuracy 100%，high-risk false-support 0 | bounded CONDITIONAL PASS；需扩大真实来源 |
| S4 Medical KG Construction / Update | 知识图谱时间状态、冲突、不变量 | 首次 fresh 18/20 FAIL；修复后新 fresh 20/20 PASS；must-reject 7/7 | CONDITIONAL PASS；persistent real-source graph 未证实，production ingest disabled |
| S5 Controlled Case / Benchmark Factory | benchmark 分区、gold、训练导出、身份/来源/血缘 | v0.2→v0.8 七轮独立 fresh 找到 F4–F31；v0.8.1 扩展开发矩阵阻断 18/18 污染并放行 18/18 clean | **RELEASE BLOCKED**；明确冻结后再做独立 fresh；gold review 仍未完成 |
| S6 Model / RAG / Agent Harness | 模型/检索增强生成/Agent 运行可复现与证据注入 | runner + fixture + CI scaffold | 不能正式推进 dedicated S6 release eval，因 S5 未 bounded release |
| S7 Evaluation & Safety Gate | rubric、多层评分、安全门禁 | protocol + rubric v0.2 + regression gate | 缺 human/Judge calibration 与真实模型 scoring |
| S8 Failure Diagnosis | 错误聚类、根因、干预路由 | taxonomy + intervention router | 缺 multi-model × multi-case failure clusters |
| S9 Intervention / Post-training Data | SFT/preference/Agent/Judge 干预数据 | schema/interface + S5 export boundary | 未做真实训练实验，不声称收益 |
| S10 Candidate + Held-out Regression | 干预后未知集提升与安全回退 | candidate-vs-baseline fixture + held-out contract | 缺真实 post-intervention held-out improvement |

## 5. 已经发生的关键优化

### S3：从“检索到文本”升级为“命题级可验证证据”

S3 把判断拆成 proposition extraction（命题抽取）与 structured entailment（结构化支持关系）。除 accuracy 外，还把 critical proposition recall、mandatory abstention 和 high-risk false-support 作为独立安全指标。当前 S3a fresh F1 98.90%、critical recall 100%，S3b 40/40，S2→S3 joint 17/18。

### S4：从静态图谱升级为 truth ledger（事实状态账本）

S4 的第一次独立 fresh 为 18/20 FAIL。修复后旧 fresh 作为回归达到 20/20，同时新 independent fresh 20/20，must-reject 7/7、stale ACTIVE 0、invariant violations 0。核心变化是把时间、冲突和状态转移变成可执行不变量，而不是只增加知识条目。

### S5：从“防止 held-out 导出”逐步升级到完整 authority chain（权威链）

```text
v0.1   F1–F3    split/export provenance, gold readiness, decision contract       FAIL
v0.2   F4–F7    provenance authority, fail-closed split, payload, exemption       fresh FAIL
v0.2.1           repair                                                           exposed PASS
v0.3   F8–F11   location laundering, self-auth digest, suite/manifest identity    fresh FAIL
v0.3.1           trust-root repair                                                 exposed PASS
v0.4   F12–F15  caller policy, off-repo root, cross-suite id, alternate root      fresh FAIL
v0.4.1           authenticated policy registry                                     exposed PASS
v0.5   F16–F19  payload-after-load, bearer context, namespace, family escape      fresh FAIL
v0.5.1           exact payload + namespace + family containment                    exposed PASS
v0.6   F20–F23  derived lineage, Unicode identity, registry/source TOCTOU         fresh FAIL
v0.6.1           semantic lineage + NFC identity + atomic authority snapshot       exposed PASS
v0.7   F24–F27  cross-split/paraphrase/partial lineage/NFKC identity              fresh FAIL
v0.7.1           deterministic F24/F27 repair                                      partial repair
v0.7.2           record/field/span hybrid + exporter validation                    exposed PASS
v0.7.3           protected-exclusive index + broader calibration                   development PASS
v0.8              cross-language/abstraction/field-flattening/mosaic                fresh FAIL
v0.8.1            36-case multilingual + mosaic development matrix                   development PASS
```

S5 目前已经形成的防线：

- `heldout` / `regression` 默认不可导出训练数据，missing/unknown authority fail closed；
- materialized benchmark payload 必须能从受信 source 重建；
- caller-supplied policy 不能自封为权威，exporter 只接受 pinned registry 中认证策略；
- suite → family root → manifest → source case 均绑定 canonical path 与 Git blob；
- ordinary source 绑定 exact file、payload、case_id、path 与 payload digest；
- family case path 必须位于精确 declared family directory；
- v0.6.1 新增 Unicode NFC canonical identity；
- v0.6.1 新增跨 benchmark/ordinary 的 semantic-core lineage fingerprint，防止仅换 ID/标题/外层字节的 held-out 洗白；
- v0.6.1 新增 atomic byte snapshot：受信 JSON 的 hash 与 parse 针对同一份内存字节，消除本次测试的 TOCTOU check/read gap；
- v0.7 首次证明精确 semantic-core hash 不能泛化到改写、局部复用和兼容字符身份；
- v0.7.3 显式减去允许 dev 共享模板，只把 protected-exclusive 字段、片段和稀有锚点作为 held-out 血缘证据；
- v0.7.3 在 30 个受保护 reference、45 个 allowed-dev reference、163 个可归因污染变体和 62 个 clean/shared hard negatives 上完成算法、阈值、索引和延迟校准；
- v0.8 在冻结提交之后创建全新 family：F29 语义抽象与 F30 跨字段展开被阻断，但 F28 跨语言被 `ALLOW`、F31 多受保护源拼接仅为 `REVIEW`；
- v0.8 的英文同领域 clean control 也进入 `REVIEW`，因此不能用“把所有 REVIEW 改成 BLOCK”作为无代价修复；
- v0.8.1 在不采用 REVIEW 全阻断的前提下，将 F28–F31 全部阻断并让两个 clean control 回到 `ALLOW`；旧 225-case 开发矩阵维持 163/163 污染阻断、0/62 误拦截和 0/62 clean review；
- v0.8.1 扩展矩阵新增 12 个英→中/日/西翻译污染、6 个带噪声双源拼接和 18 个多语言同领域干净近邻：污染 18/18 阻断，干净 18/18 放行；这些均为 synthetic exposed development evidence，不是 fresh；
- v0.8.1 冻结前清单用 Git blob SHA-1 与 SHA-256 双重固定 22 个实现、兼容依赖和证据文件，22/22 复验通过；清单仍明确 `candidate_frozen=false`，只有获批合并后才能产生正式 freeze commit；
- v0.9 fresh 准入门禁当前返回 `BLOCKED_NOT_FROZEN`；无冻结回执时注入任意 fresh 文件都会 fail-closed，回执还必须证明冻结提交已进入 canonical `main` 且 22 个固定文件逐一匹配；
- 准入门禁新增 11 个确定性对抗状态测试，覆盖畸形/自证回执、不可用或未合并提交、提前写入、控制平面错配、缺失/错配协议和模拟合法转换；11/11 通过，但模拟正路径不构成真实冻结或 fresh 证据；
- 冻结凭证生成器升级为 v0.2 并通过 7/7 状态测试：只有带可追溯用户批准引用、位于 `origin/main` 精确 tip、22/22 候选文件与 9/9 控制平面文件均匹配的提交才能生成凭证；测试均为模拟过程证据，当前没有真实凭证；
- 独立固定 9 个控制平面文件（fresh 准入、冻结凭证生成器、测试、证据和校验器），Git blob SHA-1 与 SHA-256 均匹配，9/9 路径和 10/10 状态边界通过；这仍是冻结前开发证明，不是 fresh PASS；
- canonical 冻结凭证现将两份证明绑定到同一个 `main` 提交；旧版或只固定候选、不固定控制平面的凭证会 fail-closed，避免算法未漂移但授权门禁已被替换；
- 每次 fresh first observation 用 Git blob/历史 commit 固化，不会因修复被覆盖。

## 6. 我们现在的“优化结果”应该怎样解读

最重要的结果不是 S5 分数越来越高，而是**模型/系统需要做的科学与工程判断节点越来越多，并且错误更难被平均分掩盖**：

1. 判断来源是否有权威；
2. 判断 authority 是否被外部信任根认证；
3. 判断 suite/family/manifest/source 的身份链是否一致；
4. 判断 payload 是否与来源一致；
5. 判断 partition 是否允许训练；
6. 判断 case identity 是否规范化且唯一；
7. 判断内容是否实际上来自 benchmark 血缘，即使文件字节和 ID 不同；
8. 判断校验和使用是否基于同一份数据快照；
9. 独立判断 gold review 是否完成；
10. 所有已知失败修完后，再面对新的 fresh attack。

这比单纯“增加难例”更接近真实系统可靠性研究：每个决策都可能改变下一步能否信任数据、评分或训练输出。

## 7. 当前结论与下一轮

```text
S3 bounded conditional evidence          established
S4 bounded independent evidence          established
S5 v0.7 independent fresh                FAIL (immutable)
S5 v0.7.3 development calibration        PASS (not fresh)
S5 v0.8 independent fresh                FAIL (immutable: F28/F31)
S5 v0.8.1 exposed repair                 PASS (not fresh)
S5 bounded independent release           NOT ESTABLISHED
S5 gold review                           INCOMPLETE
S6 automatic trust                       BLOCKED
```

v0.8 首次 fresh FAIL 已永久保存，v0.8.1 只能作为 exposed repair evidence。扩展开发矩阵已完成并达到预设门槛，下一步是明确冻结候选实现；冻结后还需要另一轮真正独立 fresh。Gold review 仍是另一条独立门槛。

本仓库当前没有真实用户验证、专家 gold approval、模型训练收益或临床验证数据时，均明确记录为“没有”，不会用 synthetic/CI 结果替代。
