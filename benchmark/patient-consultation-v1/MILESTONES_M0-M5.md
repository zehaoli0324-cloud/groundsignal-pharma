# GroundSignal Benchmark：验证链里程碑（M0–M5）

> **文档性质**：方法论与里程碑定义。非临床验证、非发布声明。
> **撰写日期**：2026-09-13
> **作者修正记录**：本文取代 `BENCHMARK_GAP_MATRIX.md` 中"12→24→72 家族扩容是唯一最高优先级"的判定。
> **依据**：`benchmark/ap07-oracle-draft-v1/`、`benchmark/ap07-oracle-draft-v2/`（实测）、`medical/patient-eval/STAGE_DECOMPOSITION.md`

---

## 0. 方法论修正（重要）

### 被取代的旧判定

> ~~"S5 家族规模 12→24/72 是唯一一个必须做完才能谈完整 benchmark 的任务。"~~

### 修正后的判定

> **当前最高优先级不是扩大病例数量，而是完成一个经临床审核、独立标注、真实模型运行和分歧裁决验证过的最小 Benchmark 闭环。规模化必须建立在该闭环已经证明可测、可判、可复现之后。**

### 为什么

**旧判定的结构性错误**：把 G1–G4 当成四个平行的 checklist，于是"数量"看起来可以独立推进。但真实结构是**验证链**：

```
Oracle 有效 → 测量有效 → 小规模真实运行有效 → 才值得规模化资产
```

在链条未验证前扩规模，是在**复制一个尚未验证的设计**——返工成本随规模线性放大。AP07 现在恰恰是那个"尚未验证的 Oracle 设计"。

**关键区分**：
- 用 AP07 **当母版**（提取模板）—— 正确
- 用 AP07 **当产能铺规模**（先复制 12 份）—— 错误

---

## 1. G1–G4 的正确关系

| 旧表述 | 新表述 |
|---|---|
| 四个平行验收门 | **一条验证链** |
| G1 资产完整 / G2 真值可信 / G3 测量可信 / G4 端到端可跑，并列 | Oracle 有效 → 测量有效 → 真实运行有效 → 才值得规模化 |

```
        ┌─────────────┐
        │ Oracle 有效  │  ← M0：单家族金标准闭环
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │  测量有效    │  ← M1：能否稳定裁决；是否真能制造有意义的压力
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │ 小规模真实   │  ← M4：pilot（相同条件、双人盲评、一致性）
        │  运行有效    │
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │  才值得规模化 │  ← M5：24 → 72
        └─────────────┘
```

---

## 2. 里程碑定义

### M0 — AP07 单家族金标准闭环 ⬅ **当前**

**目标**：完成一个经临床审核、独立标注、分歧裁决的 gold_approved Oracle，作为后续所有家族的标准母版（reference family）。

**清单**（用户定义）：
1. 完整节点表
2. 每个节点只依据当时已暴露信息
3. 必须行动 / 可接受行动 / 必须追问 / 可选追问 / 禁止行为
4. 正回答、边界回答、危险反回答
5. 医学适用条件与例外
6. A/B 两名医生独立填写
7. 不向医生暴露作者预期标签
8. 分歧记录与第三方裁决
9. 最终形成 `gold_approved` Oracle

### M1 — 验证 Oracle 能不能真正测模型

**用 AP07 跑第一批真实模型。重点不是总分，而是验证三个问题：**

| # | 问题 | 若失败意味着 |
|---|---|---|
| 1 | 评分标准是否能稳定裁决 | 测量无效 |
| 2 | 模型是否存在"最终答案看起来正确、过程却危险" | 这正是本 benchmark 的核心价值假设 |
| 3 | 题目是否真的能制造有意义的压力 | 题目区分度不足 |

**纪律**：**如果所有强模型都轻松满分，首先应怀疑题目区分度不足，而不是宣布模型已经解决问题。**

### M2 — 冻结"家族生产模板"

AP07 跑通后，才把它抽象成统一 schema。届时 T3/T4/T5 合并为 **Benchmark Contract v1**，一次冻结：

- 题卡 schema
- 动态披露协议
- Oracle schema
- 评分机会
- 截止节点
- 严重错误 blocker
- 分区规则
- 泄漏规则
- 人工裁决规则

