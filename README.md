# Hook Portability Doctor

检查 **Claude Code Hook 配置 → DeepSeek Harness（DSH）Claude Hook 兼容桥** 的静态差异，生成可以追溯到源码的中文报告。

例如：某插件的 `PreCompact` 事件在目标桥中会被忽略；某处理器的 `args`、`async` 配置不会被采用。检查器说明具体位置、影响、证据和下一步，同时把缺少环境信息的事项单独列出。

**交付形态：Python CLI + 可供 AI 调用的 skill。** Python 3.11+，运行时仅用标准库，无需 API Key。版本 `0.1.0`，规则固定于 DSH 提交 `ce7073d51254c26cd63b22a60835b8f948deb447`。检查器不会执行输入中的 Hook 命令。

## 直接验收

在仓库根目录运行：

```shell
python scripts/acceptance.py
```

预期输出：`PASS: 45 tests, 4 CLI scenarios`。打开生成的 `reports/acceptance/ACCEPTANCE.md`，查看四个场景及完整测试日志。此命令离线运行，不要求安装 Codex、Claude Code 或 DSH。

最直观的演示是：

1. 打开 `gaps/report.md`，查看明确不兼容项及被忽略的选项。
2. 比较 `root-unknown/report.md` 和 `root-provided/report.md`：补充实际根目录上下文后，对应提示消失。
3. 打开一份 [真实项目案例](examples/case-results/README.md)，沿报告的证据链接核对判断。

## 检查自己的配置

```shell
python scripts/check_hooks.py "path/to/plugin/hooks/hooks.json" --out reports/my-plugin
```

生成同源的 `report.json` 和 `report.md`。可以直接指定文件，也可以指定插件目录；目录仅检查 `hooks/hooks.json`、`hooks.json`、`.claude/hooks.json`、`.claude/settings.json`、`.claude/settings.local.json`、`settings.json` 六个位置。多个候选会要求指定文件，不自动合并。

支持含 `hooks` 对象的配置、裸事件映射，以及不含 hooks 的 settings 文件。文件名为 `settings.json` 或 `settings.local.json` 且没有 `hooks` 时，按无 Hook 设置处理；裸事件映射请使用其他文件名。只接受 UTF-8 JSON（可带 BOM），不接受 JSONC、重复键或超过 5 MiB 的文件。

显式提供目标环境上下文：

```shell
python scripts/check_hooks.py examples/root-context.json --plugin-root . --out reports/with-context
```

`--plugin-root` 对应目标桥的 `pluginRoot`，`--project-dir` 对应项目目录。存在的目录可以消除相应上下文提示，但不证明脚本、依赖或执行环境正确。扫描输入目录不等于已获知目标插件根目录。

指定规则和严格模式：

```shell
python scripts/check_hooks.py examples/migration-gaps.json --target dsh-claude-bridge --profile dsh-claude-ce7073d --strict --out reports/gaps
```

该示例预期返回 `1`，报告仍然生成。默认输出目录是调用者当前目录下的 `reports/latest`；重复运行会更新报告。输入文件有覆盖保护。

| 退出码 | 含义 |
|---|---|
| `0` | 检查完成；不代表运行兼容性通过 |
| `1` | 使用 `--strict`，且发现 `incompatible` 项 |
| `2` | 输入、参数或输出问题 |
| `3` | 检查器内部错误 |

## 怎么理解报告

| 分类 | 含义 | 例子 |
|---|---|---|
| `incompatible` | 目标规则快照确定会跳过的事件或处理器 | `PreCompact`、非 command 处理器 |
| `behavior_change` | 已知配置选项不被目标采用 | 非空 `args`、`async: true` |
| `configuration` | 需要补充或核对目标配置 | 本次未提供 `pluginRoot` |
| `manual_review` | 需要确认源意图或运行环境 | 工具名 matcher、未知字段 |

每项包含规则 ID、JSON Pointer、确定性、建议和固定提交证据。同类根目录和工具匹配提示会归并成问题组，所有关联位置仍保留；问题组数量不等于处理器数量。

规则覆盖 HP001–HP008，详见 [规则依据](references/rule-evidence.md)。`no_hooks`、`no_handlers` 和 `no_static_differences_found` 是不同结果，均不能当作实际迁移成功。

## 三个真实配置案例

输入固定到提交和 SHA-256。以下数量来自已执行的静态扫描，报告在仓库内可直接阅读。

