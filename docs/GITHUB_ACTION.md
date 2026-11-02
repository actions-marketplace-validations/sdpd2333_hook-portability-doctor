# GitHub Action 接入

Action 检查已 checkout 的 JSON 文件或插件目录，使用内置的固定 DSH 规则。
它通过 actions/setup-python 准备 Python 3.11，随后运行标准库检查器。
配置内容不会作为 shell 代码执行，根目录上下文也不会自动推断。

## 在本仓库使用

```yaml
name: Hook check
on: [push, pull_request]
permissions:
  contents: read
jobs:
  hooks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - id: hooks
        uses: ./
        with:
          path: examples/minimal-supported.json
          output-directory: reports/hooks
      - if: always() && steps.hooks.outputs.report-json != ''
        uses: actions/upload-artifact@v7
        with:
          name: hook-portability-report
          path: |
            ${{ steps.hooks.outputs.report-json }}
            ${{ steps.hooks.outputs.report-markdown }}
```

在其他仓库中，将 `uses: ./` 换为
`uses: sdpd2333/hook-portability-doctor@COMMIT_SHA`，并把
`COMMIT_SHA` 替换为**已推送、含 action.yml、经过检查的完整提交 SHA**。
`path` 指向调用方仓库内的配置。本轮代码发布前，请勿把占位符或历史 main
当作可用的新版本；这里没有假定 v0.2.0 标签已经存在。

## 参数

| 输入 | 默认值 | 含义 |
|---|---|---|
| path | 必填 | JSON 文件或插件目录；多个候选时报错 |
| strict | true | 仅明确不兼容时以退出码 1 失败 |
| profile | dsh-claude-ce7073d | 固定目标快照 |
| plugin-root | 空 | 显式目标插件目录 |
| project-dir | 空 | 显式目标项目目录 |
| output-directory | reports/hook-portability | 报告目录 |

`strict: 'false'` 仍生成完整报告，但不会仅因不兼容而失败。
错误输入与内部错误始终失败。请为同一 job 中的每次扫描指定独立报告目录。

## 结果与失败处理

| 输出 | 含义 |
|---|---|
| exit-code | 0 检查完成；1 严格模式不兼容；2 输入/输出错误；3 内部错误 |
| status | 当前报告的分析状态 |
| incompatible-count | 确定不兼容的问题组数量 |
| report-json / report-markdown | 本次生成的报告绝对路径 |

严格模式返回 1 时，报告已写出，可以用 `if: always()` 上传。
返回 2 或 3 时不导出报告路径或状态，避免复用之前遗留的报告；旧文件不会自动删除。
报告上传应使用 Action 导出的路径，不应无条件上传可能包含旧文件的整个目录。

需要先检查结果再决定是否失败时，可在调用步骤设置
`continue-on-error: true`，随后检查 `steps.hooks.outcome` 和输出。
步骤摘要只呈现当前扫描状态与分类计数。

`no_hooks` 和 `no_handlers` 也会返回 0；它们表示没有可检查的实际处理器。
任何退出码都不证明第三方插件实际运行兼容。

## 维护验证

`python scripts/acceptance.py` 覆盖 Action 适配脚本的成功、失败、非法输入、
旧报告隔离、上下文和特殊路径处理。

仓库 CI 的 `action-integration` job 在 Ubuntu / Windows runner 上调用
`uses: ./`，核对成功与预期失败后的输出、报告和步骤结果。
本地适配脚本测试不等同于真实 GitHub runner 已经执行。
