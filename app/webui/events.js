/* 后端 → 前端 的事件总线。
 *
 * Python 侧通过 window.__dsh.emit(type, payload) 推送。
 * 前端通过 events.on(type, handler) 订阅。
 */
(function () {
  'use strict';

  const handlers = new Map();

  function on(type, handler) {
    if (!handlers.has(type)) handlers.set(type, new Set());
    handlers.get(type).add(handler);
    return () => handlers.get(type).delete(handler);   // 返回取消订阅
  }

  function emit(type, payload) {
    const set = handlers.get(type);
    if (!set || !set.size) return;
    set.forEach((fn) => {
      try {
        fn(payload);
      } catch (err) {
        console.error('[events] 处理 ' + type + ' 时出错：', err);
      }
    });
  }

  // Python 侧的入口
  window.__dsh = window.__dsh || {};
  window.__dsh.emit = emit;
  window.__dsh.on = on;

  // ------------------------------------------------------------ 内置分发
  // 这些是「所有视图都可能关心」的事件，集中处理一次，
  // 避免每个视图都去挂同样的监听。
  let statsSink = null;   // { setStats(total, enabled) }
  let statusSink = null;  // { scanning(label, pct), idle() }

  // job.log 目前由 app.js 的 runJob 按 job_id 消费；这里只做全局兜底打印，
  // 避免后端日志完全丢失。
  on('job.log', (p) => {
    if (p && p.line) console.debug('[job]', p.line);
  });

  on('job.progress', (p) => {
    if (p && p.phase === 'scan' && statusSink) {
      statusSink.scanning(p.label || '扫描中', p.percent || 0);
    }
  });

  on('stats.changed', (p) => {
    if (statsSink && p) statsSink.setStats(p.total, p.enabled);
  });

  on('mods.changed', (p) => {
    if (statsSink && p && Array.isArray(p.mods)) {
      statsSink.setStats(p.mods.length, p.mods.filter((m) => m.enabled).length);
    }
  });

  on('job.done', () => { if (statusSink) statusSink.idle(); });
  on('job.error', (p) => {
    if (statusSink) statusSink.idle();
    console.error('[events] 任务失败：', p && p.message);
  });

  window.events = {
    on,
    emit,
    /** 由 app.js 在启动时注册，接管状态栏 */
    bindStatus(sink) { statusSink = sink; },
    bindStats(sink) { statsSink = sink; },
  };
})();
