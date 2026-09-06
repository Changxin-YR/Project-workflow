# Codex Project Factory

一个按需启用的 Codex 软件项目生产工作流：从原始想法开始，经过需求冻结、架构、实现、审查和完整验收，最后通过 Git Delivery Gate 安全交付。

## 什么时候启动

插件默认不接管普通开发请求。只有用户明确输入以下任一方式时才启动：

```text
使用项目工作流
/project-factory
```

需求访谈结束后，只有收到精确回复 `确认需求` 才会冻结需求并继续。再次启动时，先读取目标项目的 `AGENTS.md`、`workflow/state.json`、当前计划、Git 状态和历史，从上次事实状态恢复。

## 工作流阶段

```text
INIT
→ REQUIREMENT_ANALYSIS
→ REQUIREMENT_INTERVIEW
→ WAITING_FOR_USER
→ REQUIREMENT_FROZEN
→ REFERENCE_RESEARCH
→ ARCHITECTURE
→ PLAN_REVIEW
→ IMPLEMENTATION
→ MODULE_ACCEPTANCE
→ FULL_ACCEPTANCE
→ RELEASE_PREPARATION
→ GIT_DELIVERY
→ FINAL_DELIVERY
→ DONE
```

每个阶段都有独立 Skill、输入、输出和门禁。项目事实写入目标仓库，不依赖聊天记录。

## Git Delivery Gate

Full Acceptance 通过后仍需满足以下条件才能进入 `DONE`：

- Build、核心 Unit、Integration 和核心 E2E 通过
- 核心需求覆盖率为 100%
- P0/P1 缺陷为 0
- Secret Scan、Commit Plan、历史验证、最终测试和 Remote Verify 通过
- 当前远程、分支、Upstream 和目标仓库明确

Git Delivery 会检查工作区、生成逻辑提交计划、按明确文件分组提交、重新运行最终测试，并在验证远程 HEAD 后 Push。它不会默认执行 `git add .`、历史重写、强制 Push 或破坏性清理。

## 仓库前置条件

目标项目在 Git Delivery 阶段需要已有 Git 仓库：

- 无 Git 仓库：进入 `WAITING_FOR_REPOSITORY`
- 有 Git、无 `origin`：进入 `WAITING_FOR_GIT_REMOTE`
- 认证失败：进入 `WAITING_FOR_GIT_AUTH`
- 网络 Push 失败：进入 `PUSH_FAILED`，保留本地提交并支持恢复

远程仓库创建、凭据、生产环境和不可逆操作需要用户确认。公开 GitHub 参考仓库只读、隔离在 `references/repos/`，不会自动执行其中的脚本或安装依赖。

## 部署到 Codex

### 方式一：直接从 GitHub 接入（推荐）

要求：已安装 Codex CLI。首次使用先登录：

```powershell
codex login
```

1. 添加这个仓库提供的 marketplace：

   ```powershell
   codex plugin marketplace add https://github.com/Changxin-YR/Project-workflow.git --ref main
   ```

2. 确认 marketplace 已被 Codex 识别：

   ```powershell
   codex plugin marketplace list
   ```

3. 安装插件。命令行方式最直接：

   ```powershell
   codex plugin add codex-project-factory@project-workflow
   ```

   也可以在 Codex Desktop 的 Plugins Directory 中选择 `Project Workflow`，安装 `Codex Project Factory`。

4. 确认插件已经安装：

   ```powershell
   codex plugin list --marketplace project-workflow
   ```

5. 打开一个软件项目仓库，在 Codex 对话中输入：

   ```text
   使用项目工作流
   ```

   或：

   ```text
   /project-factory
   ```

6. 需求访谈结束后，检查生成的 `docs/requirements/REQUIREMENTS_FROZEN.md`，确认无误时回复：

   ```text
   确认需求
   ```

更新仓库后，在 Codex CLI 执行：

```powershell
codex plugin marketplace upgrade project-workflow
```

然后重启 Codex Desktop，确保使用最新版本。

### 方式二：先克隆到本地再接入

```powershell
git clone https://github.com/Changxin-YR/Project-workflow.git
codex plugin marketplace add .\Project-workflow
codex plugin add codex-project-factory@project-workflow
codex plugin list --marketplace project-workflow
```

这种方式适合需要审阅或修改 Skill 的团队。修改仓库后重新执行 `codex plugin marketplace upgrade project-workflow`，再重启 Codex Desktop。

### 方式三：通过 npm 安装 GitHub 源（现在可用）

Codex 当前没有把 npm registry 作为原生插件安装源。npm 安装完成后，需要把安装目录注册为 Codex marketplace，再安装插件。下面命令使用独立临时目录，不会修改你的软件项目：

PowerShell：

