# 配置

分两层：

| 文件 | 放什么 | 进仓库吗 |
|------|--------|----------|
| `.devflow.yml`（项目根目录） | 技术栈和约定、命令、需求目录、各阶段的额外规则、发布方式 | 进 |
| `~/.config/devflow/config.yml`（本机） | 和这台机器有关的：浏览器怎么连、浏览器怎么访问到这台机器、是否用 vibeview | 不进 |

**项目文件里不写任何机器相关的值**（IP、主机名、密钥、token）；它们放在本机配置或环境变量里。

## 项目配置 `.devflow.yml`

```yaml
# 每个阶段都会读：技术栈、约定、要注意的事
context: |
  Node 20 + Express，SQLite（better-sqlite3）；测试用 node --test。
  界面文案用中文；不引入前端框架。

docs_dir: docs/changes          # 需求文件夹放哪，默认 docs/changes

commands:                       # 不写就从 package.json / Makefile 等推断
  install: npm ci
  lint: npm run lint
  test: npm test
  build: npm run build
  e2e: npx playwright test      # 浏览器测试
  dev: npm run dev              # 浏览器测试前启动本地服务；远程浏览器要访问时，服务需监听 0.0.0.0
  dev_url: http://localhost:3000

rules:                          # 只对某个阶段生效的额外规则
  requirements:
    - 涉及权限的需求必须有“无权限时”的场景
  implement:
    - 不新增运行时依赖，除非 spec 写明
  test:
    - 每个页面都要检查手机宽度

release:
  bump: patch                   # 默认升哪一位：patch / minor / major
  tag_prefix: v                 # 标签 = 前缀 + 版本号，例如 v1.4.5
  # 发布和部署交给项目自己的方式：一条命令，或一句调用项目 skill 的话。
  # {version} 是不带前缀的版本号（1.4.5），{tag} 是标签（v1.4.5）。
  publish: "使用 $release 发布 {version}"
  staging: ""
  production: "使用 $deploy-view 部署 {tag}"
  post_check: "打开线上首页，确认版本号是 {version}"
```

## 本机配置 `~/.config/devflow/config.yml`

```yaml
browser:
  cdp_url_env: DEVFLOW_BROWSER_CDP   # 存 CDP 地址的环境变量名；值形如 http://10.0.0.5:9222
  host: 192.168.1.20                 # 浏览器那台机器访问“这台机器”用的地址（局域网 / Tailscale）
  # ssh_host: browser-box            # 可选：浏览器访问不到这台时，用 SSH 反向隧道打通（见 dev-test 的 browser.md）
preview:
  vibeview: auto                     # auto：装了 dview 且配置了 DVIEW_URL 就用；off：不用
```

## 读取规则

1. 先读本机配置，再读项目配置。
2. `commands` 里没写的，按项目文件推断：`package.json` 的 scripts、`Makefile`、`pyproject.toml`、`go.mod`、`Cargo.toml`、已有 CI 里的命令。推断出的命令记一行到 `decisions.md`（机械型）。
3. **被测地址 `base_url`**（浏览器测试打开的地址）：
   - 有环境变量 `DEVFLOW_BASE_URL` 就用它；
   - 否则，有本机 `browser.host` 时，把 `commands.dev_url` 里的主机换成它（`http://localhost:3000` → `http://192.168.1.20:3000`）；
   - 否则就是 `commands.dev_url`（只在浏览器和服务在同一台机器时成立）。
4. `release.bump` 没写时默认 `patch`，`tag_prefix` 默认 `v`。

## 项目还没有 `.devflow.yml` 时

不要停下来问。读项目推断一份草稿：技术栈、命令、测试框架、已有的文档目录和 CI。草稿写到项目根目录，在第一个关口简报的“其他”里写一句“新建了 .devflow.yml，请看一下命令对不对”。

本机配置不存在时，按默认值处理（没有浏览器地址就按 browser.md 的退路），不要替人创建。
