/**
 * 截取 states.html 的状态板长图。
 * 前提：静态服务 8138、Chrome 调试端口 9333。
 */
const fs = require('fs');

async function main() {
  const targets = await (await fetch('http://127.0.0.1:9333/json')).json();
  const target = targets.find((t) => t.type === 'page');
  if (!target) throw new Error('no page target');

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
  const evalx = async (expression) => (await send('Runtime.evaluate', { expression, returnByValue: true })).result.value;

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:8138/final/states.html' });
  await new Promise((r) => setTimeout(r, 900));

  const metrics = await evalx(`(() => ({
    height: document.documentElement.scrollHeight,
    width: document.documentElement.scrollWidth,
    cards: document.querySelectorAll('.state-card').length,
    dialogs: document.querySelectorAll('.dlg').length,
    panels: document.querySelectorAll('.panel').length,
    overflow: document.documentElement.scrollWidth - window.innerWidth,
  }))()`);
  console.log('metrics', JSON.stringify(metrics));

  const shot = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    clip: { x: 0, y: 0, width: 1440, height: metrics.height, scale: 1 },
  });
  fs.writeFileSync('docs/redesign/final/states.png', Buffer.from(shot.data, 'base64'));
  console.log('saved states.png');
  console.log('errors', JSON.stringify(errors));
  ws.close();
}

main().catch((err) => { console.error(err.stack || String(err)); process.exitCode = 1; });
