# 裁决点选页 v0.1

打开medical/patient-eval/adjudication-v0.1.html可以体验合成示例。填写一次协调者编号，查看原文和两份意见，再点选最终答案、理由并确认。原审阅界面的四项默认勾选不变；裁决页需要明确选择最终意见。

页面分别展示已确认分歧、已确认一致、缺答和待确认。只有已确认分歧可以裁决；其他状态保留。常见理由可点选，也可补充文字。编辑已确认项会清除本项确认；切换题目前需要重新确认。

保存的groundsignal-adjudication.json只包含已确认裁决，可以在同一页恢复。输入发生变化后，应重新生成页面；旧裁决文件无法恢复到新的答卷组合。下载、关闭重开、恢复等实际浏览器操作尚未验收，当前验证为程序逻辑与文件互通测试。

## 研究人员准备正式工作页

本版采用“先在本地核验两份答卷，再生成绑定页面”的流程；不支持在浏览器内直接导入任意两份原始答卷。

```bash
python -m scripts.patient_eval.adjudication_page \
  --original /private/original.json \
  --left /private/reviewer-a.json \
  --right /private/reviewer-b.json \
  --out /private/adjudication.html
```

路径是示意，请替换为真实的本地文件。输出必须不存在。生成页面含原资料，继续按原私有资料范围保存；公开交付只包含合成示例。

协调者交回保存文件后，用既有处理程序校验和回写：

```bash
python -m scripts.patient_eval.choice_adjudication \
  --original /private/original.json \
  --left /private/reviewer-a.json \
  --right /private/reviewer-b.json \
  --decisions /private/groundsignal-adjudication.json \
  --out /private/resolved-new
```

后端重新核对原始输入、内容摘要、选项和裁决理由。输出review.json供候选审阅流程读取，result.json保留完整裁决记录，原始两份答卷不变。这不是模型回答评分，也不会自动完成57条规则映射或12条临床裁决。

本轮27项相关测试通过，覆盖前后端文件互通、旧版本与错误输入拒绝、部分裁决不补全、候选摘录展示、页面输出与脚本检查。页面无外部依赖和网络请求，原资料按文本显示。浏览器体验与人工身份、专业判断仍待实际验收。