```powershell
$installRoot = Join-Path $env:TEMP "codex-project-factory-npm"
Remove-Item -Recurse -Force $installRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $installRoot | Out-Null
npm install --prefix $installRoot github:Changxin-YR/Project-workflow
codex plugin marketplace add (Join-Path $installRoot "node_modules\codex-project-factory")
codex plugin add codex-project-factory@project-workflow
codex plugin list --marketplace project-workflow
```

macOS/Linux：

```bash
install_root="$(mktemp -d)"
npm install --prefix "$install_root" github:Changxin-YR/Project-workflow
codex plugin marketplace add "$install_root/node_modules/codex-project-factory"
codex plugin add codex-project-factory@project-workflow
codex plugin list --marketplace project-workflow
```

### 方式四：通过 npm 下载源码包

如果你需要离线保存 tarball 或交给团队内部镜像，可以用 `npm pack` 下载并解包。无需 npm 账号即可执行：

```powershell
$installRoot = Join-Path $env:TEMP "codex-project-factory-install"
Remove-Item -Recurse -Force $installRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $installRoot | Out-Null
Push-Location $installRoot
$archive = npm pack github:Changxin-YR/Project-workflow --silent
tar -xzf $archive
codex plugin marketplace add (Join-Path $installRoot "package")
codex plugin add codex-project-factory@project-workflow
codex plugin list --marketplace project-workflow
Pop-Location
```

macOS/Linux：

```bash
install_root="$(mktemp -d)"
cd "$install_root"
archive=$(npm pack github:Changxin-YR/Project-workflow --silent)
tar -xzf "$archive"
codex plugin marketplace add "$install_root/package"
codex plugin add codex-project-factory@project-workflow
codex plugin list --marketplace project-workflow
```

这条路径中，npm 负责下载和解包源码，`codex plugin marketplace add` 负责把解包目录注册给 Codex。仓库已经包含 `package.json`，也可以在仓库目录执行 `npm pack` 生成可分发的 tarball。

### 方式五：npm registry 安装（维护者先发布）

当前包的 npm registry 发布状态可以这样检查：

```powershell
npm view codex-project-factory version
```

维护者需要先登录 npm 并发布包：

```powershell
npm publish --access public
```

发布完成后，先确认 registry 已返回版本号：

```powershell
npm view codex-project-factory version
```

确认成功后，用户即可使用标准 registry 安装：

```powershell
$installRoot = Join-Path $env:TEMP "codex-project-factory-npm"
New-Item -ItemType Directory -Force $installRoot | Out-Null
npm install --prefix $installRoot codex-project-factory
codex plugin marketplace add (Join-Path $installRoot "node_modules\codex-project-factory")
codex plugin add codex-project-factory@project-workflow
```

在 registry 返回版本号之前，请使用上面的 GitHub source npm 安装方式；registry 包发布需要维护者的 npm 账号和权限。

更新插件时，重新执行对应下载步骤，然后执行：

```powershell
codex plugin marketplace upgrade project-workflow
codex plugin list --marketplace project-workflow
```

Codex 插件目录、manifest 和 marketplace 的官方说明见：[Package your plugin - OpenAI Developers](https://developers.openai.com/plugins/build/plugins)。

## 本地验证

在插件根目录执行：

```powershell
python scripts/test_project_factory.py
python scripts/test_git_delivery.py
python scripts/test_package.py
python -m compileall -q scripts
python C:\Users\27363\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

查看 Git Delivery 的只读结果：

```powershell
python scripts/git_delivery.py inspect --repo <target>
python scripts/git_delivery.py scan --repo <target>
python scripts/git_delivery.py deliver --repo <target> --state <target>\workflow\state.json --dry-run
```

`--dry-run` 只生成检测、扫描、提交和 Push 计划，不执行 Commit 或 Push。

## 项目证据

目标项目模板位于 `templates/project/`，包括：

- `workflow/state.json`：唯一工作流状态源
- `workflow/progress.md`：阶段进度
- `workflow/failures.md`：失败与根因记录
- `workflow/last-good-state.md`：最近一次可恢复状态
- `workflow/git-commit-plan.md`：逻辑提交计划
- `docs/requirements/`、`docs/research/`、`docs/architecture/`、`docs/acceptance/`

冻结后的需求、验收标准、安全规则、权限规则和架构决策不能被静默改写。

## 安全边界

主项目可以自动安装已声明依赖、运行测试、构建和迁移。密钥、令牌、密码、生产凭据、远程创建、付费资源和不可逆操作需要人工确认。日志和状态输出只保存路径、规则和结果，不输出凭据值。

## 当前版本

本仓库包含 Project Factory V1 的插件骨架、阶段 Skills、状态/Git 核心、目标项目模板和可重复测试。验收记录见 `docs/acceptance/project-factory-v1.md`。
