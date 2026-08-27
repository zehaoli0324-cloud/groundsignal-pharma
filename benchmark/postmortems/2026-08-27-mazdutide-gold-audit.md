# Eval Postmortem — 玛仕度肽 Gold Staleness Audit

**日期：2026-08-27 · 类型：Gold Audit / 评测系统自我纠错**

> 这是 benchmark 的第一次"评测者被评测"。核心教训：**不仅模型会产生 stale knowledge，truth infrastructure 本身也会 stale；专业领域评测不能只校准模型，还必须持续校准 gold。**

## 1. 时间线

| 时间 | 事件 |
|------|------|
| 2026-08-27 13:5x | V2 无证据评测：Codex 答"玛仕度肽 2025 年已获批"，被判为 OVERCLAIM；DeepSeek 答"III 期/未获批"判为正确保守 |
| 2026-08-27 15:xx | 外部审计：信达官方公告 + 经济观察网/36氪/雪球（2025-06-27）确认 NMPA 已批准玛仕度肽（信尔美®）体重管理适应症；新浪财经（2025-09-23）确认 T2D 适应症 2025-09-19 获批 |
| 2026-08-27 | **结论反转**：Codex 基本正确；DeepSeek 是 STALE_KNOWLEDGE；GroundSignal 数据库自身 stale |

## 2. 验证证据（多源交叉，非单一来源）

- 经济观察网 2025-06-27："国家药品监督管理局批准信达生物制药（苏州）有限公司申报的 1 类创新药玛仕度肽注射液（商品名：信尔美®）上市"（www.eeo.com.cn）
- 36氪 2025-06-27：获批用于成人患者长期体重控制（36kr.com）
- 雪球 2025-06-27/07-02："全球首个获批的 GCG/GLP-1 双受体激动剂"
- 新浪财经 2025-09-23：T2D 新适应症获批（finance.sina.com.cn）
- 健康一线：获 NMPA 批准用于成人 2 型糖尿病血糖控制（vodjk.com）

## 3. 结论反转（V2 报告已重写）

| 项 | 原结论（错误） | 修正后（Pilot finding） |
|----|--------------|----------------------|
| Codex"2025 已获批" | OVERCLAIM | **基本正确**（2025-06-27 体重管理 / 2025-09-19 T2D） |
| DeepSeek"III 期未获批" | 正确保守 | **STALE_KNOWLEDGE**（训练截止 2024-10） |
| 行为画像 | DeepSeek 保守 / Codex 激进 | **pilot behavioral hypothesis**：知识新鲜度差异（1 case × 1 item × 单次采样） |
| 系统结论 | GroundSignal 消除 overclaim | **Eval the model → Eval the evaluator → Eval the truth source** |

## 4. GroundSignal 自身 failure（本轮最有价值的发现）

数据库 `玛仕度肽.md` 在审计前：

```yaml
development_status: III 期临床（中国 NDA 已递交）   # ← 过期
evidence: VERIFIED
last_verified_at: 2026-08-27                        # ← 声称 8-27 验证过
source_url: "https://clinicaltrials.gov"            # ← 高质量来源但错误支持
```

**这是一个真实的 Claim-Evidence Entailment 失败：**

```text
source 是高质量来源（clinicaltrials.gov = Tier 0）
        ≠
source 能支持当前这个 claim（"当前未获批"）
```

- ClinicalTrials.gov 可以证明"有 III 期试验"，**不能**证明"当前仍未获 NMPA 批准"
- 节点级 audit（evidence-audit.py）判该节点 VERIFIED（因为 URL 是 Tier 0）→ 但 claim 级是错的
- **节点有 VERIFIED source ≠ 节点里每个 claim 都 VERIFIED**

## 5. 新指标（已加入评测体系）

### Stale Claim Rate（Temporal Truth Validity）

```text
Stale Claim Rate =
  当前仍标为 VALID/VERIFIED、但已被后续 authoritative evidence supersede 的 claim 占比
```

玛仕度肽 case：`development_status = Phase III / NDA` 在 2025-06-27 之后应标 SUPERSEDED（valid_until: 2025-06-27），而不是继续 VERIFIED。

### Claim-Evidence Entailment

不是"这条 claim 有 URL 吗"（Provenance Coverage），而是：

```text
这个 URL 真正支持这条 claim 吗？
```

玛仕度肽 bad case：ClinicalTrials.gov 支持"有 III 期 trial"，不支持"当前未获批"。

## 6. 修复措施（已执行）

1. `玛仕度肽.md`：development_status 更新为已上市（2025-06-27 体重管理 / 2025-09-19 T2D）；旧 claim 保留 + SUPERSEDED 标注；source_url 改为 NMPA
2. 新增事件节点：[[2025-06-27-玛仕度肽获批减重]]、[[2025-09-19-玛仕度肽获批糖尿病]]
3. 更新信达生物实体关系行
4. V2 评测报告结论重写（Pilot finding 1-3）
5. 三 Track 实验设计（A Closed-book / B Frozen-grounded / C Live-grounded）落地
6. benchmark 存档 v0.1（git tag benchmark-v0.1）

## 7. 面试叙事（可直接用）

> "我原本设计了一个无证据条件来测试不同模型是否会 overclaim。第一次分析时我把 Codex 的'2025 年玛仕度肽已获批'判成了 hallucination；随后对 gold 进行外部审计时发现 Codex 实际是对的——问题出在 GroundSignal 中一个标记为 VERIFIED / last_verified_at=2026-08-27 的节点仍保存了过期的 NDA 状态。于是我把问题从 model hallucination 重新定义成 gold staleness + claim-evidence mismatch，并据此增加 temporal validity 和 claim-level provenance audit。"

这个故事证明的不是"会打模型分"，而是：**知道评测系统本身也可能错，并且会去 falsify 自己的 gold。**