| 案例 | 事件 / 处理器 | 明确不兼容 | 行为变化 | 配置待确认 | 需要核对 |
|---|---:|---:|---:|---:|---:|
| [context-mode](examples/case-results/context-mode/report.md) | 6 / 14 | 1 | 0 | 1 | 1 |
| [claude-mem](examples/case-results/claude-mem/report.md) | 9 / 11 | 3 | 12 | 0 | 4 |
| [superpowers](examples/case-results/superpowers/report.md) | 1 / 1 | 0 | 1 | 1 | 1 |

- context-mode：检出目标忽略 `PreCompact`。
- claude-mem：检出目标忽略 `Setup`、`PostToolUseFailure`、`SessionEnd`，并定位未被采用的处理器选项。
- superpowers：未检出不支持的事件；仍报告显式 `shell` 选择和上下文、匹配验证事项。因此没有把它标成“完全兼容”。

复现：

```shell
python scripts/run_cases.py --fetch
```

首次显式下载 [案例清单](examples/cases.json) 中固定版本的公开 JSON，校验 SHA-256 后分析，报告写入 `reports/cases/`。后续可省略 `--fetch`，离线使用 `.work/upstream/` 缓存。下载或摘要不符时返回 `2`。第三方配置不随仓库分发，不运行其中命令。

需要更新仓库中的展示报告时：

```shell
python scripts/run_cases.py --fetch --out examples/case-results
```

## 交给 AI 使用

本仓库根目录就是完整 skill 包：`SKILL.md`、`agents/openai.yaml`、脚本、规则和参考文档需要一起保留。

无需安装也可以让具有本地文件和命令工具的助手显式读取：

> 读取这个仓库中的 SKILL.md，按其中的流程检查 examples/migration-gaps.json，报告写到 reports/manual。解释最重要的确定问题和仍需验证的事项，保留报告路径。

也可以安装到另一个项目的 skill 根目录，例如 `python scripts/install_skill.py --skills-dir "<project>/.claude/skills"` 或对应的 `.dsh/skills`。脚本不覆盖已有同名 skill。加载后按客户端方式显式调用。调用端与受检协议分别说明：在 Codex 中调用，并不表示支持 Codex Hook 配置迁移。

已在 Claude Code **2.1.316**、DSH **0.2.1-rc.5** 完成原生 skill 调用与报告生成；DSH 自建 Hook 实际触发了四种事件。另有八项真实桥模块契约检查。复现方式见 [原生客户端验证](docs/native-clients.md)，范围和证据见 [验证记录](docs/verification.md)。第三方插件完整运行仍需分别验证。

## 范围与已知限制

- 首版只有 Claude Hook 配置到指定 DSH Claude 桥这一条路线。规则快照不是用户实际安装版本，也不声称代表上游最新状态。
- 静态检查配置，不解析 shell，不检查第三方脚本内部，不验证 Hook 输出、payload、依赖、正则是否合法及实际工具名称。
- 不合并 Claude 的多层配置，不改写配置，不安装或执行插件。源码支持的默认值及跳过顺序已纳入测试。
- `Stop` 上忽略 matcher 只报告为核对项；源平台可能同样忽略，不能据此断言迁移回归。
- 变量检查关注 `${NAME}` 形式，尤其是目标桥的两个内建替换变量。其他 shell 语法和动态路径继续保留为运行验证事项。
- `--strict` 仅阻断明确不兼容项。行为变化也可能影响业务，但其严重程度需要结合插件意图判断。
- 报告的 `target_runtime_verified`、`execution_verified` 始终为 `false`。候选 command 数量只表示静态结构，不能证明注册或运行成功。

## 开发

```shell
python -m unittest discover -s tests -v
python scripts/acceptance.py
```

可选目标桥验证：`npm ci --prefix integrations/dsh --ignore-scripts --no-audit --no-fund`，随后运行 `node scripts/verify_dsh_bridge.mjs`。这项检查不调用模型；Node/npm 不属于普通 Python 检查器的运行依赖。

GitHub Actions 覆盖 Windows / Ubuntu 的 Python 3.11、3.14 验收和 Node 24 桥模块契约检查；具体提交的状态见仓库 Actions。规则更新要求固定源码版本、检查边界和回归样例，见 [贡献指南](CONTRIBUTING.md)。

项目结构：`scripts/` 为实现，`rules/` 为目标快照，`tests/` 为行为测试，`examples/` 为自建示例与真实案例元数据，`references/` 为证据说明。`reports/`、`.work/` 和缓存均不纳入 Git。

MIT 许可。本工具由独立项目维护，与案例项目及各 AI 客户端无隶属关系。
