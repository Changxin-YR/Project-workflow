# Codex Project Factory V1 设计

## 目标

交付一个可安装的 Codex 插件，用于软件项目仓库的全自动生产流水线。用户只需提交原始想法，并在需求规格完成后明确回复 `确认需求`。工作流只在用户明确要求“使用项目工作流”或输入 `/project-factory` 时启动；再次启动时从仓库中的事实状态恢复。

需求冻结后，工作流自主完成需求分析、动态访谈、参考研究、架构、计划、实现、测试、审查和交付。只有完整验收与 Git Delivery Gate 均通过，项目才进入 `DONE`。

## 插件边界

插件由一个总控 Skill 和职责单一的阶段 Skill 组成：

- `project-factory`：显式触发、状态读取、阶段调度、门禁判断、恢复和最终报告。
- `requirement-parser`：提取目标、功能、技术关键词和未知信息。
- `requirement-interviewer`：按 P0/P1/P2 优先级动态追问；P2 使用记录过的合理默认值。
- `requirements-freeze`：生成并等待 `REQUIREMENTS_FROZEN.md` 的明确确认。
- `github-reference-miner`：检索公开仓库，按相似度、技术栈、质量、活跃度和许可证评分。
- `reference-synthesizer`：把高价值参考压缩为热知识文档，源码放在受隔离的 `references/repos/`。
- `solution-architect`：从冻结需求和参考知识生成架构与主计划。
- `plan-reviewer`：独立检查需求覆盖、可实现性、安全、测试性和过度设计。
- `implementation-agent`：按模块计划实现并提供测试证据。
- `module-reviewer`：依据冻结需求、验收标准、差异和运行结果判定模块。
- `full-project-auditor`：在尽可能干净的环境执行全项目验收。
- `release-manager`：确认发布资格并触发 Git Delivery。
- `git-delivery`：仓库检测、远程检测、敏感信息扫描、提交规划、分段提交、验证、最终测试和 Push。

所有项目事实写入目标仓库，Skill 只负责导航和操作约束。公开参考仓库视为不可信输入，不自动执行其脚本或安装其依赖。

## 生命周期

```text
INIT
  -> REQUIREMENT_ANALYSIS
  -> REQUIREMENT_INTERVIEW
  -> WAITING_FOR_USER
  -> REQUIREMENT_FROZEN
  -> REFERENCE_RESEARCH
  -> ARCHITECTURE
  -> PLAN_REVIEW
  -> IMPLEMENTATION
  -> MODULE_ACCEPTANCE
  -> FULL_ACCEPTANCE
  -> RELEASE_PREPARATION
  -> GIT_DELIVERY
  -> FINAL_DELIVERY
  -> DONE
```

异常状态为 `BLOCKED`、`FAILED`、`NEEDS_HUMAN_DECISION` 以及 Git Delivery 的 `WAITING_FOR_REPOSITORY`、`WAITING_FOR_GIT_REMOTE`、`WAITING_FOR_GIT_AUTH`、`PUSH_FAILED`、`FAILED_VALIDATION`。每个阶段完成时更新状态、进度、决策记录和最后良好状态。

## 仓库结构

```text
project/
├─ .codex-plugin/plugin.json
├─ AGENTS.md
├─ README.md
├─ ARCHITECTURE.md
├─ skills/<skill-name>/SKILL.md
├─ docs/
│  ├─ requirements/
│  ├─ research/
│  ├─ architecture/
│  ├─ exec-plans/{active,completed}/
│  ├─ acceptance/module-reports/
│  └─ decisions/
├─ workflow/
│  ├─ state.json
│  ├─ progress.md
│  ├─ failures.md
│  ├─ last-good-state.md
│  └─ git-commit-plan.md
├─ references/repos/
└─ scripts/
```

`AGENTS.md` 只提供文档导航、不可变规则和当前状态入口；详细规则分别放在需求、架构、验收和 Skills 文档中。`references/repos/` 默认写入 `.gitignore`，研究摘要仍可进入 `docs/research/`。

## 状态与恢复

`workflow/state.json` 是唯一工作流状态源，至少包含：

```json
{
  "schemaVersion": 1,
  "phase": "GIT_DELIVERY",
  "status": "READY",
  "requirementsVersion": "1.0",
  "requirementsFrozen": true,
  "currentModule": null,
  "completedModules": [],
  "failedGate": null,
  "retryCount": 0,
  "lastGoodCommit": null,
  "gitDelivery": {
    "repositoryDetected": null,
    "remoteDetected": null,
    "securityScan": "PENDING",
    "commitPlan": "PENDING",
    "commitsCompleted": false,
    "finalTest": "PENDING",
    "remoteVerify": "PENDING",
    "push": "PENDING",
    "branch": null,
    "head": null
  }
}
```

