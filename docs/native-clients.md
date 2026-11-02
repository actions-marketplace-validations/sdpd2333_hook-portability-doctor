# Claude Code 与 DSH 原生验证

2026-11-03 在 Windows 11 上完成。CLI、skill 加载、目标桥契约、自建 Hook 执行分别记录，不把一个示例的成功推广到任意第三方插件。

## 已验证的客户端流程

| 客户端 | 本机版本 | 结果 |
|---|---|---|
| Claude Code | 2.1.316 | 原生目录发现 skill，调用 `Skill`，执行检查器，读取新报告 |
| DSH headless | 0.2.1-rc.5 | 原生 `skill` 工具加载，执行检查器，读取新报告 |

两个客户端分别在独立 Git 工作目录中处理 `examples/migration-gaps.json` 的副本。请求要求使用 skill 生成报告，没有提供预期计数。报告均为 **3 项不兼容、2 项行为变化、1 项配置待确认、2 项待核对**，结构化判断与直接运行检查器一致，输入保持不变。

Claude Code 初始化事件列出了 `hook-portability-doctor`，随后调用 `Skill`；DSH JSON 事件流记录了 `tool: skill` 和对应名称。本次请求显式提到 skill 名称，证明原生发现和显式请求下的使用，未评估各种提示词中的自动选用成功率。

[机器可读结果](native-verification.json) 只保存必要的版本、摘要和观察结果。原始事件流、模型思考、会话标识和本机配置不进入公开仓库。

## 安装到项目 skill 目录

在检查器仓库运行对应命令；按使用的客户端选择其一：

```shell
python scripts/install_skill.py --skills-dir "<project>/.claude/skills"
python scripts/install_skill.py --skills-dir "<project>/.dsh/skills"
```

脚本复制完整 skill 资源，不覆盖已有同名目录，也不复制开发缓存或运行报告。DSH 默认项目根目录是最近的 `.git` 祖先；嵌套测试目录应建立独立 Git 仓库，或通过 `customSkillDirs` 显式提供根目录。Codex 可使用 `.agents/skills`，其原生加载本轮未测试。

提示词：

> 使用 hook-portability-doctor skill，检查 input.json 中 Claude hooks 迁移到 DSH Claude Hook 兼容桥的差异。调用自带检查器，输出到 output，读取新报告并解释确定问题和未知事项。不要执行输入中的 Hook 命令。

## Claude Code 可复现入口

把自建示例复制为目标工作目录的 `input.json`，确认已有正常的模型认证方式。在该目录的 PowerShell 中执行：

```powershell
claude --print --output-format stream-json --verbose --no-session-persistence --strict-mcp-config --mcp-config '{"mcpServers":{}}' --permission-mode dontAsk --allowedTools 'Skill,Read,Bash(python *)' --tools 'Skill,Read,Bash' -- '使用 hook-portability-doctor skill 检查 input.json，报告写到 output，并读取报告解释结果。'
```

本机额外使用独立 `CLAUDE_CONFIG_DIR`、`--setting-sources project,local`、`--effort low`、`--max-budget-usd 2`，在子进程环境中复用已配置的认证与网关，没有修改全局设置。实际调用通过参数数组传参，避免 shell 转义歧义。

两项实际发现的边界：

- 本版本 `--bare` 下没有把项目 skill 放入本次原生目录列表，因此正式验证使用正常模式和隔离配置目录。
- `Bash(python *)` 权限下，拼接 `ls`、Python 和 `echo` 可能被拒绝。已在 skill 中要求单独调用检查器，从工具返回值读取退出状态，不为此关闭客户端权限系统。

## DSH 可复现入口

本机使用独立 `DSH_HOME` 和 headless profile，沿用已登录的 DeepSeek account 认证路线；会话保存在测试目录。profile 的 bundle 列表为 `@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-headless`，主 profile 文件保持不变。

skill provider 测试覆盖层：

```yaml
- id: skill-filesystem
  config:
    includeDefaultRoots: false
    watch: false
    customSkillDirs:
      - <workspace>/.dsh/skills
```

启动：

```shell
dsh --profile headless --json "使用 hook-portability-doctor skill 检查 input.json，报告写到 output，并读取报告解释结果。"
```

独立 headless 环境需要正常的认证配置。本机账号路线通过 credentials / authorization / deepseek-account 服务恢复，凭据由客户端读取，不写入本项目。无交互测试采用 workspace-write sandbox 和对应的 never-approval 测试 preset，不改变主 profile 的权限设置。

## DSH 真实 Hook 执行

CLI 没有预装 Claude Hook 桥。测试单独安装官方 `@deepseek-ai/dsh-hooks-claude-code@0.2.1-rc.5`，通过绝对模块路径挂载到隔离 profile，未安装到全局。

自写 [probe.cjs](../examples/runtime/probe.cjs) 和 [配置](../examples/runtime/hooks.json) 记录事件、cwd、项目目录和参数。在真实 DSH headless 任务中观察到：

- `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`Stop` 四种事件实际启动 Node 子进程。
- `PreToolUse` 命中 DSH 的 `read` 工具。
- 插件根目录替换和 `CLAUDE_PROJECT_DIR` 与测试工作目录一致。
- 独立 `args` 字段未追加到进程参数；Stop / UserPromptSubmit 的无效正则 matcher 未阻止执行。
- 不支持事件中的无效 matcher 未使整份配置加载失败。未专门触发真实压缩流程，不把“没有 PreCompact 标记”单独当作运行证明。

复现时将两个自建文件复制到测试工作目录，替换下面的占位路径：

```yaml
- insert:
    - id: hpd-probe
      name: <repo>/integrations/dsh/node_modules/@deepseek-ai/dsh-hooks-claude-code/lib/index.js
      config:
        configPath: <workspace>/hooks.json
        pluginRoot: <workspace>
        projectDir: <workspace>
```

只在明确测试这些自建文件时挂载。常规 `check_hooks.py` 始终不执行输入命令。

## 不调用模型的目标桥契约检查

```shell
npm ci --prefix integrations/dsh --ignore-scripts --no-audit --no-fund
node scripts/verify_dsh_bridge.mjs
```

使用真实 npm 桥模块和记录型 context，在 shell 服务边界截获调用，验证八项解析与转发契约：默认 type、非 command 跳过、未知事件、无效 matcher、空 runnable 组、根目录替换、args 和 timeout。该层不启动模型或 Hook 子进程，与真实 headless 执行分别记录。

[本机契约结果](dsh-contracts.json) 包含安装包版本和模块 SHA-256。包未提供可确认的源码 commit 标识，因此只主张这些契约与规则快照一致，不把 npm 版本直接等同于 `ce7073d`。