### M3 — 12 家族回填 → 24 开发家族

先把现有 12 个全部迁移到新标准并完成临床审核。**确认没有系统性问题后**，才生产新增 12 个。

> **不要直接从 12 扩到 72。**

### M4 — 第一次正式 pilot

冻结一小批病例，对小荷/通用模型采用**相同条件**运行，双人盲评，计算评分者一致性，做 failure taxonomy，得到第一份真正意义上的 benchmark report。

### M5 — 24 → 72

只有 pilot 已证明"有区分度、可重复、Oracle 可裁决、评分者能一致"以后，72 家族规模才有统计和工程意义。

---

## 3. M0 现状盘点（实测）

### 3.1 核心发现

> **AP07 的作者侧工程已 100% 完成；医生侧 100% 空白。**

`benchmark/ap07-oracle-draft-v2/CLINICAL_REVIEW.json` 的 16 个 review row（N0–N5 + C01–C10）全部：

```json
{
  "reviewer_identity": null,
  "relevant_competence": null,
  "reviewed_at": null,
  "conclusion": null,
  "reason": null,
  "status": "pending"
}
```

**这就是 M0 缺的唯一的、也是最关键的一块：医生填的列。**

### 3.2 M0 清单逐项核对

| # | M0 要求 | 现状 | 载体 |
|---|---|---|---|
| 1 | 完整节点表 | ✅ 已完成 | `NODES.md`（N0–N5）+ `CLINICAL_REVIEW.json`（C01–C10） |
| 2 | 节点只依据当时已暴露信息 | ✅ 已强制 | `known_information.all/none` 字段；`visible_prefix_only` 约束 |
| 3 | 必须行动/可接受/必须追问/可选追问/禁止行为 | ✅ 已分类 | 见 §3.3 |
| 4 | 正回答/边界回答/危险反回答 | ✅ 已完成 | `coordinator_only/author-hypotheses.json`：4 acceptable + 4 dangerous + 4 boundary |
| 5 | 医学适用条件与例外 | 🔶 **字段已建，值全为 null** | `medical_population_and_limits`、`action_timing`、`acceptable_equivalent_routes`、`china_service_path`、`severity_anchors` |
| 6 | A/B 两名医生独立填写 | ✅ **包已备好** | `draft_stage1/{A,B}/review.json`（各 63 blank_rows） |
| 7 | 不向医生暴露作者预期标签 | ✅ **已验证** | `coordinator_only/author-hypotheses.json` 隔离（`expectations_status: author_hypotheses_not_gold`）；实测 A/B 包无 expected/author/gold/label 键 |
| 8 | 分歧记录与第三方裁决 | 🔶 **格式部分具备** | `rule_ambiguity`/`medical_dispute` 字段在；独立裁决格式待补 |
| 9 | 最终 `gold_approved` Oracle | 🔴 **未达** | `CLINICAL_REVIEW.json`：`clinical_approval: false` |

### 3.3 节点覆盖情况（六大类判据）

| 类别 | 节点/判据 | 状态 |
|---|---|---|
| **必须行动** | C04（明确必要行动及紧迫性） | 定义完整，待审 |
| **可接受行动** | C03（位置迁移后及时评估）、C08（可执行安排） | 定义完整，待审 |
| **必须追问** | C01（推进风险判断的澄清） | 定义完整，待审 |
| **可选追问** | C05（不得以不必要问答前置阻碍行动） | 定义完整，待审 |
| **禁止行为** | C02（避免无依据确诊）、C06（不得因延后诉求撤回）、C09（不得把未披露当已知） | 定义完整，待审 |
| **沟通/系统** | C07（回应具体困难）、C10（系统不得强迫续问）、N5（结束资格） | 定义完整，待审 |

**每项判据均含"通过/失败/不适用"三档 + 依据定位** —— 结构完整。

### 3.4 A/B 双医生包状态（实测）

| 项 | A | B |
|---|---|---|
| stage1 windows | 13 | 13 |
| stage1 blank_rows | 63 | 63 |
| stage2 windows | 1 | 1 |
| stage2 blank_rows | 4 | 4 |
| `submission_status` | `unsubmitted` | `unsubmitted` |
| `released` | false | false |
| 泄漏键扫描 | 无 | 无 |

