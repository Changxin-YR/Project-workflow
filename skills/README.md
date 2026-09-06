# Skills

技能按阶段读取，只处理自己的输入、输出和门禁，不把项目事实留在插件状态中。总控入口是 `project-factory`；各阶段的单一职责如下：

- `project-factory`：显式触发、初始化或恢复 `workflow/state.json`，调度阶段并阻止越过门禁。
- `requirement-parser`：提取目标、功能、技术关键词和未知信息。
- `requirement-interviewer`：按 P0/P1/P2 优先级补齐需求，必要时暂停等待用户。
- `requirements-freeze`：生成需求冻结文件并等待 `确认需求`。
- `github-reference-miner`：检索并评分公开参考仓库，保持只读隔离。
- `reference-synthesizer`：把高价值参考压缩为 `docs/research/` 热知识。
- `solution-architect`：从冻结需求和参考知识生成架构与主计划。
- `plan-reviewer`：独立检查需求覆盖、可实现性、安全、测试性和过度设计。
- `implementation-agent`：按计划实现模块并提供可复核的测试证据。
- `module-reviewer`：依据冻结需求、差异和运行结果验收模块。
- `full-project-auditor`：在尽可能干净的环境执行完整项目验收。
- `release-manager`：确认发布资格并把项目送入 Git Delivery Gate。
- `git-delivery`：调用 `scripts/git_delivery.py` 完成扫描、计划、提交、验证、Push 或安全暂停。

所有阶段都必须尊重 `workflow/state.json`、`REQUIREMENTS_FROZEN.md` 和已有验收证据。冻结后的需求和验收标准不可悄然改写；凭据、远程创建、参考仓库执行和不可逆操作必须进入人工决策状态。
