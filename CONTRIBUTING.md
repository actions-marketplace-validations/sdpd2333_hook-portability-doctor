# 贡献指南

运行环境为 Python 3.11+，检查器与测试只使用标准库。

```shell
python scripts/acceptance.py
```

改动包结构、CLI 入口或包资源后，还需[构建并验证 wheel](docs/DISTRIBUTION.md)。
运行时和普通测试保持标准库依赖；build、setuptools、twine 仅用于构建与检查分发物。
Action 修改需覆盖成功、严格模式失败、错误输入和旧报告隔离，并检查
`.github/workflows/check.yml` 中的真实 runner 集成任务。修改固定规则时更新
`scripts/hook_doctor/profiles/`，避免在仓库根目录另存一份运行规则。

修改判定规则时，请附上：

1. 目标仓库的固定提交与实际实现位置。
2. 能复现差异的最小 JSON，以及应当产生的类别、JSON Pointer 和建议。
3. 一项相近但不应误报的情况。
4. 相应测试和必要的参考文档更新。

保持输入只读，不从配置字符串执行命令，不用模型推测代替确定的规则判断。不把缺少环境信息当成不兼容，也不把未命中规则当成运行成功。

真实案例在 `examples/cases.json` 中固定提交和摘要。更新展示报告的命令是：

```shell
python scripts/run_cases.py --fetch --out examples/case-results
```

提交前检查输入来源、摘要、报告差异和测试结果。第三方原始文件、`.work/`、`reports/` 与本地环境不提交。报告使用 `case_source` 元数据记录归属，不包含第三方命令正文。

修复报告时可提供最小配置、规则 ID、预期/实际结果和版本。请删除私有路径或秘密值；本工具并不需要 API Key。
