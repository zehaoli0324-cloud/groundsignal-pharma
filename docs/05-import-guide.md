# 导入/合并指南（通用）

```bash
python3 scripts/import-helper.py <源库> <目标vault> --check   # 冲突预检
python3 scripts/import-helper.py <源库> <目标vault> --merge   # 执行合并
```

- 同名不同内容 → `企业情报-原名.md` + 内部 wikilink 自动改写
- 同名同内容 → 跳过；用户文件永不覆盖
- 更干净方案：用 ingest.py 的 YAML 在目标 vault 重建
