# Hook 迁移检查报告

**结论：发现明确不兼容项。**

本报告检查 Claude Hook 配置通过指定 DSH 兼容桥的静态差异。安装版本和实际执行尚未验证。

- 输入：thedotmack/claude-mem@02584c4ac9d9/plugin/hooks/hooks.json
- 规则：`dsh-claude-ce7073d`；目标提交：`ce7073d51254c26cd63b22a60835b8f948deb447`
- 输入 SHA-256：`8a231036f088798179ae54e8f2b792334191289148b4461698dc1823b51024a2`
- 检查器版本：`0.1.0`；规则核对日期：2026-11-03
- 事件：9；配置处理器：11；待运行验证的 command 候选：8

同一原因的路径配置、工具匹配提示按问题组归并，关联位置仍全部保留。

| 分类 | 问题组数量 |
|---|---:|
| 明确不兼容 | 3 |
| 行为变化 | 12 |
| 配置待确认 | 0 |
| 需要核对 | 4 |

## 检查项

### 1. 行为变化 · HP003

- 位置：<code>/hooks/PostToolUse/0/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 2. 行为变化 · HP003

- 位置：<code>/hooks/PostToolUse/0/hooks/0/async</code>
- 判断：async: true 不被采用；目标按事件的既定调度方式串行处理匹配命令，不保留此字段的后台执行语义。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 3. 需要核对 · HP006

- 位置：<code>/hooks/PostToolUse/0/matcher</code>
- 判断：工具名与目标正则语义需要运行核对。
- 建议：核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

同组位置：<code>/hooks/PostToolUse/0/matcher</code>、<code>/hooks/PreToolUse/0/matcher</code>

### 4. 明确不兼容 · HP001

- 位置：<code>/hooks/PostToolUseFailure</code>
- 判断：目标不识别此事件，整组配置会在解析处理器之前被忽略。
- 建议：核对源平台事件名称；需要保留该功能时寻找目标的原生入口。删除配置不等于完成迁移。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 5. 行为变化 · HP003

- 位置：<code>/hooks/PreToolUse/0/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 6. 明确不兼容 · HP001

- 位置：<code>/hooks/SessionEnd</code>
- 判断：目标不识别此事件，整组配置会在解析处理器之前被忽略。
- 建议：核对源平台事件名称；需要保留该功能时寻找目标的原生入口。删除配置不等于完成迁移。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 7. 行为变化 · HP003

- 位置：<code>/hooks/SessionStart/0/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 8. 行为变化 · HP003

- 位置：<code>/hooks/SessionStart/0/hooks/0/async</code>
- 判断：async: true 不被采用；目标按事件的既定调度方式串行处理匹配命令，不保留此字段的后台执行语义。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 9. 需要核对 · HP008

- 位置：<code>/hooks/SessionStart/0/matcher</code>
- 判断：该事件的匹配主体和目标正则语义尚未验证。
- 建议：核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 10. 行为变化 · HP003

- 位置：<code>/hooks/SessionStart/1/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 11. 需要核对 · HP008

- 位置：<code>/hooks/SessionStart/1/matcher</code>
- 判断：该事件的匹配主体和目标正则语义尚未验证。
- 建议：核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 12. 行为变化 · HP003

- 位置：<code>/hooks/SessionStart/2/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 13. 需要核对 · HP008

- 位置：<code>/hooks/SessionStart/2/matcher</code>
- 判断：该事件的匹配主体和目标正则语义尚未验证。
- 建议：核对实际匹配主体；本工具不使用 Python 正则冒充目标正则验证。
- 确定性：需要目标上下文或实际验证
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 14. 明确不兼容 · HP001

- 位置：<code>/hooks/Setup</code>
- 判断：目标不识别此事件，整组配置会在解析处理器之前被忽略。
- 建议：核对源平台事件名称；需要保留该功能时寻找目标的原生入口。删除配置不等于完成迁移。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-CONFIG](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/src/config.ts)

### 15. 行为变化 · HP003

- 位置：<code>/hooks/Stop/0/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 16. 行为变化 · HP003

- 位置：<code>/hooks/Stop/0/hooks/0/async</code>
- 判断：async: true 不被采用；目标按事件的既定调度方式串行处理匹配命令，不保留此字段的后台执行语义。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 17. 行为变化 · HP003

- 位置：<code>/hooks/SubagentStop/0/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 18. 行为变化 · HP003

- 位置：<code>/hooks/SubagentStop/0/hooks/0/async</code>
- 判断：async: true 不被采用；目标按事件的既定调度方式串行处理匹配命令，不保留此字段的后台执行语义。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

### 19. 行为变化 · HP003

- 位置：<code>/hooks/UserPromptSubmit/0/hooks/0/args</code>
- 判断：独立 args 字段被忽略；目标只保留 command 字符串。
- 建议：核对是否依赖此选项；在目标中验证替代方式。
- 确定性：已确认该目标快照的行为
- 依据：[DSH-LIMITATIONS](https://github.com/deepseek-ai/deepseek-harness/blob/ce7073d51254c26cd63b22a60835b8f948deb447/packages/experimental/hooks-claude-code/README.md#known-limitations-and-deferred-work)

## 尚未验证

- 目标实际安装版本与规则快照是否一致
- Hook 命令、脚本输出、依赖和 shell 行为
- 目标正则是否合法及实际工具名称是否匹配
- 其他配置层的合并、事件时序与实际运行结果

处理器候选数量只反映静态结构；正则、脚本依赖和运行时仍可能阻止注册或执行。
