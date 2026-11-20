/**
 * 演示页交互验证 + 截图。
 * 覆盖：初始渲染、Rail 切换、筛选、Inspector 启停与互斥、导入四阶段、下载四阶段、设置、状态栏扫描。
 */
const fs = require('fs');

const OUT = 'docs/redesign/final/';
const BASE = 'http://127.0.0.1:8138/final/demo.html';

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
    if (msg.method === 'Runtime.exceptionThrown') {
      errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
    }
  });
  await new Promise((r) => ws.addEventListener('open', r));

  const send = (method, params = {}) => new Promise((resolve) => {
    const mid = ++id;
    pending.set(mid, resolve);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  const evalx = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r && r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval error');
    return r.result.value;
  };
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const shot = async (file) => {
    const s = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(OUT + file, Buffer.from(s.data, 'base64'));
  };
  const click = async (sel) => { await evalx(`document.querySelector(${JSON.stringify(sel)}).click()`); await wait(260); };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: BASE });
  await wait(900);

  const report = {};
  report.boot = await evalx(`(() => ({
    cards: document.querySelectorAll('.mod-card').length,
    filters: document.querySelectorAll('.filter-row').length,
    title: document.querySelector('#pageTitle').textContent.trim(),
    inspectorTitle: document.querySelector('.detail-title')?.textContent.trim(),
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    panel: [...document.querySelectorAll('[data-panel]')].find(p => !p.hidden)?.dataset.panel,
  }))()`);

  await shot('demo-1-library.png');

  // 全部：应展开所有子分类
  await click('[data-rail="all"]');
  report.allRail = await evalx(`(() => ({
    groups: document.querySelectorAll('.tree-head').length,
    visibleGroups: [...document.querySelectorAll('.tree-items')].filter(n => !n.hidden).length,
    rows: document.querySelectorAll('.filter-row').length,
  }))()`);
  await shot('demo-16-all-expanded.png');

  // 跨视图：在下载页点 Rail 应自动回到浏览
  await click('[data-view="download"]');
  const beforeRail = await evalx(`document.querySelector('[data-panel="download"]').hidden`);
  await click('[data-rail="survivor"]');
  report.railJump = await evalx(`(() => ({
    downloadWasVisible: ${beforeRail} === false,
    libraryVisible: !document.querySelector('[data-panel="library"]').hidden,
    rail: document.querySelector('[data-rail].active').dataset.rail,
  }))()`);

  // rail → 武器（折叠结构）
  await click('[data-rail="weapon"]');
  report.weapon = await evalx(`(() => ({
    title: document.querySelector('#pageTitle').textContent.trim(),
    treeHeads: document.querySelectorAll('.tree-head').length,
    cards: document.querySelectorAll('.mod-card').length,
  }))()`);
  await shot('demo-2-weapon.png');

  // 展开近战
  await click('[data-group="近战"]');
  report.fold = await evalx(`(() => ({
    open: !document.querySelector('[data-group="近战"]').nextElementSibling.hidden,
  }))()`);

  // 回到角色，测试双击启停
  await click('[data-rail="survivor"]');
  await evalx(`(() => { const c = document.querySelector('[data-mod="m5"]'); c.dispatchEvent(new MouseEvent('dblclick', {bubbles:true})); })()`);
  await wait(400);
  // 同组有启用项时会先弹确认窗，双击的语义与 Inspector 开关一致
  report.dblclickDialog = await evalx(`(() => ({ title: document.querySelector('#modal-host h4')?.textContent.trim() || null }))()`);
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; if (b.length) b[b.length-1].click(); })()`);
  await wait(400);
  report.dblclickEnable = await evalx(`(() => ({
    isOn: document.querySelector('[data-mod="m5"]').classList.contains('is-on'),
    nameColor: getComputedStyle(document.querySelector('[data-mod="m5"] .mod-name')).color,
    bg: getComputedStyle(document.querySelector('[data-mod="m5"]')).backgroundImage.slice(0, 40),
  }))()`);
  await shot('demo-17-doubleclick-on.png');

  // 再双击一次应停用（验证是「切换」而不是只会启用）
  await evalx(`(() => { const c = document.querySelector('[data-mod="m5"]'); c.dispatchEvent(new MouseEvent('dblclick', {bubbles:true})); })()`);
  await wait(400);
  report.dblclickOff = await evalx(`(() => ({
    isOn: document.querySelector('[data-mod="m5"]').classList.contains('is-on'),
    badge: !!document.querySelector('[data-mod="m5"] .badge-on'),
    nameColor: getComputedStyle(document.querySelector('[data-mod="m5"] .mod-name')).color,
  }))()`);
  await shot('demo-18-doubleclick-off.png');

  // 保证同组里有启用项（m3），互斥确认窗才会出现
  await click('[data-mod="m3"]');
  const m3On = await evalx(`document.querySelector('[data-mod="m3"]').classList.contains('is-on')`);
  if (!m3On) {
    await click('#insSwitch');
    await wait(300);
  }
  await click('[data-mod="m1"]');
  await click('#insSwitch');
  await wait(400);
  report.mutex = await evalx(`(() => ({
    dialogOpen: document.querySelector('#modal-root').classList.contains('open'),
    dialogTitle: document.querySelector('#modal-host h4')?.textContent.trim(),
    rows: [...document.querySelectorAll('#modal-host .dlg-row')].map(r => r.textContent.trim().replace(/\\s+/g,' ')),
  }))()`);
  await shot('demo-3-mutex.png');

  // 确认启用
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; b[b.length-1].click(); })()`);
  await wait(400);
  report.afterEnable = await evalx(`(() => ({
    m1On: document.querySelector('[data-mod="m1"]').classList.contains('is-on'),
    m1WhiteText: getComputedStyle(document.querySelector('[data-mod="m1"] .mod-name')).color,
    m3On: document.querySelector('[data-mod="m3"]').classList.contains('is-on'),
    statusText: document.querySelector('#inspector .status-left')?.textContent.trim(),
    specLabel: [...document.querySelectorAll('#inspector .spec-row .k')].map(n => n.textContent.trim()),
  }))()`);
  await shot('demo-4-enabled.png');

  // 导入视图
  await click('[data-view="import"]');
  await click('#dropZone');
  await wait(300);
  report.importing = await evalx(`(() => ({
    progressVisible: !document.querySelector('#importProgress').hidden,
    panelHidden: document.querySelector('#importPanel').hidden,
  }))()`);
  await shot('demo-5-import-parsing.png');

  await wait(1400);
  report.importParsed = await evalx(`(() => ({
    rows: document.querySelectorAll('#importList .task-row').length,
    dups: document.querySelectorAll('#importList .task-row.is-dup').length,
    commit: document.querySelector('#importCommit').textContent.trim(),
    commitDisabled: document.querySelector('#importCommit').disabled,
  }))()`);
  await shot('demo-6-import-parsed.png');

  await click('#importCommit');
  await wait(1200);
  report.importDone = await evalx(`(() => ({
    dialogTitle: document.querySelector('#modal-host h4')?.textContent.trim(),
  }))()`);
  await shot('demo-7-import-done.png');
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; b[b.length-1].click(); })()`);
  await wait(300);

  // 下载视图
  await click('[data-view="download"]');
  await evalx(`(() => { const i = document.querySelector('#linkInput'); i.value = 'https://steamcommunity.com/sharedfiles/filedetails/?id=3671'; i.dispatchEvent(new Event('input', {bubbles:true})); })()`);
  await click('#parseBtn');
  await wait(400);
  report.parsing = await evalx(`(() => ({
    running: !document.querySelector('#downloadRunning').hidden,
    logLines: document.querySelectorAll('#dlLog div').length,
  }))()`);
  await shot('demo-8-download-parsing.png');

  await wait(1200);
  report.parsed = await evalx(`(() => ({
    rows: document.querySelectorAll('#downloadList .task-row').length,
    dups: document.querySelectorAll('#downloadList .task-row.is-dup').length,
    start: document.querySelector('#downloadStart').textContent.trim(),
  }))()`);
  await shot('demo-9-download-parsed.png');

  await click('#downloadStart');
  await wait(700);
  report.downloading = await evalx(`(() => ({
    running: !document.querySelector('#downloadRunning').hidden,
    logLines: document.querySelectorAll('#dlLog div').length,
    label: document.querySelector('#dlRunLabel').textContent.trim(),
    barWidth: document.querySelector('#dlRunBar').style.width,
  }))()`);
  await shot('demo-10-download-running.png');

  await wait(1600);
  report.downloadDone = await evalx(`(() => ({ dialogTitle: document.querySelector('#modal-host h4')?.textContent.trim() }))()`);
  await shot('demo-11-download-done.png');
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; b[b.length-1].click(); })()`);
  await wait(300);

  // 设置
  await click('[data-view="settings"]');
  report.settings = await evalx(`(() => ({ rows: document.querySelectorAll('.settings-row').length }))()`);
  await shot('demo-12-settings.png');

  // 游戏运行中拦截
  await click('[data-setting="game"]');
  await click('[data-view="library"]');
  await click('[data-mod="m5"]');
  await click('#insSwitch');
  await wait(400);
  report.locked = await evalx(`(() => ({ dialogTitle: document.querySelector('#modal-host h4')?.textContent.trim() }))()`);
  await shot('demo-13-locked.png');
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; b[0].click(); })()`);
  await wait(250);

  // 扫描状态栏
  await evalx(`(() => { const s = document.querySelector('[data-setting]'); })()`);
  await click('#tidyBtn');
  await wait(500);
  report.scanDialog = await evalx(`(() => ({ title: document.querySelector('#modal-host h4')?.textContent.trim() }))()`);
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; b[b.length-1].click(); })()`);
  await wait(700);
  report.scanning = await evalx(`(() => ({
    activityVisible: !document.querySelector('#statusActivity').hidden,
    label: document.querySelector('#statusActivityLabel').textContent.trim(),
    bar: document.querySelector('#statusActivityBar').style.width,
  }))()`);
  await shot('demo-14-scanning.png');

  // 扫描完成后会弹结果窗，先关掉再量 1100
  await wait(2600);
  await evalx(`(() => { const b = [...document.querySelectorAll('#modal-host .dlg-foot button')]; if (b.length) b[b.length-1].click(); })()`);
  await wait(400);
  report.scanDone = await evalx(`(() => ({
    activityHidden: document.querySelector('#statusActivity').hidden,
    idleHidden: document.querySelector('#statusIdle').hidden,
  }))()`);

  // 1100 宽
  await send('Emulation.setDeviceMetricsOverride', { width: 1100, height: 900, deviceScaleFactor: 1, mobile: false });
  await click('[data-view="library"]');
  await wait(400);
  report.w1100 = await evalx(`(() => ({
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    gridCols: getComputedStyle(document.querySelector('#grid')).gridTemplateColumns.split(' ').length,
    tabLabels: [...document.querySelectorAll('.ws-tab span')].filter(n => n.offsetParent !== null).length,
  }))()`);
  await shot('demo-15-1100.png');

  report.errors = errors;
  console.log(JSON.stringify(report, null, 1));
  ws.close();
}

main().catch((err) => { console.error(err.stack || String(err)); process.exitCode = 1; });
