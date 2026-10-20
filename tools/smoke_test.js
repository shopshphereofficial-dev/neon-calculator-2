/* Headless smoke test for the Neon Calculator 2 web bundle.
 * Runs the real bundled script against a minimal DOM stub and exercises
 * the calculator engine, scientific mode and the unit converter.
 *   node tools/smoke_test.js
 */
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'www', 'index.html'), 'utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];

// ---- minimal DOM stub -------------------------------------------------------
function makeEl(id) {
  const el = {
    id, textContent: '', innerHTML: '', value: '', hidden: false, className: '',
    style: {}, dataset: {}, children: [],
    classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
    addEventListener() {}, appendChild(c) { this.children.push(c); },
    add(o) { this.children.push(o); }, append(...c) { this.children.push(...c); },
    click() {}, querySelector() { return makeEl('x'); },
    set innerText(v) { this.textContent = v; }, get innerText() { return this.textContent; },
  };
  return el;
}
const els = {};
const store = {};
global.localStorage = {
  getItem: k => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};
global.Option = function (text, value) { return { text, value }; };
global.document = {
  getElementById: id => (els[id] = els[id] || makeEl(id)),
  createElement: tag => makeEl(tag),
  querySelector: () => makeEl('q'),
  querySelectorAll: () => [],
  addEventListener() {},
  visibilityState: 'visible',
};
global.window = { addEventListener() {}, AudioContext: undefined, webkitAudioContext: undefined };
global.navigator = { clipboard: { writeText: async () => {} } };
global.setTimeout = (fn) => fn;

// Expose the bundle's top-level bindings for assertions.
const runner = new Function(
  js + '\n;return {press,calc,fmt,convert,tone,units,history:()=>history,expr:()=>expr,result:()=>result,fillUnits};'
);
const api = runner();

// ---- assertions -------------------------------------------------------------
let pass = 0, fail = 0;
function check(name, got, want) {
  const ok = String(got) === String(want);
  ok ? pass++ : fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : `  (got ${got}, want ${want})`}`);
}

check('basic add', api.calc('2+3'), '5');
check('precedence', api.calc('2+3×4'), '14');
check('division', api.calc('10÷4'), '2.5');
check('decimal precision', api.calc('0.1+0.2'), '0.3');
check('percent', api.calc('50%'), '0.5');
check('sqrt', api.calc('√(81)'), '9');
check('square', api.calc('7²'), '49');
check('power', api.calc('2**10'), '1024');
check('sin 30deg', api.calc('sin(30)'), '0.5');
check('ln e', api.calc('ln(e)'), '1');
check('log 1000', api.calc('log(1000)'), '3');
check('pi', api.calc('π'), '3.1415926536');
check('negative', api.calc('−5+2'), '-3');
check('math error surfaces', (() => { try { api.calc('1/0'); return 'no-throw'; } catch (e) { return 'threw'; } })(), 'threw');
check('injection blocked', (() => { try { api.calc('window.location'); return 'no-throw'; } catch (e) { return 'threw'; } })(), 'threw');

// keypad flow
api.press('7'); api.press('+'); api.press('3'); api.press('=');
check('keypad 7+3', api.result(), '10');
check('history recorded', api.history().length, 1);
check('history persisted to localStorage', !!store['neoncalc.history'], 'true');
api.press('AC');
check('AC clears', api.result(), '0');

// converter
els.amount.value = '1';
els.fromUnit.value = 'Kilometer';
els.toUnit.value = 'Meter';
api.convert();
check('1 km -> m', els.converted.textContent, '1000');
els.amount.value = '1';
els.fromUnit.value = 'Inch';
els.toUnit.value = 'Centimeter';
api.convert();
check('1 in -> cm', els.converted.textContent, '2.54');

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
