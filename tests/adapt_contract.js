/* Node 侧契约测试：锁死 adapt() 的输入输出。
 *
 * 为什么需要这个：
 *   api._to_mod()  ←→  app.js adapt()  是一对。
 *   改一边忘另一边，前端拿到 undefined，被 || '' / || 0 兜底 ——
 *   界面照常渲染、只是数据错了，不会报任何错（静默降级）。
 *
 * Python 侧 tests/test_webui_contract.py 锁的是 _to_mod 的**输出字段集**；
 * 这个文件锁的是 adapt 的**输入字段名**和**换算规则**，两边合起来才是完整的。
 *
 * 运行：
 *   node tests/adapt_contract.js
 *   （.venv 无关，不需要任何依赖；退出码非 0 即失败）
 */
'use strict';

const path = require('path');
const app = require(path.join(__dirname, '..', 'app', 'webui', 'app.js'));

let failures = 0;

function check(name, fn) {
  try {
    fn();
    console.log('  ok   ' + name);
  } catch (err) {
    failures += 1;
    console.error('  FAIL ' + name);
    console.error('       ' + (err && err.message ? err.message : err));
  }
}

function eq(actual, expected, what) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) throw new Error((what || '') + ' 期望 ' + e + '，实际 ' + a);
}

function ok(cond, what) {
  if (!cond) throw new Error(what);
}

// _to_mod() 的输出字段集，必须与 tests/test_webui_contract.py 里的断言一致。
// 这是前后端之间唯一的书面契约。
const BACKEND_FIELDS = [
  'file', 'title', 'alias', 'category', 'item',
  'size', 'sizeText', 'enabled', 'workshop_id', 'thumb',
  'added', 'addedText', 'pinned',
  'autoCategory', 'autoItem', 'collection',
];

// adapt() 的输出字段集。加字段必须显式改这里。
const FRONTEND_FIELDS = [
  'id', 'name', 'alias', 'cat', 'item', 'size', 'img',
  'enabled', 'added', 'addedDate', 'file', 'ws',
  'pinned', 'autoCat', 'autoItem', 'coll',
];

// 后端有、但 adapt 有意不接的字段。
const DROPPED_BY_ADAPT = ['sizeText', 'addedText'];

function baseRecord(over) {
  return Object.assign({
    file: '1127584577.vpk',
    title: 'Koharu [Replace Ellis]',
    alias: '',
    category: '角色',
    item: 'Ellis',
    size: 116100000,
    sizeText: '110.7 MB',
    enabled: false,
    workshop_id: '',
    thumb: '',
    added: 1729087521,
    addedText: '2 天前',
    pinned: false,
    autoCategory: null,
    autoItem: null,
    collection: '',
  }, over || {});
}

console.log('adapt() 契约');

check('输出字段集是冻结的', () => {
  eq(Object.keys(app.adapt(baseRecord())), FRONTEND_FIELDS, 'adapt 字段集');
});

check('后端每个字段都被 adapt 显式处理（接收或明确丢弃）', () => {
  // adapt 的输入是 _to_mod 的输出。这里做一次集合运算：
  // BACKEND_FIELDS 里的每一项，要么出现在 FRONTEND_FIELDS 的映射里，
  // 要么必须列在 DROPPED_BY_ADAPT。
  const handled = new Set(DROPPED_BY_ADAPT.concat([
    // 字段改名映射：后端名 → 前端名
    'file', 'title', 'alias', 'category', 'item',
    'size', 'enabled', 'workshop_id', 'thumb', 'added',
    // 2026-11-20 新增的映射
    'pinned',        // → pinned（原样）
    'autoCategory',  // → autoCat
    'autoItem',      // → autoItem
    'collection',    // → coll
  ]));
  const unhandled = BACKEND_FIELDS.filter((f) => !handled.has(f));
  eq(unhandled, [], '这些后端字段既没被 adapt 接收、也没登记为丢弃');
});

check('file → id 与 file 同一个值（历史遗留的两份）', () => {
  const out = app.adapt(baseRecord({ file: 'x.vpk' }));
  eq(out.id, 'x.vpk', 'id');
  eq(out.file, 'x.vpk', 'file');
});

check('title 缺失时退回文件名而不是空串', () => {
  const out = app.adapt(baseRecord({ title: '', file: 'fallback.vpk' }));
  eq(out.name, 'fallback.vpk', 'name 兜底');
});

check('category 缺失时退回「未分类」而不是空串', () => {
  const out = app.adapt(baseRecord({ category: '' }));
  eq(out.cat, '未分类', 'cat 兜底');
});

