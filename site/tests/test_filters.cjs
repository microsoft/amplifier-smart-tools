/* Executes the production progressive enhancement, not a reimplementation. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '../theme/site.js'), 'utf8');

function element(dataset = {}) {
  return {
    dataset, value: '', hidden: false, textContent: '', listeners: {},
    addEventListener(event, callback) { this.listeners[event] = callback; },
    dispatch(event) { this.listeners[event](); },
    focus() { this.focused = true; },
  };
}

function catalog(withDomain = true) {
  const cards = [
    element({ tool: 'recommended', search: 'isolated failure linux macos', platforms: 'linux macos', domain: 'testing' }),
    element({ tool: 'alternative', search: 'isolated failure linux', platforms: 'linux', domain: 'testing' }),
    element({ tool: 'authoring', search: 'create tool macos', platforms: 'macos', domain: 'authoring' }),
    element({ tool: 'legacy', search: 'failure video windows', platforms: 'windows', domain: '' }),
  ];
  const ids = Object.fromEntries(['tool-search', 'platform', 'result-count',
    'empty-results', 'clear-filters', ...(withDomain ? ['domain'] : [])]
    .map(id => [id, element()]));
  const document = {
    getElementById(id) { return ids[id] || null; },
    querySelectorAll(selector) { return selector === '[data-tool]' ? cards : []; },
  };
  vm.runInNewContext(script, { document });
  return {
    cards, ids,
    visible() { return cards.filter(card => !card.hidden).map(card => card.dataset.tool); },
    set(id, value, event) { ids[id].value = value; ids[id].dispatch(event); },
  };
}

test('all domains initially includes every card and has a correct count', () => {
  const view = catalog();
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
  assert.equal(view.ids['result-count'].textContent, '4 of 4 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
});

test('domain keeps alternatives, and keyword/platform/domain filters combine with AND', () => {
  const view = catalog();
  view.set('domain', 'testing', 'change');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  view.set('tool-search', '  ISOLATED   failure ', 'input');
  view.set('platform', 'macos', 'change');
  assert.deepEqual(view.visible(), ['recommended']);
  assert.equal(view.ids['result-count'].textContent, '1 of 4 tools');
  view.set('domain', 'authoring', 'change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 of 4 tools');
  assert.equal(view.ids['empty-results'].hidden, false);
});

test('not yet classified is independent of keyword/platform filters', () => {
  const view = catalog();
  view.set('domain', '__unclassified__', 'change');
  assert.deepEqual(view.visible(), ['legacy']);
  view.set('tool-search', 'failure', 'input');
  view.set('platform', 'windows', 'change');
  assert.deepEqual(view.visible(), ['legacy']);
  view.set('platform', 'linux', 'change');
  assert.deepEqual(view.visible(), []);
});

test('clear resets all three filters, count, empty state and focus', () => {
  const view = catalog();
  view.set('domain', 'testing', 'change');
  view.set('platform', 'windows', 'change');
  view.set('tool-search', 'no-such-term', 'input');
  view.ids['clear-filters'].dispatch('click');
  for (const id of ['tool-search', 'platform', 'domain']) assert.equal(view.ids[id].value, '');
  assert.equal(view.visible().length, 4);
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['result-count'].textContent, '4 of 4 tools');
  assert.equal(view.ids['tool-search'].focused, true);
});

test('legacy catalog with no domain control still filters and resets', () => {
  const view = catalog(false);
  view.set('tool-search', 'failure', 'input');
  view.set('platform', 'linux', 'change');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  view.ids['clear-filters'].dispatch('click');
  assert.equal(view.visible().length, 4);
});

test('other family pages without search are unchanged and do not require filter controls', () => {
  vm.runInNewContext(script, {
    document: { getElementById() { return null; }, querySelectorAll() { return []; } },
  });
});