/* 前端与 Python 的桥。
 *
 * 两种模式：
 *   1. pywebview 环境 —— 走 window.pywebview.api
 *   2. 普通浏览器    —— 走 mock，界面照样能开，方便调样式
 *
 * 所有方法返回 Promise。失败统一 {ok:false, error:"..."}，不抛异常。
 */
(function () {
  'use strict';

  // ------------------------------------------------------------ mock 数据
  // 只在浏览器里跑时使用，字段与后端 _to_mod 完全一致
  const MOCK_MODS = [
    { file: 'm1.vpk', title: 'Koharu [Replace Ellis]', alias: '', category: '角色',
      item: 'Ellis', size: 116.1e6, sizeText: '116.1 MB', enabled: false,
      workshop_id: '', thumb: 'assets/mods/mod1.webp', added: Date.now() - 2 * 86400000,
      addedText: '2 天前', pinned: false },
    { file: 'm3.vpk', title: 'VRC プラム Plum replace ellis', alias: '夏日甜点屋',
      category: '角色', item: 'Ellis', size: 34.1e6, sizeText: '34.1 MB', enabled: true,
      workshop_id: '3659210344', thumb: 'assets/mods/mod3.webp',
      added: Date.now() - 7 * 86400000, addedText: '1 周前', pinned: false },
    { file: 'm4.vpk', title: '[Gakuen IDOLM@STER] Fujita', alias: '', category: '角色',
      item: 'Ellis', size: 146.4e6, sizeText: '146.4 MB', enabled: false,
      workshop_id: '3671024551', thumb: 'assets/mods/mod4.webp',
      added: Date.now() - 9 * 86400000, addedText: '1 周前', pinned: false },
    { file: 'm2.vpk', title: 'VRC lime 甜点屋 打歌服', alias: '', category: '角色',
      item: 'Ellis', size: 93.0e6, sizeText: '93.0 MB', enabled: false,
      workshop_id: '3664792140', thumb: 'assets/mods/mod2.webp',
      added: Date.now() - 4 * 86400000, addedText: '4 天前', pinned: false },
    { file: 'm5.vpk', title: '【原神】菲谢尔 极夜真梦', alias: '', category: '角色',
      item: 'Ellis', size: 38.3e6, sizeText: '38.3 MB', enabled: false,
      workshop_id: '3648830117', thumb: 'assets/mods/mod5.webp',
      added: Date.now() - 12 * 86400000, addedText: '1 周前', pinned: false },
    { file: 'm6.vpk', title: '雨衣替换 Ellis', alias: '', category: '角色',
      item: 'Ellis', size: 246.6e6, sizeText: '246.6 MB', enabled: false,
      workshop_id: '3639905428', thumb: 'assets/mods/mod6.webp',
      added: Date.now() - 18 * 86400000, addedText: '2 周前', pinned: false },
    { file: 'w1.vpk', title: 'AK-47 | 霓虹风暴', alias: '', category: '枪械',
      item: 'AK-47', size: 56.8e6, sizeText: '56.8 MB', enabled: true,
      workshop_id: '', thumb: 'assets/mods/mod2.webp', added: Date.now() - 86400000,
      addedText: '今天', pinned: false },
    { file: 'w2.vpk', title: 'M16A2 | 数码迷彩', alias: '', category: '枪械',
      item: 'M16A2', size: 40.1e6, sizeText: '40.1 MB', enabled: true,
      workshop_id: '', thumb: 'assets/mods/mod6.webp', added: Date.now() - 8 * 86400000,
      addedText: '1 周前', pinned: false },
  ];

  // 演示用合集：让浏览器预览也能看到「详情 → 更多 → 合集」块
  // （真实数据里的合集由「导入工坊合集」流程建立，不在界面上手工编组）
  const MOCK_COLL = {
    ws_900001: { name: 'Ellis 皮肤合集', workshop_id: '900001',
                 files: ['m2.vpk', 'm3.vpk', 'm5.vpk'] },
  };
  ['m2.vpk', 'm3.vpk', 'm5.vpk'].forEach((f) => {
    const m = MOCK_MODS.find((x) => x.file === f);
    if (m) m.collection = 'ws_900001';
  });

  // 浏览器演示模式也要有「全部可能子分类」，否则 demo 里特感只剩一个
  const MOCK_CATALOG = {
    '角色': ['Bill(比尔)', 'Coach(教练)', 'Ellis(艾利斯)', 'Francis(弗朗西斯)',
             'Louis(路易斯)', 'Nick(尼克)', 'Rochelle(罗谢尔)', 'Zoey(佐伊)'],
    '特感': ['Boomer', 'Charger', 'Hunter', 'Jockey', 'Smoker', 'Spitter',
             'Tank', 'Witch', '普通感染者'],
    '枪械': ['AK-47(AK)', 'AWP(大狙)', 'M16A2(M4)', 'M60(机枪)', 'MP5', 'SG552'],
  };

  const MOCK = {
    mods: MOCK_MODS.map((m) => Object.assign({}, m)),
    collections: MOCK_COLL,
    catalog: MOCK_CATALOG,
    settings: { game_dir: 'E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2',
                proxy: '', archiver_path: '', palette: 'blacksite', motion: true },
    paths: { addons: 'E:\\SteamLibrary\\steamapps\\common\\Left 4 Dead 2\\left4dead2\\addons',
             valid: true },
    version: '1.2.1',
  };

  // pywebview 异步注入。两个坑：
  //   1. 脚本执行时 api 可能还不存在
  //   2. Object.keys() 在注入完成前是空的
  // 所以用事件 + 轮询双保险，且以「keys 里有已知方法」作为就绪判据。
  const KNOWN_METHOD = 'bootstrap';
  let _pyReady = null;
  let _pyResolved = false;

  /** 后端是否已注入（不保证方法表就绪）。 */
  function hasPy() {
    return !!(window.pywebview && window.pywebview.api);
  }

  function pyIsReady() {
    const api = window.pywebview && window.pywebview.api;
    if (!api) return false;
    try {
      return Object.keys(api).indexOf(KNOWN_METHOD) >= 0;
    } catch (e) {
      return false;
    }
  }

  function markReady() {
    if (_pyResolved) return;
    _pyResolved = true;
    _pyReady = Promise.resolve(true);
  }

  function waitForPy(timeoutMs) {
    if (_pyReady) return _pyReady;
    _pyReady = new Promise((resolve) => {
      if (pyIsReady()) { _pyResolved = true; resolve(true); return; }
      const started = Date.now();
      const timer = setInterval(() => {
        if (pyIsReady()) {
          clearInterval(timer);
          _pyResolved = true;
          resolve(true);
        } else if (Date.now() - started > (timeoutMs || 10000)) {
          clearInterval(timer);
          resolve(false);
        }
      }, 40);
    });
    return _pyReady;
  }

  window.addEventListener('pywebviewready', () => {
    waitForPy(3000);
  });

  function mockBootstrap() {
    const mods = MOCK.mods;
    return {
      ok: true,
      mods: mods.map((m) => Object.assign({}, m)),
      settings: Object.assign({}, MOCK.settings),
      stats: { total: mods.length, enabled: mods.filter((m) => m.enabled).length },
      collections: Object.assign({}, MOCK.collections),
      catalog: Object.assign({}, MOCK.catalog),
      game: { running: false },
      paths: Object.assign({}, MOCK.paths),
      version: MOCK.version,
    };
  }

  /** 浏览器模式：假装解析出 3 个候选。 */
  function mockAnalyze() {
    const jobId = 'mock-analyze';
    setTimeout(() => {
      if (!window.__dsh) return;
      window.__dsh.emit('job.done', {
        job_id: jobId,
        result: {
          candidates: [
            { stem: 'a', title: 'VRC lime 甜点屋 打歌服', category: '角色',
              item: 'Ellis', sizeText: '93.0 MB', thumb: 'assets/mods/mod2.webp',
              selected: true, duplicate: false },
            { stem: 'b', title: '【原神】菲谢尔 极夜真梦', category: '角色',
              item: 'Ellis', sizeText: '38.3 MB', thumb: 'assets/mods/mod5.webp',
              selected: true, duplicate: false },
            { stem: 'c', title: 'VRC プラム Plum replace ellis', category: '角色',
              item: 'Ellis', sizeText: '34.1 MB', thumb: 'assets/mods/mod3.webp',
              selected: false, duplicate: true },
          ],
          duplicates: 1,
        },
      });
    }, 900);
    return { ok: true, job_id: jobId };
  }

  /** 浏览器模式：假装下载。 */
  function mockDownload(ids) {
    const jobId = 'mock-download';
    let pct = 0;
    const timer = setInterval(() => {
      pct = Math.min(100, pct + 12);
      if (window.__dsh) {
        window.__dsh.emit('job.progress', {
          job_id: jobId, phase: 'download', label: '正在下载',
          percent: pct, done: pct, total: 100,
        });
        if (pct >= 100) {
          clearInterval(timer);
          window.__dsh.emit('job.done', { job_id: jobId,
            result: { records: ids.map((id) => ({ id })), skipped: [], failures: [] } });
        }
      }
    }, 200);
    return { ok: true, job_id: jobId };
  }

  // ------------------------------------------------------------ 调用封装
  let lastError = null;

  async function call(name, ...args) {
    try {
      if (!hasPy()) return null;                 // 交给 mock 处理
      const api = window.pywebview.api;
      // pywebview 的 api 是 Proxy，'in' 和 typeof 都不可靠，
      // 只有 Object.keys 能列出来。用 key 列表判断。
      const keys = Object.keys(api);
      if (keys.indexOf(name) < 0) {
        lastError = '后端缺少方法：' + name;
        console.error(lastError, Object.keys(api).slice(0, 10));
        return { ok: false, error: lastError };
      }
      const res = await api[name].apply(api, args);
      if (res && res.ok === false) lastError = res.error || '未知错误';
      else lastError = null;
      return res;
    } catch (err) {
      lastError = String(err && err.message ? err.message : err);
      console.error('[bridge] ' + name + ' 失败：', err);
      return { ok: false, error: lastError };
    }
  }

  // ------------------------------------------------------------ 公开接口
  const bridge = {
    isMock: () => !hasPy(),
    log: async (message) => {
      try {
        if (pyIsReady()) await window.pywebview.api.log(String(message));
      } catch (e) { /* 日志失败不影响业务 */ }
    },
    whenReady: () => waitForPy(10000),
    lastError: () => lastError,

    // 读
    bootstrap: async () => {
      const ready = await waitForPy(10000);
      if (!ready) return mockBootstrap();
      const res = await call('bootstrap');
      return res || mockBootstrap();
    },
    get_stats: async () => {
      const b = await bridge.bootstrap();
      return b && b.ok ? { ok: true, total: b.stats.total, enabled: b.stats.enabled } : b;
    },

    // 写
    toggle_mod: async (file, enabled) => {
      const res = await call('toggle_mod', file, enabled);
      if (res) return res;
      // mock：本地改状态
      const m = MOCK.mods.find((x) => x.file === file);
      if (!m) return { ok: false, error: '找不到模组' };
      m.enabled = !!enabled;
      return { ok: true, enabled: m.enabled, disabled_siblings: [] };
    },

    set_alias: async (file, alias) => {
      const res = await call('set_alias', file, alias);
      if (res) return res;
      const m = MOCK.mods.find((x) => x.file === file);
      if (m) m.alias = alias || '';
      return { ok: true, alias: alias || '' };
    },

    set_category: async (file, category, item) => {
      const res = await call('set_category', file, category, item);
      if (res) return res;
      const m = MOCK.mods.find((x) => x.file === file);
      if (m) { m.category = category; m.item = item || ''; }
      return { ok: true };
    },

    restore_auto_category: async (file) => {
      const res = await call('restore_auto_category', file);
      if (res) return res;
      const m = MOCK.mods.find((x) => x.file === file);
      if (m) { m.category = m.autoCategory || '未分类'; m.item = ''; }
      return { ok: true };
    },

    delete_mod: async (file) => {
      const res = await call('delete_mod', file);
      if (res) return res;
      MOCK.mods = MOCK.mods.filter((x) => x.file !== file);
      return { ok: true, trashed: true };
    },

    // 外部动作
    reveal_mod: async (file) => call('reveal_mod', file) || { ok: true },
    open_workshop: async (id) => call('open_workshop', id) || { ok: true },
    open_path: async (p) => call('open_path', p) || { ok: true },
    launch_game: async () => call('launch_game') || { ok: true },

    // 长任务
    start_scan: async () => {
      const res = await call('start_scan');
      if (res) return res;
      // mock：假装扫描进度
      const job = { job_id: 'mock-scan' };
      if (window.__dsh) {
        let i = 0;
        const timer = setInterval(() => {
          i += 1;
          window.__dsh.emit('job.progress', {
            job_id: job.job_id, phase: 'scan', label: '扫描中 ' + i + '/8',
            done: i, total: 8, percent: Math.round(i / 8 * 100),
          });
          if (i >= 8) {
            clearInterval(timer);
            window.__dsh.emit('job.done', { job_id: job.job_id, result: {} });
          }
        }, 120);
      }
      return { ok: true, job_id: job.job_id };
    },

    // 全量采纳：会移动文件（子目录 → 顶层、workshop → 迁移）
    start_adopt: async () => {
      const res = await call('start_adopt');
      if (res) return res;
      const job = { job_id: 'mock-adopt' };
      if (window.__dsh) {
        let i = 0;
        const timer = setInterval(() => {
          i += 1;
          window.__dsh.emit('job.progress', {
            job_id: job.job_id, phase: 'adopt', label: '整理中 ' + i + '/5',
            done: i, total: 5, percent: Math.round(i / 5 * 100),
          });
          if (i >= 5) {
            clearInterval(timer);
            window.__dsh.emit('job.done', {
              job_id: job.job_id,
              result: { adopted: 0, moved: 0, migrated: 0, errors: [] },
            });
          }
        }, 120);
      }
      return { ok: true, job_id: job.job_id };
    },

    // 长任务
    analyze_archives: async (paths) => {
      const res = await call('analyze_archives', paths || []);
      if (res) return res;
      return mockAnalyze();
    },
    choose_archives: async () => {
      const res = await call('choose_archives');
      if (res) return res;
      return { ok: false, error: '浏览器模式不支持文件选择' };
    },
    commit_import: async (jobId, stems) => {
      const res = await call('commit_import', jobId, stems || []);
      if (res) return res;
      return { ok: false, error: '浏览器模式不支持导入' };
    },
    parse_links: async (text) => {
      const res = await call('parse_links', text || '');
      if (res) return res;
      const ids = (text || '').match(/\d{6,}/g) || [];
      return { ok: true, ids: [...new Set(ids)] };
    },
    fetch_details: async (ids) => {
      const res = await call('fetch_details', ids || []);
      if (res) return res;
      // mock：把 ids 映射成假详情
      return {
        ok: true,
        collection: null,
        items: (ids || []).map((id, i) => ({
          id, title: '演示物品 ' + id, category: '角色', item: 'Ellis',
          size: 50e6, sizeText: '50.0 MB', thumb: 'assets/mods/mod4.webp',
          existing: i === 0, appId: 550,
        })),
      };
    },

    start_download: async (ids, collection) => {
      const res = await call('start_download', ids || [], collection || null);
      if (res) return res;
      return mockDownload(ids);
    },
    cancel_job: async (jobId) => call('cancel_job', jobId) || { ok: true },

    // 窗口控制
    win_minimize: async () => call('win_minimize') || { ok: true },
    win_toggle_maximize: async () => call('win_toggle_maximize') || { ok: true, maximized: false },
    win_close: async () => call('win_close') || { ok: true },

    // 设置
    save_setting: async (key, value) => {
      const res = await call('save_setting', key, value);
      if (res) return res;
      MOCK.settings[key] = value;
      return { ok: true };
    },
    detect_game_dir: async () => call('detect_game_dir') || { ok: true, game_dir: '' },
    choose_dir: async () => {
      const res = await call('choose_dir');
      if (res) return res;
      return { ok: false, error: '浏览器模式不支持目录选择' };
    },
    clean_cache: async () => {
      const res = await call('clean_cache');
      if (res) return res;
      return { ok: true, freed: 42.6 * 1048576 };
    },
    check_update: async () => {
      const res = await call('check_update');
      if (res) return res;
      return { ok: true, latest: '1.2.1', url: '' };
    },
    set_palette: async (name) => {
      const res = await call('set_palette', name);
      if (res) return res;
      MOCK.settings.palette = name;
      return { ok: true, palette: name };
    },
  };

  window.bridge = bridge;

  if (bridge.isMock()) {
    console.info('[bridge] 浏览器模式：使用 mock 数据。启动 pywebview 后会自动连真实后端。');
  }
})();