恢复时先读取 `AGENTS.md`、`state.json`、当前执行计划，再读取 `git status`、`git log` 和远程状态。已完成的提交和 Push 不重复执行；Push 失败保留本地提交并从远程验证继续。

## Git Delivery Gate

### 进入条件

必须同时满足：完整验收、构建、核心 Unit、Integration、核心 E2E 均通过；核心需求覆盖率为 100%；P0/P1 缺陷为 0；没有阻断型安全问题。否则保持修复、测试、审查和完整验收闭环。

### 仓库检测

执行 `git rev-parse --is-inside-work-tree`、`git status --short`、`git branch --show-current` 和 `git remote -v`，识别仓库与 `origin` 的存在性。

- 已有 Git 与远程：进入分析、扫描、规划、分段提交、历史验证、最终测试、远程验证和 Push。
- 已有 Git、无远程：保存状态并进入 `WAITING_FOR_GIT_REMOTE`，用户提供 URL 后继续。
- 无 Git：保存状态并进入 `WAITING_FOR_REPOSITORY`，用户创建仓库并提供 URL 后执行 `git init`、配置远程，再继续。

远程仓库创建属于用户资源变更，默认等待用户完成；只有仓库配置明确开启自动创建时才可执行。

### 提交策略

提交前读取 `git status --short` 和 `git diff`，将文件映射为 `FILE -> MODULE -> FEATURE -> COMMIT GROUP`。每组表达一个可独立理解的逻辑变化，沿用项目已有提交规范，否则使用清晰的 Conventional Commit 类型。计划写入 `workflow/git-commit-plan.md`，字段包括 Commit ID、Message、Purpose、Files、Dependencies、Risk。

每个提交组仅 `git add` 明确文件，检查 `git diff --cached` 后再提交。已有历史只处理未提交修改，禁止重写历史、强制 Push、删除远程分支或使用破坏性清理命令。

### 安全与验证

提交和 Push 前扫描环境文件、密钥、令牌、证书、生产凭据、数据库转储、日志、备份、依赖目录和构建缓存；发现敏感信息即阻断。检查并补充必要的 `.gitignore`，但不忽略源码或业务文件。确认第三方复制代码的来源、许可证、署名和兼容性。

所有提交完成后验证工作区、历史、分支和远程；再按项目实际配置运行 Build、Lint、Type Check、Unit、Integration 和核心 E2E。最终测试失败时禁止 Push，状态为 `FAILED_VALIDATION` 并回到修复闭环。

Push 前再次确认远程 URL、所有者、仓库名、当前分支和目标分支。多个远程、异常 URL、目标不明确或历史冲突进入 `NEEDS_HUMAN_DECISION`。认证失败进入 `WAITING_FOR_GIT_AUTH`；网络等临时错误记录 `PUSH_FAILED`，保留提交并支持后续重试。

仅当 `FULL_ACCEPTANCE=PASS`、安全扫描、提交计划、提交历史、最终测试和远程验证全部通过后设置 `PUSH_ALLOWED=true` 并 Push。Push 成功后验证远程 HEAD，再写入最终交付证据；Git Delivery 未通过不得进入 `DONE`。用户明确选择跳过 Git 交付时记录 `USER_SKIPPED`，不伪装为通过。

## 权限与安全边界

主项目可自动安装已声明依赖、运行测试、构建和迁移。凭据、付费资源、生产环境、远程仓库创建和不可逆操作需要用户确认。参考仓库只读、隔离、不可执行。日志记录阶段和结果，不输出令牌、密码、私钥或其他凭据。

## 测试策略

提供可重复的断言式脚本或最小测试，覆盖：三种仓库状态、敏感信息阻断、最终测试阻断、异常远程、跨 Session 恢复、半途提交恢复、Push 失败恢复、已有历史保护、幂等重跑和 Dry Run。插件自身还需验证原有需求、冻结、研究、架构、实现、模块验收、完整验收、状态恢复和交付链路不被破坏。

## 最终交付证据

最终报告必须包含项目状态、完整验收、Git Delivery、仓库、分支、HEAD、提交数量、Build、Unit、Integration、E2E、P0/P1 缺陷和已知限制。交付状态只能由仓库事实、测试结果、验收报告和状态文件共同证明。

## 设计验收

- 触发是显式的，默认不接管普通项目。
- 需求冻结是唯一产品依据，且需要用户明确回复 `确认需求`。
- 状态、提交历史和测试结果可跨 Session 恢复。
- Full Acceptance 之后必经 Git Delivery Gate。
- 参考仓库与主仓库隔离，敏感信息和破坏性 Git 操作受到阻断。
- Git Delivery 具备检测、等待、计划、分段提交、验证、Push、失败恢复、Dry Run 和幂等能力。
