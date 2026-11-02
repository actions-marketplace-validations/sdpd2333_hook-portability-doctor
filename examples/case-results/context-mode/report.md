# Hook 迁移检查报告

**结论：发现明确不兼容项。**

本报告检查 Claude Hook 配置通过指定 DSH 兼容桥的静态差异。安装版本和实际执行尚未验证。

- 输入：mksglu/context-mode@78d3dd080e4f/hooks/hooks.json
- 规则：`dsh-claude-ce7073d`；目标提交：`ce7073d51254c26cd63b22a60835b8f948deb447`
- 输入 SHA-256：`e1fdd0c0e82d164f119daa43803513b802ca5edab93bc123b2c7d8d4c637cf3e`
- 检查器版本：`0.1.0`；规则核对日期：2026-11-03
- 事件：6；配置处理器：14；待运行验证的 command 候选：13

同一原因的路径配置、工具匹配提示按问题组归并，关联位置仍全部保留。

| 分类 | 问题组数量 |
|---|---:|
| 明确不兼容 | 1 |
| 行为变化 | 0 |
| 配置待确认 | 1 |
| 需要核对 | 1 |

## 检查项

### 1. 配置待确认 · HP005

- 位置：<code>/hooks/PostToolUse/0/hooks/0/command</code>
- 判断：命令引用 CLAUDE\_PLUGIN\_ROOT，本次检查未收到 pluginRoot；不能据此断言用户没有配置。
- 建议：用 --plugin-root 提供目标桥的实际插件根目录后复查。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

同组位置：<code>/hooks/PostToolUse/0/hooks/0/command</code>、<code>/hooks/PreToolUse/0/hooks/0/command</code>、<code>/hooks/PreToolUse/1/hooks/0/command</code>、<code>/hooks/PreToolUse/2/hooks/0/command</code>、<code>/hooks/PreToolUse/3/hooks/0/command</code>、<code>/hooks/PreToolUse/4/hooks/0/command</code>、<code>/hooks/PreToolUse/5/hooks/0/command</code>、<code>/hooks/PreToolUse/6/hooks/0/command</code>、<code>/hooks/PreToolUse/7/hooks/0/command</code>、<code>/hooks/PreToolUse/8/hooks/0/command</code>、<code>/hooks/SessionStart/0/hooks/0/command</code>、<code>/hooks/Stop/0/hooks/0/command</code>、<code>/hooks/UserPromptSubmit/0/hooks/0/command</code>

### 2. 需要核对 · HP006

- 位置：<code>/hooks/PostToolUse/0/matcher</code>
- 判断：工具名与目标正则语义需要运行核对。
- 建议：核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

同组位置：<code>/hooks/PostToolUse/0/matcher</code>、<code>/hooks/PreToolUse/0/matcher</code>、<code>/hooks/PreToolUse/1/matcher</code>、<code>/hooks/PreToolUse/2/matcher</code>、<code>/hooks/PreToolUse/3/matcher</code>、<code>/hooks/PreToolUse/4/matcher</code>、<code>/hooks/PreToolUse/5/matcher</code>、<code>/hooks/PreToolUse/6/matcher</code>、<code>/hooks/PreToolUse/7/matcher</code>、<code>/hooks/PreToolUse/8/matcher</code>

### 3. 明确不兼容 · HP001

- 位置：<code>/hooks/PreCompact</code>
- 判断：目标不识别此事件，整组配置会在解析处理器之前被忽略。
- 建议：核对源平台事件名称；需要保留该功能时寻找目标的原生入口。删除配置不等于完成迁移。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

## 尚未验证

- 目标实际安装版本与规则快照是否一致
- Hook 命令、脚本输出、依赖和 shell 行为
- 目标正则是否合法及实际工具名称是否匹配
- 其他配置层的合并、事件时序与实际运行结果

处理器候选数量只反映静态结构；正则、脚本依赖和运行时仍可能阻止注册或执行。
