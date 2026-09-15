# GroundSignal Clinical Benchmark Design Framework V3.1

这套图册把临床 Agent Benchmark 组织为六个一级模块：

```text
临床世界
→ 实验网络
→ 测量仪器
→ 执行与复现
→ 对抗验证
→ 能力与部署边界
```

核心对象不是一道孤立医学题，而是可证伪、可复现、可被攻击验证的错误实验网络。

## 完整题量公式

出题空间是稀疏张量，而不是固定三个 hypothesis：

```text
N = Σ n(s,m)
```

- `s`：6 个 process stages；
- `m`：Decision / Algorithm / Engineering 三个归因层；
- `n(s,m)`：该 stage × mechanism 格子中实际存在的错误类型数；
- 不存在的组合记 0。

每个错误类型配置：

```text
5 个成组对照 + 6 个 pressure axes × 5 个 levels = 35 planned slots
```

若六条压力轴共享同一个 L0 基线，则为：

```text
5 + 6 × (5−1) = 29 unique prompts
```

每个错误类型使用 `I=3` 个 genuine sibling clinical instances 时：

```text
Q_slots  = 105N
Q_unique = 87N
```

只要总错误类型 `N≥10`，计划实验槽位就超过 1000；`N≥12` 时，即使共享 L0 去重，独特题面也超过 1000。

## 稠密网络示例

如果 6×3 的所有格子都非空：

- 每格 1 个错误类型：`N=18`，1890 planned slots，1566 unique prompts；
- 每格 2 个错误类型：`N=36`，3780 planned slots，3132 unique prompts；
- 每格 3 个错误类型：`N=54`，5670 planned slots，4698 unique prompts。

每题运行 3 次时，对应 5670、11340、17010 episodes/模型。run/seed、对话 turn 和 checker judgment 都不算新题。

## 72 的正确定位

旧版：

```text
3 hypotheses × 3 sibling instances × 8 variants = 72
```

只是一条 H1–H3 最小 Pilot 切片，用于先校准测量仪器；不是完整 process-stage × mechanism × error-type 网络总题量。

## 图册结构

- `00-高度概括总图.svg`：六模块总框架。
- `01-题量计算与单位.svg`：稀疏错误网络与千题级计算。
- `02-临床旅程与失败假设.svg`：患者旅程、过程链和 H1–H3 示例。
- `03-因果实验网络.svg`：Estimand、C0–C4、六压力轴×L0–L4、G0–G7。
- `04-测量仪器与临床治理.svg`：Oracle、Rubric、Verifier、版本和治理。
- `05-红蓝紫攻防与极限测试.svg`：攻击面、防线、紫队证据闭环。
- `06-准入门与边界输出.svg`：工程、科学、临床三道准入门。

## 关键边界

- 精确总题数必须在冻结 `n(s,m)` 错误类型清单后计算。
- 不能为了填满 6×3 矩阵制造不存在或不可裁决的错误类型。
- 六个是 pressure axes，五个是每轴的 levels；axis interaction 是另一个 factorial 实验。
- 当前仓库 artifact 仍是 1 hypothesis、1 clinical instance、8 variants。
- clinical approval 只能由真人临床审核者签署。
- 工程 PASS、科学 Pilot PASS 和临床部署准入必须分开。

## 公开边界

本目录只包含公开方法框架，不包含 author truth、隐藏病例答案、Oracle 明细、Rubric 阈值、patient-level 隐私数据或未公开 attack fixture。

## 构建与验证

```bash
python3 scripts/build_v3.py
```

脚本生成 SVG、HTML 索引和题量说明。SVG 是纯矢量，文字保持为可编辑 `<text>`。
