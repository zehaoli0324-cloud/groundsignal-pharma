# Obsidian 使用指南（通用）

1. 用 Obsidian 打开仓库根目录（`pharma/` 或 `demo/`）作为 vault
2. 图谱视图（Graph View）查看实体关系
3. 每个实体文件 = 一个节点；`[[wikilink]]` = 关系边
4. frontmatter 的 `evidence` 字段是证据等级（VERIFIED/SUPPORTED/INFERRED/UNKNOWN）
5. 变更日志在 `07-变更日志/`；证据审计报告在 `05-证据审计/`（pharma）或 `08-证据审计/`（demo）
6. 生成看板：`python3 scripts/ask.py <vault> "实体名" -o board.html`
