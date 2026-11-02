# 安装与分发

Python 3.11+。运行包没有第三方依赖，不要求 AI 客户端、API Key 或 DSH。
当前开发版本为 0.2.0；本指南使用本地源码或 wheel，不假定 PyPI 上有同名版本。

## 从源码安装

先激活你自己的 Python 虚拟环境，在源码仓库根目录运行：

```shell
python -m pip install .
hook-portability-doctor --version
```

然后可以切换到任何目录，运行：

```shell
hook-portability-doctor "path/to/hooks.json" --strict --out reports/hooks
python -m hook_doctor "path/to/hooks.json" --strict --out reports/hooks
```

两个入口使用同一份实现与规则。输入和相对输出目录以调用时的工作目录为基准。
源码入口 `python scripts/check_hooks.py` 和完整 skill 安装仍可使用。

## 构建与检查

在开发虚拟环境中安装构建工具：

```shell
python -m pip install build twine
python -m build
python -m twine check dist/*
python scripts/verify_distribution.py
```

默认构建先生成 sdist，再从 sdist 构建 wheel。版本来自
`scripts/hook_doctor/__init__.py`；规则作为包资源包含在 wheel 中。

`verify_distribution.py` 会创建独立临时虚拟环境，用
`pip install --no-index --no-deps` 安装 wheel，随后在仓库外的中文及空格目录中验证：

- 导入来自安装环境，版本正确，固定规则完整，没有运行依赖。
- 命令行和模块入口的支持配置、明确不兼容、仅报告模式、行为变化、无 Hook、错误 JSON、根目录上下文。
- 退出码、JSON / Markdown、输入只读、输入覆盖保护及 Hook 不执行。

结果写入 `reports/package-verification.json`。独立环境由验证脚本自动清理。
构建工具的首次安装可能访问包索引；wheel 的消费验证本身离线。

## 使用构建好的文件

在接收方的虚拟环境中：

```shell
python -m pip install --no-index --no-deps "dist/hook_portability_doctor-0.2.0-py3-none-any.whl"
python -m hook_doctor --version
```

wheel 是可安装的运行包；sdist 提供源码、示例、skill 和开发脚本。
上述步骤不会上传 PyPI、创建 Git 标签或发布 GitHub Release。
