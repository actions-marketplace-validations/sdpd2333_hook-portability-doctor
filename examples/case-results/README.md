# 固定版本真实配置案例

以下结果来自配置静态扫描；没有运行第三方 Hook，也没有证明整套插件可在 DSH 中工作。

| 案例 | 固定源文件 | 目标不支持的事件 | 报告 |
|---|---|---|---|
| context-mode | [78d3dd080e4f](https://github.com/mksglu/context-mode/blob/78d3dd080e4f52c9e3a81a63cd7eb369d8bb8d02/hooks/hooks.json) | PreCompact | [Markdown](context-mode/report.md) · [JSON](context-mode/report.json) |
| claude-mem | [02584c4ac9d9](https://github.com/thedotmack/claude-mem/blob/02584c4ac9d92fea45adf5c61e22c546b5738621/plugin/hooks/hooks.json) | PostToolUseFailure、SessionEnd、Setup | [Markdown](claude-mem/report.md) · [JSON](claude-mem/report.json) |
| superpowers | [2ce8aa15d05b](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/hooks/hooks.json) | 未检出 | [Markdown](superpowers/report.md) · [JSON](superpowers/report.json) |

复现：在仓库根目录运行 `python scripts/run_cases.py --fetch`。首次下载固定版本公开 JSON，随后可离线使用缓存。

每份 JSON 报告的 `case_source` 记录来源提交、路径和输入摘要。源 JSON 仅缓存在 `.work/`，不随仓库分发。

[本批次完整计数](summary.json)
