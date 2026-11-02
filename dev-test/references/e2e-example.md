# 浏览器端到端测试：写法示例

用 Playwright Test。项目里已经有别的 E2E 框架（Cypress 等）时，跟随项目，但要能连远程浏览器。
下面的配置和写法已在“远程 CDP 浏览器”和“本机无头浏览器”两种情况下实测通过。

## 安装（项目还没有时）

```bash
npm i -D @playwright/test
# 只在需要本机浏览器时才装：npx playwright install chromium
```

`.devflow.yml` 里写上 `commands.e2e: npx playwright test`。

## 配置 `playwright.config.js`

```js
const { defineConfig } = require('@playwright/test');

const remote = !!process.env.DEVFLOW_BROWSER_CDP;

module.exports = defineConfig({
  testDir: 'tests/e2e',
  timeout: remote ? 60_000 : 30_000,   // 远程浏览器隔着网络，开关页面更慢
  workers: remote ? 1 : undefined,     // 远程浏览器只有一个，串行跑
  use: {
    baseURL: process.env.DEVFLOW_BASE_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
    trace: remote ? 'off' : 'retain-on-failure',  // 远程时录 trace 会明显变慢
  },
});
```

本机运行报 `Executable doesn't exist` 时，说明本机浏览器和 `@playwright/test` 的版本对不上，执行 `npx playwright install chromium` 后重跑。

CI 里要自动启动被测服务时，加上 `webServer: { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: true }`。

## 连接远程或本机浏览器，以及截图 `tests/e2e/fixtures.js`

```js
const path = require('path');
const { test: base, expect, chromium } = require('@playwright/test');

// 有 CDP 地址就连远程浏览器，没有就在本机启动无头浏览器。
// 每个测试仍然有自己独立的 context，互不影响。
const test = base.extend({
  browser: [async ({}, use) => {
    const cdp = process.env.DEVFLOW_BROWSER_CDP;
    const browser = cdp
      ? await chromium.connectOverCDP(cdp)
      : await chromium.launch();
    await use(browser);
    await browser.close(); // 远程时只断开连接，不会关掉对方的浏览器
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
