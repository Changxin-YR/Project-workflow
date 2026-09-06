# Project Factory V1 Acceptance

## 一、本次结论

插件实现和分发验证通过。仓库已绑定 `origin`，核心实现已安全推送到 `main`；Git Delivery 的三种仓库状态和阻断/恢复逻辑由临时仓库测试覆盖。

## 二、实际修改与新增文件

- 插件元数据：`.codex-plugin/plugin.json`
- 导航和使用说明：`AGENTS.md`、`README.md`、`.gitignore`、`skills/README.md`
- 总控与阶段 Skills：`skills/*/SKILL.md`
- 状态/Git 核心：`scripts/project_factory.py`、`scripts/git_delivery.py`、`scripts/state_schema.json`
- 可重复测试：`scripts/test_project_factory.py`、`scripts/test_git_delivery.py`、`scripts/test_package.py`
- 目标项目模板：`templates/project/`
- Codex marketplace 清单：`.agents/plugins/marketplace.json`
- npm 分发元数据：`package.json`、`.npmignore`

## 三、状态机

```text
INIT -> REQUIREMENT_ANALYSIS -> REQUIREMENT_INTERVIEW -> WAITING_FOR_USER
-> REQUIREMENT_FROZEN -> REFERENCE_RESEARCH -> ARCHITECTURE -> PLAN_REVIEW
-> IMPLEMENTATION -> MODULE_ACCEPTANCE -> FULL_ACCEPTANCE
-> RELEASE_PREPARATION -> GIT_DELIVERY -> FINAL_DELIVERY -> DONE
```

`FULL_ACCEPTANCE` 未通过时不能进入 Git Delivery；Git Delivery 的等待、失败和人工决策状态保留在 `workflow/state.json`，跨 Session 依据状态、Git 状态和历史恢复。

## 四、Git Delivery 实际逻辑

先检查仓库、工作区、分支和 `origin`，再执行前置验收检查、敏感信息扫描、逻辑提交规划、显式文件分组、缓存区差异检查、分段提交、历史验证、提交后最终测试、远程验证和 Push。`--dry-run` 只输出计划命令，不修改提交或远程。

三种仓库情况：

1. 有 Git 且有 `origin`：进入扫描、计划、分段提交、验证和 Push。
2. 有 Git 但无 `origin`：进入 `WAITING_FOR_GIT_REMOTE`，等待用户提供 URL。
3. 无 Git：进入 `WAITING_FOR_REPOSITORY`，等待用户创建仓库并提供 URL；不伪装为完成。

安全规则包含环境文件、令牌、密码、私钥、证书、数据库转储、日志、备份、依赖目录、构建产物和参考仓库隔离；不使用历史重写、强制 Push 或破坏性清理。认证失败进入 `WAITING_FOR_GIT_AUTH`，临时网络失败进入 `PUSH_FAILED`，最终测试失败进入 `FAILED_VALIDATION`。

## 五、验证结果

| Check | Result |
| --- | --- |
| `python scripts/test_project_factory.py` | PASS |
| `python scripts/test_git_delivery.py` | PASS |
| `python scripts/test_package.py` | PASS |
| `python -m compileall -q scripts` | PASS |
| plugin creator `validate_plugin.py .` | PASS |
| `npm pack --dry-run --json` | PASS, 40 files; no Python cache or workspace-only files |
| real local tarball `npm install --ignore-scripts` | PASS; manifest and project-factory Skill present under `node_modules/codex-project-factory` |
| `git_delivery.py inspect --repo .` | `repositoryDetected=true`, `remoteDetected=true`, branch `main` |
| `git_delivery.py scan --repo .` | PASS, no findings |
| Real remote Push | PASS; remote `main` HEAD matched local HEAD after Push, verified with `git ls-remote` |

## 六、当前可用性与限制

插件可安装并按显式触发运行。目标软件项目在进入最终 Git Delivery 前必须由用户准备 Git 仓库和远程地址；远程仓库创建和凭据操作保持人工确认。当前插件仓库使用 `main` 分支并跟踪 `origin/main`。

## 七、Codex 部署入口

官方 GitHub marketplace 入口：

```powershell
codex plugin marketplace add https://github.com/Changxin-YR/Project-workflow.git --ref main
codex plugin add codex-project-factory@project-workflow
```

npm 下载入口：

```powershell
$archive = npm pack github:Changxin-YR/Project-workflow --silent
tar -xzf $archive
codex plugin marketplace add .\package
codex plugin add codex-project-factory@project-workflow
```

npm registry 尚未发布此包；当前仓库已可通过 `npm install github:Changxin-YR/Project-workflow` 安装源码，或通过 `npm pack` 生成干净的分发 tarball。安装后将 `node_modules/codex-project-factory` 注册为 Codex marketplace，再执行 `codex plugin add codex-project-factory@project-workflow`。