check('size 从字节换算成 MB（除以 1048576）', () => {
  const out = app.adapt(baseRecord({ size: 1048576 }));
  eq(out.size, 1, '1MB');
  const zero = app.adapt(baseRecord({ size: 0 }));
  eq(zero.size, 0, '0 字节');
  const missing = app.adapt(baseRecord({ size: undefined }));
  eq(missing.size, 0, '缺失按 0');
});

check('added 从「秒级时间戳」换算成「几天前」', () => {
  // 同名不同义，这是最容易踩的一处（HANDOFF §5）。
  const now = Math.floor(Date.now() / 1000);
  eq(app.adapt(baseRecord({ added: now })).added, 0, '今天');
  eq(app.adapt(baseRecord({ added: now - 86400 })).added, 1, '1 天前');
  eq(app.adapt(baseRecord({ added: now - 86400 * 7 })).added, 7, '7 天前');
});

check('added 缺失或 0 时不出现负数或 NaN', () => {
  const zero = app.adapt(baseRecord({ added: 0 }));
  eq(zero.added, 0, 'added=0');
  eq(zero.addedDate, '', 'addedDate 空');
  const missing = app.adapt(baseRecord({ added: undefined }));
  eq(missing.added, 0, 'added 缺失');
  ok(!Number.isNaN(missing.added), '不能是 NaN');
});

check('addedDate 用本地时区格式化成 YYYY-MM-DD', () => {
  const out = app.adapt(baseRecord({ added: 1700000000 }));
  ok(/^\d{4}-\d{2}-\d{2}$/.test(out.addedDate), '格式应为 YYYY-MM-DD，实际 ' + out.addedDate);
});

check('enabled 严格布尔（前端用 !!x 和 ===）', () => {
  eq(app.adapt(baseRecord({ enabled: 1 })).enabled, true, 'truthy → true');
  eq(app.adapt(baseRecord({ enabled: 0 })).enabled, false, 'falsy → false');
  eq(app.adapt(baseRecord({ enabled: undefined })).enabled, false, 'undefined → false');
});

check('thumb 为空时 img 是空串（不是 undefined）', () => {
  // 空串让前端画占位；undefined 会让 <img src="undefined"> 裂图。
  eq(app.adapt(baseRecord({ thumb: '' })).img, '', '空 thumb');
  const uri = app.adapt(baseRecord({ thumb: 'data:image/jpeg;base64,AAAA' })).img;
  eq(uri, 'data:image/jpeg;base64,AAAA', 'data URI 原样透传');
});

check('workshop_id → ws 原样保留为字符串', () => {
  eq(app.adapt(baseRecord({ workshop_id: '3659210344' })).ws, '3659210344', '字符串 ID');
  // 数字必须被转成字符串：否则拼进 steam:// 链接会出错、=== 比较也会失效。
  const numeric = app.adapt(baseRecord({ workshop_id: 3659210344 })).ws;
  eq(typeof numeric, 'string', 'ws 必须是字符串，实际 ' + typeof numeric);
  eq(numeric, '3659210344', '数字 ID 转字符串');
  eq(app.adapt(baseRecord({ workshop_id: null })).ws, '', 'null → 空串');
  eq(app.adapt(baseRecord({ workshop_id: undefined })).ws, '', 'undefined → 空串');
});

check('pinned：后端传了就必须接住（原来被静默丢弃）', () => {
  eq(app.adapt(baseRecord({ pinned: true })).pinned, true, 'pinned=true');
  eq(app.adapt(baseRecord({ pinned: false })).pinned, false, 'pinned=false');
  eq(app.adapt(baseRecord({ pinned: undefined })).pinned, false, '缺失按 false');
});

check('autoCat/autoItem：null 表示从没改过分类', () => {
  // 三态必须能区分：
  //   null      → 用户从没改过，前端不展示「识别结果」
  //   ''        → 改过，但识别结果是空分类
  //   '角色'    → 改过，识别结果是角色
  const never = app.adapt(baseRecord({ autoCategory: null, autoItem: null }));
  eq(never.autoCat, null, '从没改过时 autoCat 必须是 null（不是空串）');
  eq(never.autoItem, null, '从没改过时 autoItem 必须是 null');

  const empty = app.adapt(baseRecord({ autoCategory: '', autoItem: '' }));
  eq(empty.autoCat, '', '改过但识别为空时是空串');

  const real = app.adapt(baseRecord({ category: '杂项',
    autoCategory: '角色', autoItem: 'Ellis' }));
  eq(real.cat, '杂项', '当前分类是用户值');
  eq(real.autoCat, '角色', 'autoCat 是识别值');
  eq(real.autoItem, 'Ellis', 'autoItem 是识别值');
});