**盲法与时间盲化**：
- `coordinator_only/blind-map.json`（作者侧，医生不可见）
- `withheld_stage2/`：第二阶段材料单独隔离，`stage2_released: false`
- INSTRUCTIONS.md 明确：*"第二阶段必须由协调人在收到并锁定本评审全部第一阶段原始记录后另行发放"*
- INSTRUCTIONS.md 明确：*"声明既有暴露；不得将看过 v1 标签者称首次盲评"*（v1 已发布，暴露不可逆）

### 3.5 工程验证（实测）

```
command: python3 -m unittest discover -s tests/ap07_revision -v
exit_code: 0
test_methods: 16
result: OK
scope: AP07 v2 material and deterministic helper only; not repository-wide regression
old_version_unchanged: true
clinical_approval: false
AB_actual_ratings: 0
calibration_ready: false
```

16 项测试覆盖（节选关键项）：
- `test_all_six_nodes_and_ten_criteria_have_unsigned_review_rows`
- `test_stage1_has_no_future_and_stage2_is_withheld`
- `test_forged_claimed_coverage_cannot_hide_omission`
- `test_unknown_major_errors_do_not_become_zero`
- `test_changed_rubric_cannot_reuse_rows_under_same_version`
- `test_actual_prefix_not_authored_node_drives_coverage`

---

## 4. M0 剩余工作（按责任方分）

### 🟦 只有医生能做（M0 的关键路径）

| # | 任务 | 载体 |
|---|---|---|
| D-A | 医生 A 填 `draft_stage1/A/review.json` 的 63 行 | 逐行 judgment + evidence + reason |
| D-B | 医生 B 独立填 `draft_stage1/B/review.json` 的 63 行 | 同上，独立进行 |
| D-C | 填 `CLINICAL_REVIEW.json` 的 16 个 row 的临床字段 | `medical_population_and_limits`、`action_timing`、`acceptable_equivalent_routes`、`china_service_path`、`severity_anchors` |
| D-D | 声明身份与资质 | `reviewer_identity`、`reviewer_qualification`、`reviewed_at` |
| D-E | 分歧裁决（若 A/B 不一致） | 需第三方裁决人 |

### 🟨 Hermes 可代做的（不冒充临床）

| # | 任务 | 说明 |
|---|---|---|
| H-1 | 生成医生填写指南 | 基于 INSTRUCTIONS.md 出中文操作说明 |
| H-2 | 建立分歧裁决格式 | 定义 `adjudication.json` schema |
| H-3 | 建立一致性计算入口 | Cohen's kappa（加权线性） |
| H-4 | 泄漏扫描验证报告 | 已初测，出正式报告 |
| H-5 | M1 pilot 运行接口核查 | 预算仍为 0，不实调 |
| H-6 | 本 M0–M5 里程碑文档 | ✅ 本文 |

### 🔴 不可代做

- 填写任何 clinical judgment
- 生成临床 gold
- 冒充医生签名
- `clinical_approval` 状态升级

---

## 5. M0 完成的判据（exit criteria）

M0 视为完成，当且仅当：

- [ ] A/B 两份 stage1 review.json 均已 `submitted`，`reviewer_identity`/`reviewer_qualification`/`reviewed_at` 非空
- [ ] A/B 评分一致率已计算（Cohen's kappa 报告）
- [ ] 不一致项已由第三方裁决并留痕
- [ ] `CLINICAL_REVIEW.json` 16 row 的 `conclusion` 非空（accept / accept_after_revision / insufficient_evidence）
- [ ] 临床适用条件字段（`medical_population_and_limits` 等）已填
- [ ] 规则歧义（`rule_ambiguity`）已显式记录，未用 insufficient 代替
- [ ] `clinical_approval` 由医生显式置 true（**AI 不得代置**）
- [ ] Oracle 标记为 `gold_approved`，可进入 M1

**当前进度：0/8**（结构就绪，医生填写未开始）

---

## 6. 验证边界

- 本文是**方法论与里程碑定义**，非临床验证、非发布声明。
- M0 现状盘点基于实测（读取实际 JSON 文件、运行实际测试命令），非引用。
- 医生侧字段全部为 `null`，照实记录为未完成。
- 未伪造任何 clinical gold、评分、签名或审批状态。
- 未创建任何 cron、未启动任何真实模型调用。
