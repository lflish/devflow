# dev-* skills：AI 辅助开发流程

一套给 Claude Code 和 Codex 用的开发流程 skills。目标是**让人只在几个关口集中投入注意力**：

| 关口 | 人看什么 |
|------|----------|
| A 需求确认 | spec（要做 / 不做 / 验收场景 / AI 的假设）+ vibeview 效果页 |
| B 方案确认 | 一页方案简报：方案、待定的决定、任务、风险 |
| C 验收 | 验收页：每个场景的结果和浏览器截图、执行中的决定、遗留问题 |
| D 上线确认 | 要执行的推送、PR、发布、部署，一次确认 |

关口之间 AI 自己推进：只有一个合理答案的决定直接定；两个方案都行的先按推荐定、到下一个关口给人看；要改人定下的东西的，绝不自己改，留给关口。只有不可逆、安全敏感、对外发布、需求根本做不了这 4 种情况才中途停下。

## 阶段

| skill | 做什么 |
|-------|--------|
| `dev-workflow` | 总纲：判断阶段、读配置、共用规则（`references/`） |
| `dev-requirements` | 先读代码；需求评审（前提挑战、产品方案、范围模式）；一条带推荐答案的消息问完；写带验收场景的 spec；新人通读检查；效果页 → 关口 A |
| `dev-design` | 选方案、接口、数据，前置验证，独立工程评审 |
| `dev-plan` | 测试计划 + 任务（每个任务挂测试）→ 关口 B |
| `dev-implement` | 逐任务先写测试再实现，裁决并记录，不中途停 |
| `dev-test` | 单元/集成 + 远程浏览器端到端测试 + 探索式检查，截图留证 |
| `dev-review` | 独立子 agent 评审，明确错误直接修，其余交关口 |
| `dev-accept` | 核对完整性、正确性、一致性，生成验收页 → 关口 C |
| `dev-cicd` | 按配置生成 CI，对外动作一次确认（关口 D），部署交给项目自己的方式 |

借鉴来源：superpowers（先查后问、新人通读、执行中裁决不停等、计划粒度）、Spec Kit（缺口清单、最多 5 题带推荐、假设）、OpenSpec（需求加场景、只写行为、验收三项核对、项目配置）、gstack（需求评审：前提挑战、建设性改写、最小可行方案、四种范围模式、理想状态对照；决定三分类、决策原则、一页简报、统一提问格式、真实浏览器 QA、修复前先写回归测试、评审时检查测试是否被放松）。

## 安装

```bash
./install.sh            # 软链接到 ~/.claude/skills 和 ~/.codex/skills
./install.sh --status   # 查看安装情况
./install.sh --uninstall
```

- 软链接安装：改了仓库里的文件立即生效（已打开的会话要重开才会重新读取 skill 列表）。
- 目标位置已有同名的旧 dev-* 目录（比如之前手动复制进去的旧版）时，会先移到 `~/.cache/devflow-backup/<时间>/`，不会直接删除。

## 每台机器配置一次

1. 本机配置：`mkdir -p ~/.config/devflow && cp templates/machine-config.yml ~/.config/devflow/config.yml`，填上 `browser.host`（浏览器那台机器访问这台机器用的局域网或 Tailscale 地址）。
2. 浏览器：在 shell 配置里设置 `export DEVFLOW_BROWSER_CDP=http://<浏览器主机>:9222`。
   - 远程 Chrome 用 `--remote-debugging-port=9222 --user-data-dir=<单独目录>` 启动（新版 Chrome 不允许对默认配置目录开调试端口）。Chrome 默认只监听浏览器那台的 127.0.0.1，要从这台访问，用 SSH 隧道（在这台执行 `ssh -N -L 9222:localhost:9222 <浏览器主机>`，此时地址是 `http://localhost:9222`）或在那台做端口转发。也可以用 neko、steel-browser 等直接提供 CDP 的服务。
   - 这个端口能完全控制浏览器，只在内网或 Tailscale 上开放。
3. 可选，让 AI 能像人一样点页面（探索式检查）：
   ```bash
   claude mcp add -s user playwright -- npx @playwright/mcp@latest --cdp-endpoint "$DEVFLOW_BROWSER_CDP"
   codex mcp add playwright -- npx @playwright/mcp@latest --cdp-endpoint "$DEVFLOW_BROWSER_CDP"
   ```
   添加时地址会被固定下来，浏览器地址变了要重新添加。
4. vibeview：装好 `dview`，设置 `DVIEW_URL` 和 `DVIEW_TOKEN`。没有也能用，页面会只留在本地。

## 每个项目

不用预先做什么。第一次在项目里提需求时，AI 会读项目生成 `.devflow.yml` 草稿，在第一个关口请你确认。模板见 `templates/devflow.yml`。项目文件里不写 IP、主机名、密钥这类机器相关的值。

需求文件放在 `docs/changes/<日期>-<短名>/`：`spec.md`、`design.md`、`tasks.md`、`decisions.md`、`test-report.md`、`review.md`、`evidence/`、`pages/`。spec 第一行下面的状态行记录“状态 / 阶段 / 待关口”，换了会话也能从断点接着做。

## 用法

- 提需求：“我想给 xxx 加一个 …”（触发 dev-requirements）
- 接着做：“继续”（dev-workflow 按状态行判断从哪里接着做）
- 关口回复：`all` 全部按默认；`d2 B`、`c1 同意`、`Q3 B`、`H2 改为 …`、`E1 加入`、`问 d3`、`重做 <原因>`
- 单独用某个阶段：“评审一下这段代码”“跑一下测试”——找不到需求文件夹时只做这一步，不会自动往下走
