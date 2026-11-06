// devflow-browser.js —— 打开测试浏览器：本机无头 / 固定 CDP 地址 / 云浏览器（Steel、Kernel）。
// 复制到项目的 tests/e2e/ 下，由 fixtures.js 和检查脚本共用。不依赖任何 SDK，只用 Node 18+ 自带的 fetch。
//
// 环境变量：
//   DEVFLOW_BROWSER_PROVIDER  local | cdp | steel | kernel；不设时：有 DEVFLOW_BROWSER_CDP 就是 cdp，否则 local
//   DEVFLOW_BROWSER_CDP       provider=cdp 时的连接地址
//   STEEL_API_KEY / KERNEL_API_KEY  云浏览器的 key（只放环境变量，不写进任何文件）
//   DEVFLOW_BROWSER_KEY_ENV   key 放在别的变量名里时，写那个变量名（例如 CHROME_KEY）
//   DEVFLOW_BROWSER_TIMEOUT_MIN     云浏览器会话的最长分钟数，默认 14（Steel 免费档上限 15 分钟）
//   DEVFLOW_CHROME_PATH       provider=local 时用指定的 Chrome（例如系统装的 /usr/bin/google-chrome），不用 Playwright 下载的
const { chromium } = require('@playwright/test');

function provider() {
  return process.env.DEVFLOW_BROWSER_PROVIDER || (process.env.DEVFLOW_BROWSER_CDP ? 'cdp' : 'local');
}

// 报错信息里可能带着含 key 的连接地址，抛出前先把 key 换掉
function scrub(e, ...secrets) {
  let msg = String((e && e.message) || e);
  for (const x of secrets) if (x) msg = msg.split(x).join('***');
  return new Error(msg);
}

function need(name) {
  const alt = process.env.DEVFLOW_BROWSER_KEY_ENV;
  const v = process.env[name] || (alt && /_API_KEY$/.test(name) ? process.env[alt] : undefined);
  if (!v) throw new Error(`缺少环境变量 ${name}`);
  return v;
}

// 返回 { browser, liveUrl, close }。close() 断开连接并释放云端会话（停止计费）。
async function openBrowser() {
  const p = provider();
  const minutes = Number(process.env.DEVFLOW_BROWSER_TIMEOUT_MIN || 14);

  if (p === 'local') {
    const exe = process.env.DEVFLOW_CHROME_PATH;
    const browser = await chromium.launch(exe ? { executablePath: exe } : {});
    return { browser, liveUrl: null, close: () => browser.close() };
  }

  if (p === 'cdp') {
    const browser = await chromium.connectOverCDP(need('DEVFLOW_BROWSER_CDP'));
    // 对连接上的浏览器，close() 只断开，不会关掉对方的浏览器
    return { browser, liveUrl: null, close: () => browser.close() };
  }

  if (p === 'steel') {
    const key = need('STEEL_API_KEY');
    const res = await fetch('https://api.steel.dev/v1/sessions', {
      method: 'POST',
      headers: { 'steel-api-key': key, 'content-type': 'application/json' },
      body: JSON.stringify({ timeout: minutes * 60 * 1000 }),
    });
    if (!res.ok) throw scrub(`Steel 创建会话失败：HTTP ${res.status} ${await res.text()}`, key);
    const s = await res.json();
    const release = () => fetch(`https://api.steel.dev/v1/sessions/${s.id}/release`, {
      method: 'POST', headers: { 'steel-api-key': key },
    }).catch(() => {});
    let browser;
    try {
      browser = await chromium.connectOverCDP(`wss://connect.steel.dev?apiKey=${key}&sessionId=${s.id}`);
    } catch (e) { await release(); throw scrub(e, key); }
    return { browser, liveUrl: s.debugUrl || null, close: async () => { await browser.close().catch(() => {}); await release(); } };
  }

  if (p === 'kernel') {
    const key = need('KERNEL_API_KEY');
    const res = await fetch('https://api.onkernel.com/browsers', {
      method: 'POST',
      headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
      body: JSON.stringify({ timeout_seconds: 300 }),
    });
    if (!res.ok) throw scrub(`Kernel 创建浏览器失败：HTTP ${res.status} ${await res.text()}`, key);
    const b = await res.json();
    const del = () => fetch(`https://api.onkernel.com/browsers/${b.session_id}`, {
      method: 'DELETE', headers: { authorization: `Bearer ${key}` },
    }).catch(() => {});
    let browser;
    try { browser = await chromium.connectOverCDP(b.cdp_ws_url); } catch (e) { await del(); throw scrub(e, key, b.cdp_ws_url); }
    // Kernel：browser.close() 不会删除云端浏览器，必须调用删除接口
    return { browser, liveUrl: b.browser_live_view_url || null, close: async () => { await browser.close().catch(() => {}); await del(); } };
  }

  throw new Error(`不认识的 DEVFLOW_BROWSER_PROVIDER：${p}`);
}

module.exports = { openBrowser, provider };

// 直接运行时做一次连接检查：node tests/e2e/devflow-browser.js [要打开的地址]
if (require.main === module) {
  (async () => {
    const { browser, liveUrl, close } = await openBrowser();
    try {
      console.log('provider', provider(), 'version', browser.version());
      const url = process.argv[2];
      if (url) {
        const page = await (await browser.newContext()).newPage();
        const resp = await page.goto(url, { timeout: 30000 });
        console.log('open', url, resp && resp.status(), await page.title());
      }
      if (liveUrl) console.log('live view 已生成（不打印：拿到链接的人都能操作这个浏览器）');
    } finally { await close(); }
  })().catch((e) => { console.error(String(e && e.message || e)); process.exit(1); });
}
