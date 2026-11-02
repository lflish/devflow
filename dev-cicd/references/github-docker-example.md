# 示例：GitHub Actions + 单台 Linux/Docker 部署

> **这是示意，不能直接用。** 照着改之前要补齐：CI 里构建并推送以提交 sha 为标签的镜像（部署时拉的就是它）；
> CI 里加上浏览器测试和失败截图上传（见 dev-cicd 第 2 步）；`APP_NAME`、`DOCKER_REGISTRY` 等变量在 compose 和脚本里要一致地导出。

原版 dev-cicd 的完整示例，项目没有自己的 CI 和部署方式时参考。命令要换成项目实际的（见 .devflow.yml 的 commands）。

## 生成 GitHub Actions 工作流

在 `.github/workflows/` 下创建 CI 配置文件，默认结构如下：

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup runtime
        # 根据项目语言选择对应 setup action
        uses: actions/setup-node@v4  # 示例：Node.js
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Lint
        run: npm run lint
        # lint 失败即红，阻断后续步骤

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup runtime
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Test
        run: npm test
      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup runtime
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Build
        run: npm run build
      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
```

**根据实际项目语言调整**：将 setup action、安装命令、lint/test/build 命令替换为项目实际使用的工具链。核心原则不变：lint → test → build 三段串行，任一失败即终止。

## 密钥与环境变量管理

严格遵守以下规则：

1. **绝不将密钥写入代码或配置文件入库**。在工作流中通过 `${{ secrets.XXX }}` 引用。
2. 列出本项目需要的所有密钥和环境变量，生成一份清单文件 `docs/secrets-checklist.md`：

```markdown
# 密钥与环境变量清单

以下变量需在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置。

| 变量名 | 用途 | 环境 | 示例值格式 |
|--------|------|------|-----------|
| DEPLOY_HOST | 部署目标服务器地址 | staging / production | 192.168.1.100 |
| DEPLOY_SSH_KEY | SSH 私钥，用于部署连接 | staging / production | -----BEGIN OPENSSH... |
| DEPLOY_USER | 部署用户名 | staging / production | deploy |
| DOCKER_REGISTRY | Docker 镜像仓库地址 | all | registry.example.com |
| DOCKER_USER | 镜像仓库用户名 | all | myuser |
| DOCKER_PASS | 镜像仓库密码 | all | (密码) |
```

3. 对于需要区分环境的变量，使用 GitHub Environments 功能（staging / production），在工作流中通过 `environment:` 字段引用。

## 生成部署脚本

创建 `scripts/deploy.sh`，按单台 Linux + Docker 场景编写，满足以下要求：

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# 部署脚本 — 单台 Linux + Docker
# 用法: ./scripts/deploy.sh <环境> <镜像标签>
#   环境: staging | production
#   镜像标签: 如 v1.2.3 或 git commit sha
# ============================================================

ENV="${1:?用法: $0 <staging|production> <镜像标签>}"
TAG="${2:?用法: $0 <staging|production> <镜像标签>}"

# ---------- 配置 ----------
APP_NAME="myapp"                         # 根据项目实际名称替换
COMPOSE_FILE="docker-compose.${ENV}.yml"
BACKUP_DIR="/opt/${APP_NAME}/backups"
HEALTH_URL="http://localhost:8080/health" # 根据项目实际端口和路径替换
HEALTH_TIMEOUT=60                         # 健康检查超时秒数
ROLLBACK_TAG=""

# ---------- 前置检查 ----------
if [[ "$ENV" != "staging" && "$ENV" != "production" ]]; then
  echo "错误: 环境必须是 staging 或 production" >&2
  exit 1
fi

# 生产部署的确认在关口 D 已经做过；脚本里不做交互确认（CI/ssh 里没有终端，read 会读到空值）。
# 用环境变量显式确认，缺少时失败退出（非 0），而不是“成功地什么都没做”。
if [[ "$ENV" == "production" && "${CONFIRM:-}" != "yes" ]]; then
  echo "错误: 部署生产环境需要设置 CONFIRM=yes" >&2
  exit 1
fi

# ---------- 备份 ----------
echo ">>> 备份当前版本..."
mkdir -p "$BACKUP_DIR"
CURRENT_TAG=$(docker inspect --format='{{.Config.Image}}' "${APP_NAME}" 2>/dev/null | awk -F: '{print $2}') || true
if [[ -n "$CURRENT_TAG" ]]; then
  ROLLBACK_TAG="$CURRENT_TAG"
  echo "当前运行版本: $ROLLBACK_TAG（回滚可用）"
  # 导出数据库快照（若适用，根据项目调整）
  # docker exec ${APP_NAME}-db pg_dump -U postgres mydb > "$BACKUP_DIR/db-$(date +%Y%m%d%H%M%S).sql"
fi

# ---------- 拉取新镜像 ----------
echo ">>> 拉取镜像 ${APP_NAME}:${TAG}..."
TAG="$TAG" docker compose -f "$COMPOSE_FILE" pull

# ---------- 部署 ----------
echo ">>> 启动新版本..."
TAG="$TAG" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# ---------- 健康检查 ----------
echo ">>> 等待健康检查通过（超时 ${HEALTH_TIMEOUT}s）..."
elapsed=0
while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
  if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo "健康检查通过！"
    break
  fi
  sleep 2
  elapsed=$((elapsed + 2))
done

if [[ $elapsed -ge $HEALTH_TIMEOUT ]]; then
  echo "错误: 健康检查超时！" >&2

  # ---------- 自动回滚 ----------
  if [[ -n "$ROLLBACK_TAG" ]]; then
    echo ">>> 自动回滚到版本 $ROLLBACK_TAG..."
    TAG="$ROLLBACK_TAG" docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
    echo "已回滚到 $ROLLBACK_TAG。请排查问题。"
  else
    echo "无可用回滚版本，请手动处理。" >&2
  fi

  # 报警（替换为实际的通知方式）
  echo ">>> 发送部署失败报警..."
  # curl -X POST "$ALERT_WEBHOOK" -d "{\"text\":\"部署失败: ${APP_NAME}:${TAG} on ${ENV}\"}"
  exit 1
fi

# ---------- 记录发布 ----------
RELEASE_LOG="/opt/${APP_NAME}/releases.log"
cat >> "$RELEASE_LOG" <<EOF
---
版本: ${TAG}
环境: ${ENV}
时间: $(date '+%Y-%m-%d %H:%M:%S')
变更: ${CHANGE_SUMMARY:-"见 git log"}
回滚: TAG="${ROLLBACK_TAG}" docker compose -f ${COMPOSE_FILE} up -d --remove-orphans
EOF
echo ">>> 发布记录已写入 $RELEASE_LOG"

echo ">>> 部署完成: ${APP_NAME}:${TAG} → ${ENV}"
```