check('collection → coll：合集归属必须透出（A-1 根因）', () => {
  eq(app.adapt(baseRecord({ collection: 'ws_189971863' })).coll,
     'ws_189971863', '合集 ID');
  eq(app.adapt(baseRecord({ collection: '' })).coll, '', '无归属是空串');
  eq(app.adapt(baseRecord({ collection: undefined })).coll, '', 'undefined→空串');
});

check('空对象不抛异常且给出安全默认值', () => {
  const out = app.adapt({});
  eq(out.id, '', 'id');
  eq(out.name, '', 'name');
  eq(out.cat, '未分类', 'cat');
  eq(out.size, 0, 'size');
  eq(out.enabled, false, 'enabled');
});

console.log('\n枚举一致性');

check('CATEGORY_OPTIONS 覆盖 core 的 CATEGORIES', () => {
  const coreCats = ['角色', '特感', '枪械', '近战', '医疗品', '投掷',
    'UI', '音效音乐', '载具', '弹药', '材质特效', '动作',
    '地图', '杂项', '其他', '未分类'];
  eq(app.CATEGORY_OPTIONS.slice().sort(), coreCats.slice().sort(), '分类集合');
});

check('RAIL_DEFS 覆盖全部分类（否则模组会「消失」）', () => {
  const covered = new Set();
  app.RAIL_DEFS.forEach((d) => {
    if (d.cats === null) return;          // all
    d.cats.forEach((c) => covered.add(c));
  });
  const missing = app.CATEGORY_OPTIONS.filter((c) => !covered.has(c));
  eq(missing, [], '这些分类不在任何 rail 里，对应模组看不见');
});

console.log('\n标题三层兜底（别名 → 模组标题 → vpk 文件名）');

// 这条链必须和 Python 侧 `_to_mod` 的 title 兜底接得上：
//   _to_mod:  title = rec["title"] or rec["file"]      （永远非空，末层是完整文件名）
//   adapt:    name  = apiMod.title or apiMod.file
//   displayTitle: alias → name → file
check('有别名时用别名', () => {
  eq(app.displayTitle({ alias: '夏日甜点屋', name: 'VRC プラム', file: '3664792140.vpk' }),
     '夏日甜点屋');
});

check('无别名时用模组标题', () => {
  eq(app.displayTitle({ alias: '', name: 'The Bloody Moors', file: '189941645.vpk' }),
     'The Bloody Moors');
});

check('都没有时用完整 vpk 文件名（含扩展名）', () => {
  eq(app.displayTitle({ alias: '', name: '', file: '189941645.vpk' }), '189941645.vpk');
});

check('全是空白字符视为没有，继续往下兜底', () => {
  eq(app.displayTitle({ alias: '   ', name: '  ', file: 'a.vpk' }), 'a.vpk');
});

check('别名两端空格会被裁掉', () => {
  eq(app.displayTitle({ alias: '  甜点屋  ', name: 'X', file: 'a.vpk' }), '甜点屋');
});

check('三层都缺也不会返回 undefined', () => {
  eq(app.displayTitle({}), '');
});

console.log('\n子分类统一（item 空时回落到合集名）');

// 合集表夹具：两个章节共用
const COLLS = {
  ws_1: { name: 'The Bloody Moors', workshop_id: '1',
          files: ['a.vpk', 'b.vpk', 'c.vpk'] },
};


check('item 有值时就是子分类', () => {
  eq(app.displayItem({ item: 'Ellis', coll: 'ws_1' }, COLLS), 'Ellis');
});

check('item 为空但属于合集 → 回落到合集名', () => {
  eq(app.displayItem({ item: '', coll: 'ws_1' }, COLLS), 'The Bloody Moors');
});

check('item 为空白也算空', () => {
  eq(app.displayItem({ item: '   ', coll: 'ws_1' }, COLLS), 'The Bloody Moors');
});

check('item 为空且不属于合集 → 空串', () => {
  eq(app.displayItem({ item: '', coll: '' }, COLLS), '');
});

check('回落不修改原对象（只读兜底）', () => {
  const m = { item: '', coll: 'ws_1' };
  app.displayItem(m, COLLS);
  eq(m.item, '', 'displayItem 不能改 m.item');
});

console.log('\n子分类列表（排序 / 去重 / 自动消失）');

const SUBS_MODS = [
  { cat: '地图', item: 'Zeta', coll: '' },
  { cat: '地图', item: 'Alpha', coll: '' },
  { cat: '地图', item: 'Mid', coll: '' },
  { cat: '地图', item: 'Alpha', coll: '' },          // 重复
  { cat: '地图', item: '', coll: 'ws_1' },           // 靠合集名回落
  { cat: '角色', item: 'Ellis', coll: '' },          // 别的分类
];

