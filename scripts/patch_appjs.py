# -*- coding: utf-8 -*-
"""把 demo.js 改写为接真实后端的 app.js。

============================================================
!!  危险：此脚本已过期，执行会覆盖并丢失代码  !!
============================================================

它生成的是「第一次接线」时的版本（约 1370 行）。
此后 app.js 又被手工改过很多轮（启用/删除/别名落盘、
扫描真任务、设置页真实数据、冲突保留最新 …），
现在是 1600 行左右。

再次执行会用 demo.js（1133 行）重新生成，
**静默丢掉这几百行真实功能**，而且没有任何校验会提示你。

保留它只是为了记录「当时的改造步骤」。
要看历史请读 WEBUI_DELIVERY.md，不要跑这个文件。

原始用途：一次性完成 demo.js → app.js 的改写，每步都断言。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "app" / "webui" / "app.js"
SOURCE = ROOT / "docs" / "redesign" / "final" / "demo.js"


def must(cond, msg):
    if not cond:
        print("FAILED:", msg)
        sys.exit(1)


def main():
    s = SOURCE.read_text(encoding="utf-8")
    original = s

    # ---------------------------------------------------------- 1) 数据层
    s = s.replace("  const MODS = [", "  const DEMO_MODS = [", 1)
    must("const DEMO_MODS = [" in s, "DEMO_MODS")

    # 找到 DEMO_MODS 数组结尾，插入 MODS 声明
    idx = s.index("  const DEMO_MODS = [")
    depth = 0
    i = idx + len("  const DEMO_MODS = ")
    end = None
    while i < len(s):
        if s[i] == "[":
            depth += 1
        elif s[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    must(end, "DEMO_MODS 数组闭合")

    s = (s[:end] + "\n\n  // 真实数据由 bootstrap 填充；DEMO_MODS 只在浏览器 mock 时兜底。\n"
         "  let MODS = [];" + s[end:])

    # ---------------------------------------------------------- 2) 适配层 + 加载
    adapt = '''
  // ---------------------------------------------------------------- 数据适配
  // 后端字段（title/category/thumb/size 字节）→ 界面字段（name/cat/img/size MB）
  function adapt(apiMod) {
    return {
      id: apiMod.file || '',
      name: apiMod.title || apiMod.file || '',
      alias: apiMod.alias || '',
      cat: apiMod.category || '未分类',
      item: apiMod.item || '',
      size: (apiMod.size || 0) / 1048576,
      img: apiMod.thumb || '',
      enabled: !!apiMod.enabled,
      added: Math.max(0, Math.round(
        (Date.now() - (apiMod.added || Date.now())) / 86400000)),
      file: apiMod.file || '',
      ws: apiMod.workshop_id || '',
      mutex: !!apiMod.mutex,
    };
  }

  async function loadFromBridge() {
    await window.bridge.whenReady();
    const res = await window.bridge.bootstrap();
    if (!res || !res.ok) {
      if (window.bridge.isMock()) MODS = DEMO_MODS.slice();
      return false;
    }
    MODS = (res.mods || []).map(adapt);
    state.settings = res.settings || state.settings;
    state.version = res.version || state.version;
    state.gameRunning = !!(res.game && res.game.running);
    if (res.paths && res.paths.addons) {
      const el = $('#statusPath');
      if (el) el.textContent = res.paths.addons;
    }
    if (MODS.length && !MODS.some((m) => m.id === state.selectedId)) {
      state.selectedId = MODS[0].id;
    }
    return true;
  }

  async function reloadMods() {
    const res = await window.bridge.bootstrap();
    if (res && res.ok) {
      MODS = (res.mods || []).map(adapt);
      return true;
    }
    return false;
  }

  /** 跑一个后端长任务，把事件桥接到 UI 回调。 */
  function runJob(jobId, onProgress, onDone, onError) {
    const offs = [];
    const cleanup = () => offs.forEach((off) => { try { off(); } catch (e) {} });
    offs.push(window.events.on('job.progress', (p) => {
      if (p && p.job_id === jobId && onProgress) onProgress(p);
    }));
    offs.push(window.events.on('job.done', (p) => {
      if (!p || p.job_id !== jobId) return;
      cleanup();
      if (onDone) onDone(p.result || {});
    }));
    offs.push(window.events.on('job.error', (p) => {
      if (!p || p.job_id !== jobId) return;
      cleanup();
      if (onError) onError(p.message || '任务失败');
    }));
  }

'''
    anchor = "  // ---------------------------------------------------------------- actions"
    must(anchor in s, "actions 锚点")
    s = s.replace(anchor, adapt + anchor, 1)

    # ---------------------------------------------------------- 3) 空库引导
    s = s.replace(
        """    if (!list.length) {
      grid.innerHTML = `<div class="empty"><strong>这里还没有模组</strong>切换到别的分类，或导入一个新模组。</div>`;
      renderHeader();
      return;
    }""",
        """    const totalAll = MODS.length;
    const onboard = $('#onboard');
    if (onboard) onboard.hidden = totalAll > 0;

    if (!list.length) {
      grid.innerHTML = totalAll === 0 ? '' : '<div class="empty">没有匹配的模组</div>';
      renderHeader();
      return;
    }""", 1)
    must("onboard.hidden = totalAll > 0" in s, "onboard 逻辑")

    # ---------------------------------------------------------- 4) 状态栏事件
    bind = '''  // ---------------------------------------------------------------- 状态栏事件
  if (window.events) {
    window.events.bindStatus({
      scanning(label, pct) { setStatus('scanning', { label: label, pct: pct }); },
      idle() { setStatus('idle'); },
    });
  }

'''
    must("  // ---------------------------------------------------------------- boot" in s, "boot 锚点")
    s = s.replace("  // ---------------------------------------------------------------- boot",
                  bind + "  // ---------------------------------------------------------------- boot", 1)

    # ---------------------------------------------------------- 5) 引导按钮
    onboard_btn = '''  // ---------------------------------------------------------------- 首次引导
  const onboardBtn = $('#onboardStart');
  if (onboardBtn) {
    onboardBtn.addEventListener('click', async () => {
      onboardBtn.disabled = true;
      onboardBtn.textContent = '正在整理…';
      const res = await window.bridge.start_scan();
      if (!res || !res.ok) {
        onboardBtn.disabled = false;
        onboardBtn.textContent = '开始整理';
        await infoDialog({ title: '无法整理', tone: 'danger',
                           text: (res && res.error) || '扫描失败' });
        return;
      }
      window.events.on('job.done', async (p) => {
        if (!p || p.job_id !== res.job_id) return;
        onboardBtn.disabled = false;
        onboardBtn.textContent = '开始整理';
        await reloadMods();
        renderFilters(); renderGrid(); renderInspector();
      });
    });
  }

'''
    s = s.replace("  // ---------------------------------------------------------------- boot",
                  onboard_btn + "  // ---------------------------------------------------------------- boot", 1)

    # ---------------------------------------------------------- 6) boot 顺序
    old_boot = """  // ---------------------------------------------------------------- boot
  $('#statusPath').textContent = 'E:\\\\SteamLibrary\\\\steamapps\\\\common\\\\Left 4 Dead 2\\\\left4dead2\\\\addons';
  renderRail();
  renderFilters();
  renderGrid();
  renderInspector();
  setView('library');
  setStatus('idle');
})();"""
    new_boot = """  // ---------------------------------------------------------------- boot
  // 先取真实数据再渲染，避免闪一帧演示内容。
  (async () => {
    setView('library');
    setStatus('idle');

    const ok = await loadFromBridge();
    if (!ok) console.warn('[app] 后端不可用，使用演示数据');
    if (window.bridge && window.bridge.log) {
      window.bridge.log('boot mods=' + MODS.length + ' ok=' + ok);
    }

    renderRail();
    renderFilters();
    renderGrid();
    renderInspector();

    if (window.bridge && window.bridge.log) {
      window.bridge.log('rendered cards='
        + document.querySelectorAll('.mod-card').length);
    }
  })();
})();"""
    must(old_boot in s, "旧 boot 块")
    s = s.replace(old_boot, new_boot, 1)

    # ---------------------------------------------------------- 7) 导入流程
    start = s.index("  async function runImport() {")
    end = s.index("  // ---------------------------------------------------------------- download flow")
    new_import = '''  async function runImport() {
    if (importFlow.running) return;

    let paths = [];
    if (!window.bridge.isMock()) {
      const picked = await window.bridge.choose_archives();
      if (!picked || !picked.ok || !picked.paths || !picked.paths.length) return;
      paths = picked.paths;
    } else {
      paths = ['mock.7z'];
    }

    importFlow.running = true;
    importFlow.candidates = [];
    importFlow.batchJob = null;

    $('#importPanel').hidden = true;
    $('#importActions').hidden = true;
    $('#dropZone').hidden = true;
    setImportProgress({ title: '正在解析', label: '准备中', meta: '', pct: 0 });

    const res = await window.bridge.analyze_archives(paths);
    if (!res || !res.ok) {
      importFlow.running = false;
      $('#importProgress').hidden = true;
      $('#dropZone').hidden = false;
      await infoDialog({ title: '无法导入', tone: 'warning',
                         text: (res && res.error) || '解析失败' });
      return;
    }

    importFlow.batchJob = res.job_id;
    runJob(res.job_id,
      (p) => setImportProgress({
        title: '正在解析', label: p.label || '读取压缩包',
        meta: (p.percent || 0) + '%', pct: p.percent || 0,
      }),
      (result) => {
        importFlow.candidates = (result.candidates || []).map((c) => ({
          stem: c.stem,
          name: c.title || c.stem,
          meta: [c.category, c.item].filter(Boolean).join(' / ')
                + (c.sizeText ? ' · ' + c.sizeText : ''),
          img: c.thumb || '',
          dup: !!c.duplicate,
          parseError: c.parseError || '',
          selected: !!c.selected,
        }));
        $('#importProgress').hidden = true;
        $('#dropZone').hidden = false;
        importFlow.running = false;
        $('#importPanel').hidden = false;
        renderImportCandidates();
      },
      async (msg) => {
        $('#importProgress').hidden = true;
        $('#dropZone').hidden = false;
        importFlow.running = false;
        await infoDialog({ title: '解析失败', tone: 'danger', text: msg });
      });
  }

  async function commitImport() {
    const picked = importFlow.candidates.filter(
      (c) => c.selected && !c.dup && !c.parseError);
    if (!picked.length) return;

    if (state.gameRunning) {
      await infoDialog({ title: '游戏运行中', tone: 'warning',
                         text: '游戏运行时无法写入模组库，请先退出游戏。' });
      return;
    }

    $('#importPanel').hidden = true;
    $('#importActions').hidden = true;
    $('#dropZone').hidden = true;
    setImportProgress({ title: `正在导入 ${picked.length} 个模组`,
                        label: picked[0].name, meta: '0 / ' + picked.length, pct: 0 });

    const stems = picked.map((c) => c.stem).filter(Boolean);
    const res = await window.bridge.commit_import(importFlow.batchJob, stems);
    if (!res || !res.ok) {
      $('#importProgress').hidden = true;
      $('#importPanel').hidden = false;
      $('#dropZone').hidden = false;
      await infoDialog({ title: '导入失败', tone: 'danger',
                         text: (res && res.error) || '写入失败' });
      return;
    }

    runJob(res.job_id,
      (p) => setImportProgress({
        title: `正在导入 ${picked.length} 个模组`,
        label: p.label || '', meta: (p.percent || 0) + '%', pct: p.percent || 0,
      }),
      async (result) => {
        $('#importProgress').hidden = true;
        $('#dropZone').hidden = false;
        await infoDialog({
          title: '导入完成',
          text: `已加入模组库 ${result.imported || picked.length} 个。`,
          rows: picked.map((c) => ({ name: c.name, tag: '已写入', tone: 'ok' })),
        });
        importFlow.candidates = [];
        await reloadMods();
        renderFilters(); renderGrid(); renderInspector();
      },
      async (msg) => {
        $('#importProgress').hidden = true;
        $('#importPanel').hidden = false;
        $('#dropZone').hidden = false;
        await infoDialog({ title: '导入失败', tone: 'danger', text: msg });
      });
  }

'''
    s = s[:start] + new_import + s[end:]

    # ---------------------------------------------------------- 8) 下载流程
    start = s.index("  async function parseLink() {")
    end = s.index("  // ---------------------------------------------------------------- settings")
    new_dl = '''  async function parseLink() {
    const raw = $('#linkInput').value.trim();
    if (!raw) {
      await infoDialog({ title: '无法解析', tone: 'warning',
                         text: '请先粘贴创意工坊链接或物品 ID。' });
      return;
    }

    $('#downloadPanel').hidden = true;
    $('#downloadActions').hidden = true;
    $('#downloadRunning').hidden = false;
    $('#dlRunTitle').textContent = '正在解析链接';
    $('#dlRunMeta').textContent = '';
    $('#dlLog').innerHTML = '';
    $('#dlRunBar').style.width = '0%';
    $('#dlRunLabel').textContent = '识别物品 ID';
    log('开始解析：' + raw);

    const res = await window.bridge.parse_links(raw);
    if (!res || !res.ok || !res.ids || !res.ids.length) {
      $('#downloadRunning').hidden = true;
      await infoDialog({ title: '链接无效', tone: 'warning',
                         text: (res && res.error) || '没有识别到有效的创意工坊物品 ID。' });
      return;
    }
    log('识别到 ' + res.ids.length + ' 个物品 ID');

    $('#dlRunLabel').textContent = '读取工坊详情';
    const details = await window.bridge.fetch_details(res.ids);
    if (!details || !details.ok) {
      $('#downloadRunning').hidden = true;
      await infoDialog({ title: '解析失败', tone: 'danger',
                         text: (details && details.error) || '读取工坊详情失败' });
      return;
    }

    dlFlow.collection = details.collection || null;
    dlFlow.items = (details.items || []).map((d) => ({
      id: d.id,
      name: d.title || d.id,
      meta: (d.sizeText ? d.sizeText : '') + (d.existing ? ' · 已在库' : ''),
      img: d.thumb || '',
      dup: !!d.existing,
      selected: !d.existing,
    }));
    log('读取完成：' + dlFlow.items.length + ' 个物品');

    $('#dlRunBar').style.width = '0%';
    $('#downloadRunning').hidden = true;
    $('#downloadPanel').hidden = false;
    renderDownloadItems();
  }

  async function startDownload() {
    const picked = dlFlow.items.filter((i) => i.selected && !i.dup);
    if (!picked.length) return;
    if (state.gameRunning) {
      await infoDialog({ title: '游戏运行中', tone: 'warning',
                         text: '请先关闭游戏，再下载导入模组。' });
      return;
    }

    $('#downloadPanel').hidden = true;
    $('#downloadActions').hidden = true;
    $('#downloadRunning').hidden = false;
    $('#dlRunTitle').textContent = `正在下载 ${picked.length} 个模组`;
    $('#dlRunMeta').textContent = '';
    $('#dlLog').innerHTML = '';
    $('#dlRunLabel').textContent = picked[0].name;
    log(`准备下载 ${picked.length} 个模组`);

    const res = await window.bridge.start_download(
      picked.map((i) => i.id), dlFlow.collection);
    if (!res || !res.ok) {
      $('#downloadRunning').hidden = true;
      $('#downloadPanel').hidden = false;
      $('#downloadActions').hidden = false;
      await infoDialog({ title: '无法下载', tone: 'danger',
                         text: (res && res.error) || '启动下载失败' });
      return;
    }

    runJob(res.job_id,
      (p) => {
        $('#dlRunBar').style.width = (p.percent || 0) + '%';
        if (p.current) {
          $('#dlRunLabel').textContent = p.current;
          if (p.label) log(p.label);
        }
        $('#dlRunMeta').textContent = `已完成 ${p.percent || 0}%`;
      },
      async (result) => {
        $('#downloadRunning').hidden = true;
        const recs = (result && result.records) || [];
        const fails = (result && result.failures) || [];
        const skipped = (result && result.skipped) || [];
        log(`完成：导入 ${recs.length}，失败 ${fails.length}，跳过 ${skipped.length}`);

        if (fails.length) {
          await infoDialog({
            title: '部分下载未完成',
            tone: 'warning',
            text: `已导入 ${recs.length} 个，失败 ${fails.length} 个。`,
            rows: fails.map((f) => ({ name: f.title || f.id,
                                      tag: (f.error || '').slice(0, 20) || '失败',
                                      tone: 'bad' })),
          });
        } else {
          await infoDialog({
            title: '下载完成',
            text: `已导入 ${recs.length} 个模组`
                  + (skipped.length ? `，跳过 ${skipped.length} 个已在库的条目` : '') + '。',
            rows: recs.map((r, i) => ({ name: picked[i] ? picked[i].name : String(i + 1),
                                        tag: '已启用', tone: 'ok' })),
          });
        }

        await reloadMods();
        renderFilters(); renderGrid(); renderInspector();
        renderDownloadItems();
        $('#downloadPanel').hidden = false;
        $('#downloadActions').hidden = false;
      },
      async (msg) => {
        $('#downloadRunning').hidden = true;
        $('#downloadPanel').hidden = false;
        $('#downloadActions').hidden = false;
        await infoDialog({ title: '下载失败', tone: 'danger', text: msg });
      });
  }

'''
    s = s[:start] + new_dl + s[end:]

    # ---------------------------------------------------------- 9) 设置
    start = s.index("    $$('[data-setting]').forEach((b) => b.addEventListener('click', async () => {")
    end = s.index("  // ---------------------------------------------------------------- view switching")
    new_settings = '''    $$('[data-setting]').forEach((b) => b.addEventListener('click', async () => {
      const kind = b.dataset.setting;

      if (kind === 'game') {
        state.gameRunning = !state.gameRunning;
        $('#gameStatus').classList.toggle('running', state.gameRunning);
        $('#gameStatus').title = state.gameRunning ? '游戏运行中' : '游戏未运行';
        $('#launchBtn').disabled = state.gameRunning;
        renderSettings();
        toast(state.gameRunning ? '已标记为运行中' : '已标记为未运行');
        return;
      }

      if (kind === 'detect' || kind === 'browse') {
        const res = kind === 'detect'
          ? await window.bridge.detect_game_dir()
          : await window.bridge.choose_dir();
        const dir = res && res.ok ? (res.game_dir || res.path || '') : '';
        if (!dir) {
          await infoDialog({ title: '未找到', tone: 'warning',
                             text: (res && res.error) || '未能自动定位游戏目录，请手动选择。' });
          return;
        }
        await window.bridge.save_setting('game_dir', dir);
        state.settings.game_dir = dir;
        renderSettings();
        await loadFromBridge();
        renderFilters(); renderGrid(); renderInspector();
        toast('已更新游戏目录');
        return;
      }

      if (kind === 'clean') {
        const ok = await confirmDialog({
          title: '清理缓存', tone: 'question',
          text: '将删除缩略图缓存与临时解压目录，不影响模组文件。',
          confirm: '清理',
        });
        if (!ok) return;
        const res = await window.bridge.clean_cache();
        await infoDialog({
          title: '清理缓存',
          tone: (res && res.ok) ? 'info' : 'danger',
          text: (res && res.ok)
            ? (res.freed > 0
                ? `已释放 ${(res.freed / 1048576).toFixed(1)} MB。`
                : '没有可清理的文件。')
            : ((res && res.error) || '清理失败'),
        });
        return;
      }

      if (kind === 'update') {
        const res = await window.bridge.check_update();
        await infoDialog({
          title: '检查更新',
          text: (res && res.ok)
            ? (res.latest && res.latest !== state.version
                ? `发现新版本 ${res.latest}（当前 v${state.version}）。`
                : `当前已是最新版本 v${state.version}。`)
            : ((res && res.error) || '检查失败'),
        });
        return;
      }

      if (kind === 'saveProxy') {
        const input = $('.settings-row input');
        await window.bridge.save_setting('proxy', input ? input.value.trim() : '');
        toast('代理已保存');
        return;
      }

      if (kind === 'repo') {
        await window.bridge.open_path('https://github.com/PolysaCHride/l4d2-mod-manager');
        return;
      }
    }));
  }

'''
    s = s[:start] + new_settings + s[end:]

    # ---------------------------------------------------------- 10) 状态默认值
    s = s.replace("    toastTimer: null,",
                  "    toastTimer: null,\n    settings: {},\n    version: '1.2.1',", 1)

    # ---------------------------------------------------------- 写盘
    TARGET.write_text(s, encoding="utf-8")
    print("app.js 已生成：%d 行（原 %d 行）" % (len(s.splitlines()), len(original.splitlines())))


if __name__ == "__main__":
    main()