**脚本核心原则说明**：

| 原则 | 脚本中的体现 |
|------|-------------|
| **幂等** | `docker compose up -d` 本身幂等，重复执行结果一致 |
| **部署前备份** | 记录当前运行版本标签，可选导出数据库快照 |
| **部署后健康检查** | 循环轮询 /health 端点，超时判定失败 |
| **检查失败自动回滚** | 健康检查超时后自动用上一版本重新启动 |
| **生产需人工确认** | `production` 环境部署前需输入 `yes` 确认 |
| **发布记录** | 每次部署追加写入 releases.log |

## 生成部署用 Docker Compose 模板

为测试和生产环境各生成一份 compose 文件：

```yaml
# docker-compose.staging.yml
services:
  app:
    image: ${DOCKER_REGISTRY}/${APP_NAME}:${TAG}
    container_name: ${APP_NAME}
    restart: unless-stopped
    ports:
      - "8080:8080"
    env_file:
      - .env.staging
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s

# docker-compose.production.yml — 同结构，env_file 改为 .env.production
# 生产环境可额外增加资源限制：
#   deploy:
#     resources:
#       limits:
#         memory: 512M
#         cpus: '1.0'
```

## 添加部署工作流（CD）

在 `.github/workflows/` 下创建部署工作流：

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  workflow_run:
    workflows: ["CI"]
    branches: [main, dev]
    types: [completed]

jobs:
  deploy-staging:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'dev'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/${{ vars.APP_NAME }}
            git pull origin dev
            ./scripts/deploy.sh staging ${{ github.event.workflow_run.head_sha }}

  deploy-production:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    runs-on: ubuntu-latest
    environment: production  # GitHub Environment 保护规则提供人工审批
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/${{ vars.APP_NAME }}
            git pull origin main
            CONFIRM=yes CHANGE_SUMMARY="$(git log --oneline -5)" ./scripts/deploy.sh production ${{ github.event.workflow_run.head_sha }}
```

**关键设计**：
- CI 成功才触发 CD（`workflow_run` + `conclusion == 'success'`）。
- staging 由 dev 分支自动触发。
- production 由 main 分支触发，但通过 GitHub Environment 保护规则 (Required reviewers) 实现人工确认点。