check('按名称排序（不是按数量）', () => {
  eq(app.subItemsOf('地图', SUBS_MODS, COLLS),
     ['Alpha', 'Mid', 'The Bloody Moors', 'Zeta']);
});

check('中文在前、英文在后（中文内部按拼音）', () => {
  // 用户明确要的排序：中文优先。localeCompare(zh) 在 Node 与 WebView2 里一致，
  // 这条断言把「中文在前」钉住，避免以后换成普通字符串比较就悄悄变了。
  eq(app.subItemsOf('地图', [
    { cat: '地图', item: 'Zeta' },
    { cat: '地图', item: '地心引力' },
    { cat: '地图', item: 'Alpha' },
    { cat: '地图', item: '档案：零' },
    { cat: '地图', item: '广州' },
  ], {}), ['档案：零', '地心引力', '广州', 'Alpha', 'Zeta']);
});

check('去重', () => {
  const list = app.subItemsOf('地图', SUBS_MODS, COLLS);
  eq(list.filter((x) => x === 'Alpha').length, 1);
});

check('只看指定一级分类', () => {
  eq(app.subItemsOf('角色', SUBS_MODS, COLLS), ['Ellis']);
});

check('item 为空的模组按合集名参与子分类', () => {
  ok(app.subItemsOf('地图', SUBS_MODS, COLLS).indexOf('The Bloody Moors') >= 0,
     '合集名没有进入子分类列表');
});

check('最后一个模组移走后子分类自动消失', () => {
  const before = app.subItemsOf('地图', SUBS_MODS, COLLS);
  ok(before.indexOf('Zeta') >= 0, '前置条件：Zeta 应在列表里');
  const after = app.subItemsOf('地图',
    SUBS_MODS.filter((m) => m.item !== 'Zeta'), COLLS);
  eq(after.indexOf('Zeta'), -1, '没有模组引用后不该再出现');
});

check('没有子分类时返回空数组', () => {
  eq(app.subItemsOf('枪械', SUBS_MODS, COLLS), []);
});

console.log('\n卡片合集标签（合集名 (x/x)）');

check('合集成员显示名称与序号', () => {
  eq(app.collectionTag({ coll: 'ws_1', file: 'b.vpk', pinned: false }, COLLS),
     'The Bloody Moors (2/3)');
});

check('首尾成员序号正确', () => {
  eq(app.collectionTag({ coll: 'ws_1', file: 'a.vpk', pinned: false }, COLLS),
     'The Bloody Moors (1/3)');
  eq(app.collectionTag({ coll: 'ws_1', file: 'c.vpk', pinned: false }, COLLS),
     'The Bloody Moors (3/3)');
});

check('不属于合集 → 不渲染（返回空串）', () => {
  eq(app.collectionTag({ coll: '', file: 'a.vpk', pinned: false }, COLLS), '');
});

check('合集里找不到这个文件 → 只显示合集名，不编序号', () => {
  eq(app.collectionTag({ coll: 'ws_1', file: 'zzz.vpk', pinned: false }, COLLS),
     'The Bloody Moors');
});

check('用户改过子分类（pinned 且不同于合集名）→ 只显示用户值，不带编号', () => {
  eq(app.collectionTag({ coll: 'ws_1', file: 'a.vpk', pinned: true, item: '沼泽地图' }, COLLS),
     '沼泽地图');
});

check('pinned 但子分类与合集名相同 → 仍显示编号', () => {
  eq(app.collectionTag({ coll: 'ws_1', file: 'a.vpk', pinned: true,
                         item: 'The Bloody Moors' }, COLLS),
     'The Bloody Moors (1/3)');
});

check('空 collections 不应崩', () => {
  eq(app.collectionTag({ coll: 'ws_1', file: 'a.vpk' }, {}), '');
});

console.log('\n写入闸门（game.unknown）');

check('running=true 时禁止写入', () => {
  ok(app.writeBlockedOf(true, false).length > 0, '运行中必须被拦');
});

check('检测失败(unknown=true)时也禁止写入', () => {
  // 这是 HANDOFF §7.2 / §9.2 那条隐患：检测失败不能当成「没运行」。
  ok(app.writeBlockedOf(false, true).length > 0, 'unknown 必须被拦');
});

check('只有两者都 false 才放行', () => {
  eq(app.writeBlockedOf(false, false), '', '可以写时返回空串');
});

console.log('');
if (failures) {
  console.error('失败 ' + failures + ' 项');
  process.exit(1);
}
console.log('全部通过');
