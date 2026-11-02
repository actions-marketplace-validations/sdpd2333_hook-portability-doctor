# 验证记录

## 0.2.0：安装包与 CI 接入

2026-11-03，在 Windows 11 / Python 3.14.8 上完成：

| 检查 | 实际结果 | 复现 |
|---|---|---|
| 行为、skill 安装、Action 适配器 | 59 项测试通过，其中 Action 14 项 | `python scripts/acceptance.py` |
| 源码 CLI | 4 个场景通过 | 同上 |
| wheel / sdist 构建及元数据 | 构建成功，twine 两项通过 | [分发指南](DISTRIBUTION.md) |
| 全新环境离线 wheel 安装与运行 | 60 项断言通过，两个命令入口、仓库外目录 | `python scripts/verify_distribution.py` |
| 固定真实配置案例 | 3 份摘要及预期事件一致 | `python scripts/run_cases.py --fetch` |
| 工作流静态检查 | actionlint 1.7.12 通过 | `actionlint .github/workflows/check.yml` |

[机器可读摘要](v0.2.0-verification.json) 记录本轮范围。详细运行日志在忽略目录
`reports/acceptance/`、`reports/package-verification.json`、`reports/cases/`。
原生客户端未在本轮重跑；下文 0.1.0 记录保留为历史证据。

Ubuntu、Python 3.11 和真实 GitHub composite runner 的任务已加入 CI，
此处不把本机适配器测试视作它们已经通过；具体状态需查看本轮提交的 Actions。

## 0.1.0：历史验证

更新：2026-11-03。检查器 `0.1.0`，本机 Windows 11 / Python 3.14.8 / Node 24.20.0。

| 层次 | 实际结果 | 证据 |
|---|---|---|
| Python 行为和安装测试 | 45 项通过 | [本机数据](local-verification.json) |
| CLI 验收 | 4 个场景通过 | `python scripts/acceptance.py` |
| 三个固定真实配置 | SHA-256 与预期不支持事件一致 | [案例索引](../examples/case-results/README.md) |
| skill 格式 | bundled `quick_validate.py` 通过 | 命名、frontmatter、占位符检查 |
| 当前 Codex 手动读取 skill | 调用检查器并解读报告完成 | 首轮本地验收 |
| Claude Code 2.1.316 原生 skill | 目录发现、Skill 调用、检查器和报告读取通过 | [原生验证](native-clients.md) |
| DSH 0.2.1-rc.5 原生 skill | skill 工具加载、检查器和报告读取通过 | [原生验证](native-clients.md) |
| DSH 自建 Hook | 四种事件实际执行，目录与参数行为符合观察 | [原生数据](native-verification.json) |
| 官方 DSH 桥模块契约 | 八项通过；shell 调用在服务边界截获 | [契约数据](dsh-contracts.json) |

Python CLI 和普通验收只依赖标准库。Node 和锁定 npm 包仅用于可选桥契约检查；格式校验用的 PyYAML 位于忽略目录，不是检查器依赖。

两个客户端处理 `examples/migration-gaps.json` 的副本，得到 3 项不兼容、2 项行为变化、1 项配置待确认、2 项待核对。核验输入摘要和完整 findings 与 CLI 基准一致，不把模型自述的“成功”当作唯一证据。

客户端请求显式提到 skill 名称。原生目录发现和调用已观察到，任意提示词下的自动选择成功率未评估。Codex 原生安装与自动选择尚未测试。

目标桥测试只覆盖指定版本和自建用例，不验证三份第三方插件的完整运行。每次静态扫描中的 `target_runtime_verified`、`execution_verified` 继续为 `false`，它们描述当前扫描输入，而不是开发时的集成测试。

GitHub Actions 配置了 Windows / Ubuntu 的 Python 3.11、3.14 验收，以及 Node 24 的 DSH 契约检查。远程结果以具体提交的 Actions 为准，不以本地结果替代。
