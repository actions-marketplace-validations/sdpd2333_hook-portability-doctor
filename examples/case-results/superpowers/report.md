# Hook 迁移检查报告

**结论：发现配置行为差异。**

本报告检查 Claude Hook 配置通过指定 DSH 兼容桥的静态差异。安装版本和实际执行尚未验证。

- 输入：obra/superpowers@2ce8aa15d05b/hooks/hooks.json
- 规则：`dsh-claude-ce7073d`；目标提交：`ce7073d51254c26cd63b22a60835b8f948deb447`
- 输入 SHA-256：`47fd72cc8bedf31c72702b35b4ed7bab670294d658c4ce518330337525a3798b`
- 检查器版本：`0.1.0`；规则核对日期：2026-11-03
- 事件：1；配置处理器：1；待运行验证的 command 候选：1

同一原因的路径配置、工具匹配提示按问题组归并，关联位置仍全部保留。

| 分类 | 问题组数量 |
|---|---:|
| 明确不兼容 | 0 |
| 行为变化 | 1 |
| 配置待确认 | 1 |
| 需要核对 | 1 |

## 检查项

### 1. 配置待确认 · HP005

- 位置：<code>/hooks/SessionStart/0/hooks/0/command</code>
- 判断：命令引用 CLAUDE\_PLUGIN\_ROOT，本次检查未收到 pluginRoot；不能据此断言用户没有配置。
- 建议：用 --plugin-root 提供目标桥的实际插件根目录后复查。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 2. 行为变化 · HP003

- 位置：<code>/hooks/SessionStart/0/hooks/0/shell</code>
- 判断：显式 shell 选择不被采用；实际执行 shell 需要核对。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 3. 需要核对 · HP008

- 位置：<code>/hooks/SessionStart/0/matcher</code>
- 判断：该事件的匹配主体和目标正则语义尚未验证。
- 建议：核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

## 尚未验证

- 目标实际安装版本与规则快照是否一致
- Hook 命令、脚本输出、依赖和 shell 行为
- 目标正则是否合法及实际工具名称是否匹配
- 其他配置层的合并、事件时序与实际运行结果

处理器候选数量只反映静态结构；正则、脚本依赖和运行时仍可能阻止注册或执行。
