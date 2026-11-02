# Changelog

## 0.2.0 — 2026-11-03

- 增加标准 Python 构建元数据、wheel / sdist 和安装后的命令入口。
- 支持 hook-portability-doctor 与 python -m hook_doctor；原脚本入口继续可用。
- 将固定目标规则作为包资源分发，安装后不依赖仓库目录或当前工作目录。
- 增加复用型 GitHub Action：严格模式、报告输出、步骤摘要和错误退出码。
- 增加 Action 行为测试及全新环境中的离线 wheel 安装验证。

本版本未扩展受检目标版本或 Hook 语义。0.1.0 的原生客户端记录是历史验证，
不能当作本版本重新执行过客户端测试的证据。

## 0.1.0 — 2026-11-03

- 初始静态检查器：八类规则、JSON / Markdown 报告、固定真实案例和 skill。
