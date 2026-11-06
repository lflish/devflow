# 文件放在哪、状态怎么写

## 目录

每个需求一个文件夹，放在配置的 `docs_dir` 下（默认 `docs/changes/`）：

```
docs/changes/
├── README.md                          所有需求的索引
└── 2026-11-02-review-comments/        <创建日期>-<英文短名>
    ├── spec.md          需求（dev-requirements）；标题下第一行是状态行
    ├── design.md        设计 + 方案验证结论（dev-design；规模“小”时没有）
    ├── tasks.md         测试计划、任务、进度、后续（dev-design 写，dev-build 更新）
    ├── decisions.md     裁决记录，只追加（各阶段都写）
    ├── review.md        代码评审（dev-review，每轮覆盖）
    ├── test-report.md   测试结果（dev-test，每轮覆盖）
    ├── verdict.md       独立验证结论（dev-test，每轮覆盖；旧的移到 verdict-history.md）
    ├── evidence/        截图等证据
    └── pages/           要上传到 vibeview 的页面源文件
        ├── prototype/   效果页
        ├── summary/     汇总页（同一个链接，持续更新）
        └── compare-<n>/ 需求走不通时的对比页
```

- 短名用小写英文加连字符，3–5 个词。
- 项目原来有别的需求文档目录（比如 `docs/specs/*.md`），**不要迁移旧文件**。新需求按这里的格式放；`docs_dir` 可以在配置里改。
- `pages/` 放在仓库里，是为了让 vibeview 每次上传同一个路径时更新到同一个链接（见 preview.md）。
- 项目级的文件：`.devflow.yml`（配置）、`docs/secrets-checklist.md`（CI 需要的密钥清单，只写变量名）、项目验证 skill（`.claude/skills/verify-<项目名>/` 或 `.agents/skills/verify-<项目名>/`，见 dev-test）。
- 临时文件放 `.devflow-tmp/`，第一次用时加进 `.git/info/exclude`，不提交。

## 状态行

spec.md 标题下第一行：

```markdown
状态：开发中　阶段：dev-build　待关口：—　等级：L1　规模：标准　创建：2026-11-02　更新：2026-11-03
```

| 字段 | 含义 | 谁来改 |
|------|------|--------|
| **状态** | 需求走到哪了，给人和索引看 | 阶段切换、关口放行时改 |
| **阶段** | 正在做哪个 skill，给 AI 续做用 | 每个阶段开始时改成自己；交接时改成下一个 |
| **待关口** | 正在等用户回复什么：评审、A、B、C、合并、上生产、c<n>、停-n；没有就写 `—` | 发出需要回复的简报时写上；处理完清空 |
| **等级** | 这个需求的自主等级 | 创建时按 config.md 的优先级算出（用户说的 > 本机配置本项目下 > `.devflow.yml` > L1）；用户说“按 L3 跑”时改 |
| 规模、创建、更新 | 微小/小/标准；日期 | dev-requirements 写规模；每次改状态行时更新日期 |

### 状态

| 状态 | 什么时候改成它 |
|------|----------------|
| 草案 | 创建 spec 时 |
| 已确认 | 关口 A 通过 |
| 开发中 | 机器关口 B 放行（规模“小”：关口 A 通过）；返工时也改回它 |
| 测试中 | 可提测、进入 dev-test 时 |
| 已验证 | 机器关口 C 放行（还没合并、没发布） |
| 已合并 | 合并到默认分支后 |
| 已发布 | 上生产完成后 |
| 搁置 | 用户说不做了；写明原因 |

“只暂停这一项”的 `c<n>` 不改状态，只在 tasks.md 里标“阻塞”并写进汇总。

## 索引 `README.md`

```markdown
# 需求索引

| 需求 | 状态 | 等级 | 规模 | 说明 | 等你的事 | 更新 |
|------|------|------|------|------|----------|------|
| [2026-11-02-review-comments](2026-11-02-review-comments/spec.md) | 测试中 | L1 | 标准 | 页面批注和确认签字 | c1 | 2026-11-03 |
```

每次改状态、或等用户的事有变化时同步更新这一行。“等你的事”一栏让用户一眼看到所有需求里等他的事。

## `decisions.md` 文件头

```markdown
# 裁决记录 · <需求名>

规则见 dev-workflow/references/decisions.md。只追加，不修改旧行。

| # | 阶段 | 决定 | 类型 | 依据 | 理由 | 放弃的选项 | 定错的代价 | 处理结果 |
|---|------|------|------|------|------|------------|------------|----------|
```

## 编号

整个需求里统一：

| 前缀 | 是什么 | 在哪 |
|------|--------|------|
| R1、R1.1 | 需求、验收场景 | spec |
| P1 | 前提 | spec |
| E1 | 扩展候选 | 需求评审消息、spec |
| Q1 | 问题 | 需求评审消息、关口 A |
| H1 | 假设（AI 定的） | spec |
| T1 | 任务 | tasks |
| d1 / c1 | 口味型 / 只有人能做的决定 | decisions |
| X1 | 测试中发现的问题 | test-report、verdict |
| V1 | 前置验证 | design |

## git

- **dev-requirements 建文件夹时**，如果当前在默认分支（main/master）上，新建本地分支 `change/<短名>` 并切过去。建本地分支、本地提交、建 worktree 都不需要确认。
- **每个阶段结束时**，提交本阶段的产物（文档、代码、`.dview.json`），提交信息写明阶段，比如 `docs(review-comments): spec and prototype`。
- 推送、开 PR、合并、上生产都在发布阶段处理（dev-release）。
