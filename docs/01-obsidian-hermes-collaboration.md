# Hermes × Obsidian 协作方式（通用）

Agent 直接通过文件系统读写 Obsidian vault（无需插件）：

- 读：`read_file`；写：`write_file`（自动建父目录）；改：`patch`；搜：`search_files`
- wikilink 规则：关系一律 `[[文件名]]`；重名用全路径 `[[01-实体/礼来]]`
- wikilink 不放 frontmatter 和代码块（图谱不渲染）
- 文件名避开 `&`/`/`/`?`
- Obsidian URI 打开：`powershell.exe -Command "Start-Process 'obsidian://open?vault=<VaultName>&file=00-总目录'"`
