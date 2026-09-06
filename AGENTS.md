# Codex Project Factory

这是一个只面向软件项目仓库的、可恢复的 Codex 工作流插件。入口和阶段规则位于
`skills/project-factory/SKILL.md`；Git Delivery 规则位于 `skills/git-delivery/SKILL.md`，
可执行核心位于 `scripts/git_delivery.py`。

## 事实入口

- 当前阶段和恢复状态：`workflow/state.json`
- 阶段进度与失败记录：`workflow/progress.md`、`workflow/failures.md`、`workflow/last-good-state.md`
- 冻结后的唯一需求依据：`docs/requirements/REQUIREMENTS_FROZEN.md`
- 架构与执行计划：`ARCHITECTURE.md`、`docs/exec-plans/active/`
- 验收证据：`docs/acceptance/`，模块报告在 `docs/acceptance/module-reports/`
- Git 交付计划：`workflow/git-commit-plan.md`

## 不可变规则

- 仅在用户明确输入“使用项目工作流”或 `/project-factory` 时启动；普通项目请求不被接管。
- 需求只有在用户明确回复 `确认需求` 后才冻结，冻结后的需求和验收标准不可悄然改写。
- `workflow/state.json` 是唯一状态源；跨 Session 恢复前先读取状态、计划、Git 状态和历史。
- `references/repos/` 只读且隔离，公开参考仓库的脚本和依赖不得自动执行或安装。
- 主项目的常规依赖安装、测试、构建和迁移可自动执行；凭据、远程创建和不可逆操作必须暂停等待确认。
- 只有完整验收和 Git Delivery Gate 全部通过后才能进入 `DONE`；任何等待、失败或人工决策状态都必须保留证据。

## 当前状态

以 `workflow/state.json`、最近的验收报告和 Git 事实为准。不要把聊天记录或摘要当作项目事实。
