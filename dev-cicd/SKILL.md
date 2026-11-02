---
name: dev-cicd
description: 交付与 CI/CD（devflow 第 8 阶段）。需求验收通过后，或用户说“发布”“上线”“部署”“合并”“搭 CI”“release”“deploy”时使用。把合并、推送、开 PR、发布、部署这些对外动作列成一份清单在关口 D 一次确认；需要时按 .devflow.yml 的命令生成或补充 CI（含浏览器测试）；部署交给项目自己的方式并做上线后检查。
---

# dev-cicd：交付与 CI/CD

目标：**对外的动作集中让人确认一次；CI 跑的和本地一样。**

## 开始

1. 先读 `../dev-workflow/SKILL.md` 的“每次开始时”并照做（包括读 `../dev-workflow/references/decisions.md`）。本阶段还要读同目录下的 `gates.md`。
2. 有当前需求时，状态行“阶段”改为 `dev-cicd`。
3. **独立模式**：没有需求文件夹（用户只是要“搭个 CI”“发个版”）时，照常做下面的步骤，只是不读写需求文件。

**接着做**：关口 D 已确认、做了一半的，看 spec 变更记录里写到哪一步，从下一步继续。

## 1. 了解现状

- `.devflow.yml` 的 `commands` 和 `release`。
- 已有的 CI：`.github/workflows/`、`.gitlab-ci.yml`、`Jenkinsfile` 等。
- 已有的发布和部署方式：脚本、Dockerfile、compose 文件、项目里的发布或部署 skill（比如 `$release`、`$deploy-view`）。
- 分支和远程：当前分支、默认分支、`git remote -v`、是否有 `gh` 等平台命令。

**已有的东西优先沿用和补充，不要覆盖。**

## 2. CI（没有或不完整时才做）

CI 要跑的和本地一样：安装 → lint → 测试 → 构建 → 浏览器测试，任何一步失败就停。
- 命令全部用 `.devflow.yml` 的 `commands`，不要另编一套。
- 浏览器测试在 CI 里用本机无头浏览器：CI 里不设 `DEVFLOW_BROWSER_CDP`，测试会自动改用本机浏览器（见 dev-test 的 e2e-example.md）；用 Playwright 的 `webServer` 启动被测服务；先 `npx playwright install --with-deps chromium`。
- 失败时上传截图和 trace 作为产物。
- 密钥只用 CI 平台的 secrets 引用，不写进文件；在 `docs/secrets-checklist.md` 列出需要配置的变量名和用途（不写值）。

项目完全没有 CI、也没有部署方式时，参考 [references/github-docker-example.md](references/github-docker-example.md)，按项目实际情况改（那是示意，不能直接用）。

改完 CI 配置，先在本地把同样的命令按顺序跑一遍，确认能过，然后在本地提交。**这些改动是在关口 C 之后做的，要在关口 D 里列出来给人看。**

## 3. 关口 D：对外动作一次确认

把所有对外动作列在一份清单里，人确认一次就全部执行。不要一个一个问。

```markdown
## 关口 D：对外动作 · <需求名>

**一句话**：把 <需求名> 合并到 main 并发布 1.4.5
**本次新增的 CI 改动**（关口 C 之后做的，没有就不写）：
- .github/workflows/ci.yml：增加浏览器测试步骤（+24 行）

要执行的动作：
1. 推送分支 change/<短名> 到 origin
2. 开 PR 到 main（标题：…）
3. 等 CI 通过后合并（没有远程平台时：本地合并到 main 并推送）
4. 发布 1.4.5（按 release.publish：使用 $release 发布 1.4.5）
5. 部署到生产（按 release.production：使用 $deploy-view 部署 v1.4.5）
6. 上线后检查：打开线上首页，确认版本号是 1.4.5

回滚方式：…

回复 `all` 执行全部；或 `只到 3`、`去掉 5`、`跳过`（什么都不做，需求留在本地分支）。
```

- 版本号按 `release.bump` 升（默认补丁号，1.4.4 → 1.4.5），`{version}` 替换为版本号，`{tag}` 替换为 `release.tag_prefix` + 版本号。
- `release` 里没配的动作不列。没有远程仓库时，只列“本地合并到默认分支”。
- 状态行写 `待关口：D`，**这一轮结束，等人回复**。

## 4. 执行

清空待关口，按人确认的范围依次执行，每一步成功再做下一步，每做完一步在 spec 变更记录里写一句（便于中断后接着做）：
- 推送、开 PR 后，用 `gh pr checks --watch`（或对应平台的命令）等 CI 结果。CI 失败：修复（按 dev-implement 的做法，提交、再推送）；同一个问题失败 3 次就停下，把情况告诉人。
- 发布和部署交给项目自己的方式（`release.*` 配置的命令或 skill），**遵循它自己的规则**（预演、备份、健康检查、回滚）。
- 任何一步失败，不要自行用破坏性手段补救（强推、删 tag、手动改服务器），停下来报告。

## 5. 完成后

- 有上线后检查的，实际验证；有测试浏览器时用它打开线上地址，截图。
- 人选了 `跳过` 时：状态保持“已完成”，变更记录写“关口 D：跳过”，阶段清空。
- 动作执行完：状态改为“已交付”，阶段清空，变更记录写清做了哪些（合并、推送、发布的版本、部署时间），同步索引。
- 告诉人：交付了什么、版本、检查结果、回滚方式。
