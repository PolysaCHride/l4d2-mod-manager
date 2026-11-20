/**
 * 截图 / 布局校验脚本。
 * 用法：
 *   1. 在 docs/redesign 目录起一个静态服务：python -m http.server 8138
 *   2. 起带调试端口的 Chrome：
 *      chrome --headless=new --remote-debugging-port=9224 --user-data-dir=<临时目录> about:blank
 *   3. 在仓库根目录运行：node docs/redesign/final/capture.js
 */
const fs = require('fs');

const BASE = 'http://127.0.0.1:8138/final/preview.html';
const OUT = 'docs/redesign/final/';
const WIDTHS = [1440, 1280, 1100];
const RAILS = [['survivor', 'preview.png'], ['all', 'preview-all.png'], ['weapon', 'preview-weapon.png'], ['other', 'preview-other.png']];

async function main() {
  const targets = await (await fetch('http://127.0.0.1:9333/json')).json();
  const target = targets.find((t) => t.type === 'page');
  if (!target) throw new Error('no page target; start Chrome with --remote-debugging-port=9224');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 0;
  const pending = new Map();
  const errors = [];

  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg.result ?? msg.error);
      pending.delete(msg.id);
    }
    if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails.text);
  });
  await new Promise((r) => ws.addEventListener('open', r));

  const send = (method, params = {}) => new Promise((resolve) => {
    const mid = ++id;
    pending.set(mid, resolve);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const evalx = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value;
  const settle = (ms = 350) => new Promise((r) => setTimeout(r, ms));

  async function open() {
    await send('Page.navigate', { url: BASE + '?t=' + Date.now() });
    await settle(700);
    await evalx(`document.activeElement && document.activeElement.blur()`);
  }

  async function shot(file) {
    const s = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(OUT + file, Buffer.from(s.data, 'base64'));
  }

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });

  const report = {};

  // layout metrics at each supported width
  for (const width of WIDTHS) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await open();
    report['w' + width] = await evalx(`(() => {
      const box = (s) => { const el = document.querySelector(s); if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.width)]; };
      return {
        overflow: document.documentElement.scrollWidth - window.innerWidth,
        search: box('.top-search'),
        mainHead: box('.main-head'),
        rail: box('.rail'),
        filters: box('.filters'),
        inspector: box('.inspector'),
        tabLabels: Array.from(document.querySelectorAll('.ws-tab span')).filter((n) => n.offsetParent !== null).length,
      };
    })()`);
  }

  // visual states at 1440
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  for (const [rail, file] of RAILS) {
    await open();
    if (rail !== 'survivor') {
      await evalx(`document.querySelector('[data-rail="${rail}"]').click()`);
      await settle();
    }
    await shot(file);
  }

  await open();
  await evalx(`document.querySelector('[data-ws="import"]').click()`);
  await settle();
  await shot('preview-import.png');

  await evalx(`document.querySelector('[data-ws="download"]').click()`);
  await settle();
  await shot('preview-download.png');

  await open();
  await evalx(`document.querySelector('.rail-utility').click()`);
  await settle(900);
  await shot('preview-scanning.png');

  await open();
  await evalx(`document.querySelector('[data-more]').click()`);
  await settle(300);
  await shot('preview-more.png');

  report.states = await evalx(`(() => ({
    libraryHidden: document.querySelector('[data-view="library"]').hidden,
    moreOpen: !document.querySelector('.more-menu').hidden,
    title: document.querySelector('.page-title').textContent.trim(),
    crumb: document.querySelector('.crumb').textContent.trim().replace(/\\s+/g, ' '),
  }))()`);

  await send('Emulation.setDeviceMetricsOverride', { width: 1100, height: 900, deviceScaleFactor: 1, mobile: false });
  await open();
  await shot('preview-1100.png');

  report.errors = errors;
  console.log(JSON.stringify(report, null, 1));
  ws.close();
}

main().catch((err) => {
  console.error(err.stack || String(err));
  process.exitCode = 1;
});
