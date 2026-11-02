# 规则依据与误报边界

核对日期：2026-11-03。唯一规则集：`dsh-claude-ce7073d`。

目标仓库：`deepseek-ai/deepseek-harness`。提交：`ce7073d51254c26cd63b22a60835b8f948deb447`。目标包：`@deepseek-ai/dsh-hooks-claude-code`。

## 一手来源

- [DSH-CONFIG：配置解析实现](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)：`CLAUDE_EVENTS`、`parseClaudeCodeConfig`、`substituteCommand`。
- [DSH-LIMITATIONS：桥接范围与限制](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)：配置字段、事件和运行行为的限制。
- [DSH 目标桥完整说明](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md)：根目录上下文和 matcher 主体。
- [OpenAI skill 文档](https://learn.chatgpt.com/docs/build-skills)：技能组织与调用参考；不是目标桥行为的证据。

规则文件保存证据 ID 与固定链接，JSON 和 Markdown 共享同一次分析结果。源码断言限于该提交；没有用当前 `main` 替换固定基线。

## HP001–HP008

| 规则 | 本工具判定 | 依据与保留条件 |
|---|---|---|
| HP001 | 未识别事件被跳过；空数组仅提示核对 | `CLAUDE_EVENTS` 白名单；未知事件在遍历处理器前已被排除 |
| HP002 | 非 command 处理器不运行 | 解析器的 `type` 分支；缺失或非字符串 type 按 command 处理，空字符串不按默认值处理 |
| HP003 | 指定选项不会被目标采用 | 解析器仅保留 command 与数值 timeout；限制文档列出忽略选项。`async/asyncRewake/once` 只对 true 报行为变化，非空 args 等单列 |
| HP004 | Stop / UserPromptSubmit 的 matcher 被丢弃 | 解析器在 matcher 校验前丢弃它；不主张源平台行为必然不同 |
| HP005 | 内建路径变量需要上下文 | `substituteCommand` 替换 `${CLAUDE_PLUGIN_ROOT}` 和 `${CLAUDE_PROJECT_DIR}`；未提供上下文不等于目标配置缺失 |
| HP006 | 工具 matcher 需要核对目标名称与正则 | 目标对 PreToolUse / PostToolUse 按工具名匹配；仅靠配置无法证明实际命中或失败 |
| HP007 | 局部结构异常会导致条目被跳过 | 事件数组、组 hooks 数组、处理器对象、command 字符串的类型检查；不扩大为所有配置必然失效 |
| HP008 | 字段意图、其他变量或数值等仍需确认 | 结合保留字段和已知限制说明覆盖边界；没有依据时不升级为确定的业务故障 |

目标认可的七种事件为 `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`Stop`、`SubagentStart`、`SubagentStop`。“被认可”只涉及入口，不代表所有 payload、Hook 输出和时序语义都一致。

## 必须保持的区别

- **静态事实与业务影响**：可以确认某字段没有被采用；要确认插件因此失效，还需要源配置意图、脚本和目标运行结果。
- **同步字段与事件调度**：忽略 `async` 不等于所有事件都等待 Hook 完成。部分事件有独立的 detached 调度；报告只指出不保留该字段的后台执行语义和匹配命令串行处理。
- **目标配置与当前机器**：本机存在的根目录仅用于消除上下文提示，不验证脚本是否存在，也不证明另一台目标机器具有同一路径。
- **匹配器检查**：非 runnable 组不检查 matcher。Stop / UserPromptSubmit 不编译 matcher。其他 matcher 可能使目标拒绝整份配置；本工具未执行目标正则引擎，不能用 Python 的正则结果代替。
- **输入规范化与目标宽松行为**：拒绝非对象根节点、非对象 hooks、重复键和非标准 JSON；没有模仿目标对所有损坏根结构的宽松回退。错误明确返回输入问题。

## 可复现证据

[案例清单](../examples/cases.json) 记录三个公开配置的仓库、固定提交、路径和 SHA-256。`run_cases.py` 校验摘要及预期不支持事件后才写出报告。展示结果见 [案例索引](../examples/case-results/README.md)。

单元测试使用本项目编写的最小配置，不复制第三方 Hook 实现。第三方 JSON 缓存在被忽略的 `.work/upstream/`；本工具从不执行其命令。

## 更新规则

新增目标版本时使用新 profile ID，保留旧快照。核对事件集合、解析顺序、默认值、字段保留、根目录替换与 matcher 逻辑，补充能证明变化和避免误报的最小用例。源信息冲突时说明冲突，直到确认实现前保留待核对状态。
