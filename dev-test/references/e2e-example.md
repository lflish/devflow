# 浏览器端到端测试：写法示例

用 Playwright Test。项目里已经有别的 E2E 框架（Cypress 等）时，跟随项目，但要能连远程浏览器。
下面的配置和写法已在“本机无头浏览器”“远程 CDP 浏览器”和 Steel 云浏览器上实测通过。

## 安装（项目还没有时）

```bash
npm i -D @playwright/test
# 只在需要本机浏览器时才装：npx playwright install chromium
```

`.devflow.yml` 里写上 `commands.e2e: npx playwright test`。

## 配置 `playwright.config.js`

```js
const { defineConfig } = require('@playwright/test');

const remote = !!process.env.DEVFLOW_BROWSER_CDP
  || ['cdp', 'steel', 'kernel'].includes(process.env.DEVFLOW_BROWSER_PROVIDER);

module.exports = defineConfig({
  testDir: 'tests/e2e',
  // 远程浏览器隔着网络更慢；机器很慢时用 DEVFLOW_E2E_TIMEOUT_MS 放宽（比如 1 核小内存的服务器）
  timeout: Number(process.env.DEVFLOW_E2E_TIMEOUT_MS) || (remote ? 60_000 : 30_000),
  workers: remote ? 1 : undefined,     // 远程和云浏览器串行跑：少占会话，也少花钱
  use: {
    baseURL: process.env.DEVFLOW_BASE_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
    // 远程时录 trace 会明显变慢；很慢的机器上本机也会卡住，用 DEVFLOW_E2E_TRACE=off 关掉
    trace: process.env.DEVFLOW_E2E_TRACE || (remote ? 'off' : 'retain-on-failure'),
  },
});
```

本机运行报 `Executable doesn't exist` 时，说明本机浏览器和 `@playwright/test` 的版本对不上，执行 `npx playwright install chromium` 后重跑；或者设 `DEVFLOW_CHROME_PATH` 用系统装的 Chrome。

机器很慢（比如 1 核、内存不到 2 GB）时，测试可能超时或卡住：设 `DEVFLOW_E2E_TIMEOUT_MS=120000`、`DEVFLOW_E2E_TRACE=off`。实测在 1 核 2 GB 的服务器上，打开 trace 会卡住，关掉后一个测试约 45 秒。

CI 里要自动启动被测服务时，加上 `webServer: { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: true }`。

## 打开浏览器 `tests/e2e/devflow-browser.js`

从 dev-test 的 `references/devflow-browser.js` 原样复制到项目的 `tests/e2e/`，提交进仓库。它按 `DEVFLOW_BROWSER_PROVIDER` 打开本机无头、固定 CDP 地址或云浏览器（Steel、Kernel），云浏览器会自动创建和释放会话。不要在项目里改它；需要改的话改 skill 里的那份，再复制过去。

## 连接和截图 `tests/e2e/fixtures.js`

```js
const path = require('path');
const { test: base, expect } = require('@playwright/test');
const { openBrowser } = require('./devflow-browser');

// 每个测试进程开一个浏览器（本机 / CDP / 云浏览器），结束时断开并释放云端会话。
// 每个测试仍然有自己独立的 context，互不影响。
const test = base.extend({
  browser: [async ({}, use) => {
    const { browser, close } = await openBrowser();
    try { await use(browser); } finally { await close(); }
  }, { scope: 'worker' }],

  // 验收证据：设置了 DEVFLOW_EVIDENCE_DIR 时才保存截图（需求流程里由 dev-test 设置）
  evidence: async ({ page }, use) => {
    await use(async (name) => {
      const dir = process.env.DEVFLOW_EVIDENCE_DIR;
      if (dir) await page.screenshot({ path: path.join(dir, `${name}.png`), fullPage: true });
    });
  },
});

module.exports = { test, expect };
```

## 测试：一个场景一个测试，名字带场景编号

```js
// tests/e2e/review-comments.spec.js
const { test, expect } = require('./fixtures');

test('R1.3 访问码过期后打开评论页', async ({ page, evidence }) => {
  // 假如：一个访问码已过期的页面（用测试数据准备接口或种子数据构造，不依赖手工状态）
  await page.goto('/v/test-expired');

  // 那么：显示过期提示，不显示评论
  await expect(page.getByText('访问码已过期')).toBeVisible();
  await expect(page.getByTestId('comment-list').locator('li')).toHaveCount(0);

  await evidence('R1.3');
});
```

## 要点

- **定位元素**：优先用 `getByRole`、`getByText`、`getByTestId`，不要用会随样式变化的 CSS 选择器。需要时在实现里加 `data-testid`。
- **等待**：用 `expect(...).toBeVisible()` 这类会自动等待的断言，不用 `waitForTimeout` 固定等待。
- **数据**：每个测试自己准备数据（调接口、种子脚本），不依赖别的测试留下的状态。
- **断言要能失败**：至少一个断言针对场景里的“那么”；只检查“页面打开了”不算测试。
- **截图**：关键场景最后调用 `evidence('<场景编号>')`，验收页会用到。测试代码里不写死任何需求文件夹的路径。
- **运行**：见 browser.md 的“运行脚本化测试”。
