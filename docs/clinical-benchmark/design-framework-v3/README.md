# GroundSignal Clinical Benchmark Design Framework V3

这套图册把临床 Agent Benchmark 组织为六个一级模块：

```text
临床世界
→ 实验网络
→ 测量仪器
→ 执行与复现
→ 对抗验证
→ 能力与部署边界
```

其核心主张不是“增加医学题目数量”，而是把每个 failure hypothesis（失败假设）建设成可证伪、可复现、可被攻击验证的实验网络。

## 当前题量建议

脑卒中 reference family 当前目标为 **72 个受控 query**：

```text
3 hypotheses × 3 sibling clinical instances × (7 core variants + 1 P4 interaction) = 72 queries
```

每个 query 独立运行 3 次，即 216 episodes/模型；若比较两个模型，则为 432 episodes。

这里的 run/seed、对话 turn 和 checker judgment 都不是新题，不能用于虚增题量。

## 图册结构

- `00-高度概括总图.svg`：六模块总框架。
- `01-题量计算与单位.svg`：72 query 的口径与三级规模。
- `02-临床旅程与失败假设.svg`：患者旅程、过程链和 H1–H3。
- `03-因果实验网络.svg`：Estimand、C0–C4、P0–P4、G0–G7。
- `04-测量仪器与临床治理.svg`：Oracle、Rubric、Verifier、版本和治理。
- `05-红蓝紫攻防与极限测试.svg`：攻击面、防线、紫队证据闭环。
- `06-准入门与边界输出.svg`：工程、科学、临床三道准入门。

## 每个 hypothesis 的核心题组

```text
C0/P0  基线
C1/P1  弱目标压力
C1/P2  中目标压力
C1/P3  强目标压力
C2     阴性对照
C3     阳性对照
C4     救援/反转
```

P0 已由 C0 承担，不重复计算。P4 是两个已独立验证的压力轴组合，只用于估计 interaction（交互效应）。

## 关键边界

- 72 是设计目标，不是已完成题数，也不是统计功效结论。
- 当前仓库 artifact 仍是 1 hypothesis、1 clinical instance、8 variants。
- 当前 8 variants 不能冒充 8 个独立病例，也不能直接宣称已满足 V3 七臂合同。
- 图中 C0–C4、G0–G7 和红蓝紫攻防是在原设计纲要基础上的形式化增补。
- clinical approval 只能由真人临床审核者签署。
- 工程 PASS、科学 Pilot PASS 和临床部署准入必须分开。

## 公开边界

本目录只包含公开方法框架，不包含：

- author truth；
- 隐藏病例答案；
- Oracle 明细；
- Rubric 阈值；
- patient-level 隐私数据；
- 未公开 attack fixture。

## 构建与验证

运行：

```bash
python3 scripts/build_v3.py
```

脚本生成 SVG、HTML 索引和题量说明。SVG 是纯矢量，文字保持为可编辑 `<text>`。
