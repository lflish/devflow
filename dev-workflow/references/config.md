# 配置和环境

分两处：

| 文件 | 放什么 | 进仓库吗 |
|------|--------|----------|
| `.devflow.yml`（项目根目录） | 技术栈和约定、命令、需求目录、自主等级、有哪些环境和各自的数据规则、各阶段的额外规则、发布方式 | 进。**地址只写变量名，不写真实地址** |
| `~/.config/devflow/config.yml`（本机） | 和机器有关的（测试浏览器、vibeview、验证模型），以及**每个人在每个项目里的环境地址**（按仓库根目录分组） | 不进 |

密钥和账号只放环境变量，两个文件里都只写变量名。

## 项目配置 `.devflow.yml`

```yaml
context: |                      # 每个阶段都会读：技术栈、约定、要注意的事
  Node 20 + Express，SQLite（better-sqlite3）；测试用 node --test。
  界面文案用中文；不引入前端框架。

docs_dir: docs/changes          # 默认 docs/changes
autonomy: L1                    # L1 / L2 / L3，默认 L1

commands:                       # 不写就从 package.json / Makefile 等推断
  install: npm ci
  lint: npm run lint
  test: npm test
  build: npm run build
  e2e: npx playwright test

environments:                   # 有哪些环境；地址一律写变量名
  local:
    start: npm run dev          # 远程浏览器要访问时，服务需监听 0.0.0.0
    url_env: MYPROJ_LOCAL_URL           # 变量名带上项目名，避免一个全局变量覆盖所有项目
    default_url: http://localhost:3000   # 只允许 localhost 这类不含真实主机的默认值
    data: 可随意读写，可重置
  staging:
    url_env: MYPROJ_STAGING_URL
    deploy: "使用 $deploy-view 部署到 staging"
    data: 共享环境：只能用 e2e- 开头的测试数据，用完清理
    account_env: [STAGING_TEST_USER, STAGING_TEST_PASS]
  production:
    url_env: MYPROJ_PROD_URL
    data: 只读：只做上线后检查，不提交表单、不写数据

test:
  e2e_env: local                # 开发时跑浏览器测试的环境
  verify_env: staging           # 机器关口 C 独立验证的环境；用户说过没有这个环境（url: none）时用 e2e_env

rules:                          # 只对某个阶段生效的额外规则
  requirements: []
  design: []
  build: []
  test: []

release:
  bump: patch                   # 默认升哪一位：patch / minor / major
  tag_prefix: v
  # {version} 是不带前缀的版本号（1.4.5），{tag} 是标签（v1.4.5）
  publish: "使用 $release 发布 {version}"
  production: "使用 $deploy-view 部署 {tag}"
  post_check: "打开线上首页，确认版本号是 {version}"
```

## 本机配置 `~/.config/devflow/config.yml`

```yaml
browser:
  cdp_url_env: DEVFLOW_BROWSER_CDP   # 测试浏览器 CDP 地址所在的环境变量
  host: 192.168.1.20                 # 浏览器那台机器访问“这台机器”用的地址
  # ssh_host: browser-box            # 可选：访问不到时，在这台机器上建反向隧道
preview:
  vibeview: auto                     # auto：装了 dview 且配置了 DVIEW_URL 就用；off：不用
verify:
  models: [codex, claude, same]      # 验证者候选，按顺序探测；可写 codex:<模型>、claude:<模型> 指定同级别模型（见 verification.md）
  probe_timeout: 60                  # 探测限时（秒）
  run_timeout: 1800                  # 一次验证限时（秒）

projects:
  /home/you/github/myproj:           # 键是仓库根目录的绝对路径
    autonomy: L2                     # 可选：这台机器上覆盖项目默认等级
    environments:
      local:   { url: http://192.168.1.20:3000 }
      staging: { url: https://staging.internal.example.com }
```

本机配置可以写真实地址，因为它不进任何仓库。

## 读取规则

1. 读本机配置顶层，以及 `projects` 下键等于当前仓库根目录（`git rev-parse --show-toplevel`）的那一节。
2. `commands` 里没写的，按项目文件推断：`package.json` 的 scripts、`Makefile`、`pyproject.toml`、`go.mod`、`Cargo.toml`、已有 CI 里的命令。推断出的命令记一行到 `decisions.md`（机械型）。
3. **环境地址**：按顺序取第一个有值的：
   1. 环境变量（`url_env` 指的那个）；
   2. 本机配置里本项目下 `environments.<名字>.url`；值是 `none` 表示“用户说过没有这个环境”，此时这个环境不可用（不是一个地址）；
   3. `.devflow.yml` 的 `default_url`（只有 local 有，没写时为 `http://localhost:3000`）。

   都没有 → 这个环境缺地址，按下面“缺地址时”处理。
4. **给测试浏览器用的地址**：测试浏览器在另一台机器上时，它的 localhost 不是这台机器。所以取到的地址如果是 `localhost` 或 `127.0.0.1`，而本机配置有 `browser.host`，浏览器访问时把主机换成 `browser.host`（端口和路径不变）。这台机器上的命令（启动、健康检查）仍用原地址。
5. **自主等级**：用户在这个需求里说的 > 本机配置本项目下的 `autonomy` > `.devflow.yml` 的 `autonomy` > L1。建 spec 时按这个顺序算出来写进状态行，之后以状态行为准。
6. `release.bump` 默认 `patch`，`tag_prefix` 默认 `v`。

## 缺地址时

用到某个环境（比如 `verify_env: staging`）却取不到地址时，**一次性**问用户所有缺的地址（允许问人的例外之一，不限第一次），写进本机配置本项目下，之后不再问：
- 用户给了地址 → 写 `url: <地址>`；
- 用户说没有这个环境 → 写 `url: none`；`verify_env` 不可用时退回 `e2e_env`，在汇总里说明。

本机配置文件或其中本项目的一节不存在时，创建它，只写用户给的值。

## 项目还没有 `.devflow.yml` 时

不要停下来问。读项目推断一份草稿：技术栈、命令、测试框架、已有的文档目录、CI、能看出来的环境（只写变量名）。草稿写到项目根目录，在关口 A 的“其他”里写一句“新建了 .devflow.yml，请看一下”。
