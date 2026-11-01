/* Headless logic test: run the app script inside a minimal DOM shim. */
'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const APP = path.join(__dirname, '..', 'index.html');
const html = fs.readFileSync(APP, 'utf8');

const scripts = [];
const re = /<script([^>]*)>([\s\S]*?)<\/script>/g;
let m;
while ((m = re.exec(html))) {
  const attrs = m[1] || '';
  if (/type\s*=\s*["']application\/json["']/.test(attrs)) continue;
  scripts.push(m[2]);
}
const appSrc = scripts[scripts.length - 1];
const seedMatch = /<script[^>]*application\/json[^>]*>([\s\S]*?)<\/script>/.exec(html);
const seedText = seedMatch[1];

const RESULT = [];
const ok = (name, cond, extra) => RESULT.push((cond ? 'PASS' : 'FAIL') + ' | ' + name + (extra !== undefined ? ' | ' + extra : ''));

class El {
  constructor(id) {
    this.id = id; this._html = ''; this.textContent = ''; this.value = '';
    this.style = {}; this.dataset = {}; this.files = null;
    this.classList = { add() {}, remove() {}, contains() { return false; }, toggle() {} };
    this.children = [];
  }
  set innerHTML(v) { this._html = String(v); }
  get innerHTML() { return this._html; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener() {}
  setAttribute() {}
  focus() {}
  click() {}
  setSelectionRange() {}
  querySelectorAll() { return []; }
  closest() { return null; }
}

const els = new Map();
const getEl = (id) => {
  if (!els.has(id)) els.set(id, new El(id));
  return els.get(id);
};

const store = new Map();
const localStorage = {
  getItem: k => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: k => store.delete(k),
};

const documentShim = {
  readyState: 'complete',
  documentElement: new El('html'),
  body: new El('body'),
  getElementById: (id) => {
    if (id === 'seed') { const e = new El('seed'); e.textContent = seedText; return e; }
    return getEl(id);
  },
  createElement: (tag) => new El(tag),
  querySelector: (sel) => (sel === '.toast' ? null : new El('q')),
  querySelectorAll: (sel) => {
    const tabs = getEl('tabs').innerHTML;
    const n = (tabs.match(/<button/g) || []).length;
    return { length: sel.includes('button') ? n : 0, forEach() {} };
  },
  addEventListener: () => {},
};

const sandbox = {
  console,
  document: documentShim,
  localStorage,
  setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 1; },
  clearTimeout: () => {}, setInterval: () => 1, clearInterval: () => {},
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  confirm: () => true,
  alert: () => {},
  Blob: class {}, URL: { createObjectURL: () => 'blob:', revokeObjectURL() {} },
  FileReader: class { readAsText() {} },
  SpeechSynthesisUtterance: class {},
  navigator: { userAgent: 'node' },
  requestAnimationFrame: (fn) => setTimeout(fn, 0),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;

const ctx = vm.createContext(sandbox);
try {
  vm.runInContext(appSrc, ctx, { filename: 'app.js' });
} catch (e) {
  console.log('FAIL | app-script-threw | ' + e.message);
  console.log(e.stack.split('\n').slice(0, 4).join('\n'));
  process.exit(1);
}

const g = (name) => vm.runInContext(name, ctx);
const call = (expr) => vm.runInContext(expr, ctx);

try {
  ok('items-count', call('ITEMS.length') === 1078, call('ITEMS.length'));
  const ver = call('VERSION');
  ok('version-injected', typeof ver === 'string' && ver.indexOf('__VERSION__') < 0 && /^v\d+\.\d+\.\d+/.test(ver), ver);
  ok('ids-unique', call('new Set(ITEMS.map(i=>i.id)).size') === call('ITEMS.length'));
  ok('all-labelled', call('ITEMS.filter(i=>!i.label||!i.zh||!i.ans.length).length') === 0);
  ok('syn-alt-answers', call('ITEMS.filter(i=>i.kind==="s").every(i=>i.ans.length>=2)'));
  ok('phr-variants', call('ITEMS.filter(i=>i.kind==="p").reduce((a,i)=>a+(i.ans.length>1?1:0),0)') > 0);
  ok('home-rendered', getEl('app').innerHTML.includes('今日学习'));
  ok('tabs-rendered', call('document.querySelectorAll("nav#tabs button").length') === 4);

  ok('judge-exact', call('judge("transient",["transient"]).level') === 'correct');
  ok('judge-case-space', call('judge("  Transient ",["transient"]).level') === 'correct');
  ok('judge-near', call('judge("transiant",["transient"]).level') === 'near');
  ok('judge-wrong', call('judge("tran",["transient"]).level') === 'wrong');
  ok('judge-empty', call('judge("",["transient"]).level') === 'wrong');
  ok('judge-lenient-space', call('judge("payattentionto",["pay attention to"]).level') === 'correct');
  ok('judge-hyphen', call('judge("second hand",["second-hand"]).level') === 'correct');
  ok('judge-syn-any', call('judge("diversity",["variety","diversity"]).level') === 'correct');
  ok('judge-syn-near', call('judge("divirsity",["variety","diversity"]).level') === 'near');

  const mask = call('maskHTML("pay attention to")');
  ok('mask-shows-first', mask.includes('>p<') && mask.includes('>a<') && mask.includes('>t<'));

  // 预习阶段（新词先学一遍）
  call('db.set.goal=4; db.set.learnFirst=true; startSession({})');
  ok('preview-phase', call('S.session.phase') === 'learn', call('S.session.phase'));
  ok('preview-list', call('S.session.learnIds.length') === 4, call('S.session.learnIds.length'));
  ok('preview-renders', getEl('app').innerHTML.includes('预习') && getEl('app').innerHTML.includes('开始测试') === false);
  const li0 = call('S.session.li');
  call('learnStep(1)');
  ok('preview-advances', call('S.session.li') === li0 + 1);
  call('learnStep(-1)');
  ok('preview-back', call('S.session.li') === li0);
  let guard2 = 0;
  while (call('S.session.phase') === 'learn' && guard2++ < 20) call('learnStep(1)');
  ok('preview-to-test', call('S.session.phase') === 'test' && call('S.q !== null'));
  ok('test-renders', getEl('app').innerHTML.includes('提交答案'));
  call('S.view="home"; S.session=null; render()');

  call('db.set.goal=5; db.set.learnFirst=false; startSession({})');
  ok('session-view', call('S.view') === 'study');
  ok('session-size', call('S.session.ids.length') === 5, call('S.session.ids.length'));
  ok('session-renders', getEl('app').innerHTML.includes('提交答案'));

  const firstId = call('S.session.ids[0]');
  call('S.typed="zzzzz"');
  call('submitAnswer()');
  ok('reveal', call('S.revealed') === true);
  ok('reveal-level', call('S.judgeRes.level') === 'wrong');
  ok('reveal-shows-suggest', getEl('app').innerHTML.includes('sug'));

  const boxBefore = (call('db.items[S.session.ids[0]]') || {}).box || 0;
  call('rate("known")');
  ok('grade-box+1', (call('db.items["' + firstId + '"]') || {}).box === boxBefore + 1);
  ok('grade-due-future', (call('db.items["' + firstId + '"]') || {}).d > Date.now());
  ok('advance', call('S.session.i') === 1);

  const id2 = call('S.session.ids[1]');
  call('S.typed="nope"');
  call('submitAnswer()');
  call('rate("unknown")');
  ok('requeue', call('S.session.ids.filter(x=>x==="' + id2 + '").length') > 1);
  ok('unknown-box0', (call('db.items["' + id2 + '"]') || {}).box === 0);
  ok('wrongbook-flag', call('isWrong("' + id2 + '")') === true);
  ok('daily-log', call('logToday().done') === 2, call('logToday().done'));

  let guard = 0;
  while (call('S.view') === 'study' && guard++ < 80) {
    call('S.typed = S.q.label');
    call('submitAnswer()');
    call('rate("known")');
  }
  ok('finishes', call('S.view') === 'done', call('S.view'));
  ok('done-screen', getEl('app').innerHTML.includes('这一组完成了'));

  call('S.view="wrong"; render()');
  ok('wrong-tab', getEl('app').innerHTML.includes('开始重刷错词'));
  ok('wrong-lists-item', getEl('app').innerHTML.includes(call('BY_ID["' + id2 + '"].label')));

  call('S.view="lib"; S.libQuery="crucial"; render()');
  ok('lib-search', getEl('app').innerHTML.includes('crucial'));
  call('S.libQuery="不存在的词xyz"; render()');
  ok('lib-empty', getEl('app').innerHTML.includes('没有匹配'));

  call('S.view="settings"; render()');
  const setHtml = getEl('app').innerHTML;
  ok('settings-renders', setHtml.includes('每日目标') && setHtml.includes('导出进度'));

  ok('persisted', JSON.parse(store.get('cet6-vocab-v1')).items[id2] !== undefined);
  call('S.view="home"; render()');
  ok('home-back', getEl('app').innerHTML.includes('今日学习'));

  // fuzzy grading path
  call('db.set.goal=3; startSession({})');
  call('S.typed = S.q.label.slice(0,-1) + "x"');
  call('submitAnswer()');
  ok('near-path', ['near', 'correct', 'wrong'].includes(call('S.judgeRes.level')), call('S.judgeRes.level'));
  call('rate("fuzzy")');
  ok('fuzzy-due', (call('db.items[S.session.ids[0]]') || {}).d > Date.now());
} catch (e) {
  RESULT.push('FAIL | assertion-threw | ' + e.message);
}

console.log(RESULT.join('\n'));
const fails = RESULT.filter(r => r.startsWith('FAIL'));
console.log('\nTOTAL=' + RESULT.length + ' FAIL=' + fails.length);
process.exit(fails.length ? 1 : 0);
