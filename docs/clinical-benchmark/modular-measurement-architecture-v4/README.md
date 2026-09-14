# GroundSignal Modular Measurement Architecture V4

GroundSignal 不是静态题库，而是把临床世界、交互协议、实验条件、模型执行与模块化测量组合起来的测量编排系统。

## 核心分层

1. Clinical Scenario：患者完整事实世界。
2. Interaction Protocol：运行前的披露、分支和终止规则。
3. Execution Spec：决定模型实际看到什么、能做什么及是否必须新运行。
4. Episode / Observed Trajectory：一次真实模型执行产生的行为证据。
5. Evaluation Task：希望测量的能力问题。
6. Failure Probe：把能力问题落实为具体可观察失败条件。
7. Verifier Bundle：对一个 probe 执行多个原子判定。
8. Experiment Result：跨条件、病例和运行形成的有限范围结论。

## 关键 many-to-many 关系

- 一个 trajectory 可被多个 task/probe 读取。
- 一个 task 可组合多个 probes。
- 一个 probe 可调用多个 verifiers。
- 一个 verifier 可被多个 probes 参数化复用。
- 只新增后台 probe/verifier 可以重评旧 trajectory，不新增模型行为。
- 改变模型可见输入、交互规则、工具或 condition，必须产生新 execution spec 并重新运行。

## ID 补充

原七个 ID 应至少补充：

- `task_id`：原对象模型定义了 Evaluation Task，但七 ID 中缺失；
- `protocol_id`：交互协议不是实际 trajectory；
- `execution_spec_id`：执行复用与重新运行的判据；
- `episode_id/run_id`：每次独立运行；
- `model_config_id`：模型、system prompt、tools、RAG 和 decoding 的联合身份；
- `judgment_id`：某个 verifier invocation 的版本化裁决。

## 数量账本

不再只报“题目数”，至少分开：

- `N_scenario`：独立患者世界数；
- `N_execution_spec`：唯一模型可见执行条件数；
- `N_episode`：实际模型运行数；
- `N_probe_template`：通用探针定义数；
- `N_probe_binding`：探针在病例/节点/条件上的合法绑定数；
- `N_judgment`：原子 verifier 裁决数。

联调例：1 scenario × 1 protocol × 2 conditions × 2 model configs × 3 repeats = 12 episodes。每场挂3个 probes，得到36个 probe-result positions；若每 probe 平均调用2个 verifiers，则得到72个 atomic judgments。它仍然只有1个患者世界、12次模型运行。

## 图册

- `00-模块化测量总图.svg`
- `01-对象模型与ID.svg`
- `02-Task-Probe-Verifier多对多.svg`
- `03-数量账本与运行复用.svg`
- `04-编排与双清单.svg`
- `05-双闭环与失败路由.svg`

## 公开边界

本目录只含架构方法，不含 patient truth、Oracle 明细、Rubric 阈值、隐藏答案、真实患者数据或未公开攻击夹具。clinical approval 仍只能由真人临床审核者签署。
