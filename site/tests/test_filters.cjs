/* Executes the production progressive enhancement, not a reimplementation. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '../theme/site.js'), 'utf8');

function element(dataset = {}) {
  return {
    dataset, value: '', checked: false, hidden: false, textContent: '', listeners: {},
    addEventListener(event, callback) { this.listeners[event] = callback; },
    dispatch(event) { this.listeners[event](); },
    focus() { this.focused = true; },
  };
}

function catalog(withCategory = true, zeroRecommendations = false) {
  const cards = zeroRecommendations ? [
    element({ tool: 'classified-alpha', search: 'research linux', platforms: 'linux', category: 'testing', recommended: 'false' }),
    element({ tool: 'classified-beta', search: 'research macos', platforms: 'macos', category: 'testing', recommended: 'false' }),
    element({ tool: 'unclassified', search: 'research windows', platforms: 'windows', category: '', recommended: 'false' }),
  ] : [
    element({ tool: 'recommended', search: 'isolated failure linux macos', platforms: 'linux macos', category: 'testing', recommended: 'true' }),
    element({ tool: 'alternative', search: 'isolated failure linux', platforms: 'linux', category: 'testing', recommended: 'false' }),
    element({ tool: 'authoring', search: 'create tool macos', platforms: 'macos', category: 'authoring', recommended: 'false' }),
    element({ tool: 'legacy', search: 'failure video windows', platforms: 'windows', category: '', recommended: 'false' }),
  ];
  const categoryControls = withCategory
    ? ['empty-title', 'empty-hint', 'show-all-tools', 'category', 'recommended-only', 'recommended-filter']
    : [];
  const ids = Object.fromEntries(['tool-search', 'platform', 'result-count',
    'empty-results', 'clear-filters', ...categoryControls]
    .map(id => [id, element()]));
  ids['empty-results'].hidden = true;
  ids['clear-filters'].textContent = withCategory ? 'Clear all filters' : 'Clear filters';
  if (withCategory) {
    ids['recommended-filter'].hidden = true;
    ids['empty-title'].textContent = 'No matching tools.';
    ids['empty-hint'].textContent = 'Try a broader term, another platform, or another category.';
    ids['show-all-tools'].textContent = 'Show all matching tools';
    ids['show-all-tools'].hidden = true;
  }
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

test('all categories and recommendation states are initially included and counted', () => {
  const view = catalog();
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.ids['recommended-filter'].hidden, false);
  assert.equal(view.ids['result-count'].textContent, '4 of 4 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
});

test('Recommended only combines with keyword, platform, and category using AND', () => {
  const view = catalog();
  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  assert.deepEqual(view.visible(), ['recommended']);
  assert.equal(view.ids['result-count'].textContent, '1 of 4 tools');

  view.set('category', 'testing', 'change');
  view.set('tool-search', '  ISOLATED   failure ', 'input');
  view.set('platform', 'macos', 'change');
  assert.deepEqual(view.visible(), ['recommended']);
  view.set('category', 'authoring', 'change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 of 4 tools');
  assert.equal(view.ids['empty-results'].hidden, false);
  assert.equal(view.ids['empty-title'].textContent, 'No Recommended tools match these filters.');
  assert.equal(view.ids['show-all-tools'].hidden, false);
  assert.match(view.ids['empty-hint'].textContent, /include tools without a Recommended designation/);
  view.ids['show-all-tools'].dispatch('click');
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.ids['recommended-only'].focused, true);
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['show-all-tools'].hidden, true);
  assert.equal(view.ids['empty-title'].textContent, 'No matching tools.');
});

test('zero Recommended designations explain the empty filter and restore every tool', () => {
  const view = catalog(true, true);
  assert.deepEqual(view.visible(), ['classified-alpha', 'classified-beta', 'unclassified']);
  assert.equal(view.ids['result-count'].textContent, '3 of 3 tools');
  assert.equal(view.ids['recommended-only'].checked, false);

  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 of 3 tools');
  assert.equal(view.ids['empty-results'].hidden, false);
  assert.equal(view.ids['empty-title'].textContent, 'No tools are currently shown as Recommended.');
  assert.match(view.ids['empty-hint'].textContent, /alternatives and unclassified entries/);
  assert.equal(view.ids['show-all-tools'].hidden, false);
  assert.equal(view.ids['show-all-tools'].textContent, 'Show all matching tools');
  assert.equal(view.ids['clear-filters'].textContent, 'Clear all filters');

  view.ids['show-all-tools'].dispatch('click');
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.ids['recommended-only'].focused, true);
  assert.deepEqual(view.visible(), ['classified-alpha', 'classified-beta', 'unclassified']);
  assert.equal(view.ids['result-count'].textContent, '3 of 3 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['show-all-tools'].hidden, true);
});

test('ordinary alternatives stay visible by default and category can show unclassified', () => {
  const view = catalog();
  view.set('category', 'testing', 'change');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  view.set('category', '__unclassified__', 'change');
  assert.deepEqual(view.visible(), ['legacy']);
  view.set('tool-search', 'failure', 'input');
  view.set('platform', 'windows', 'change');
  assert.deepEqual(view.visible(), ['legacy']);
  view.set('platform', 'linux', 'change');
  assert.deepEqual(view.visible(), []);
});

test('clear resets all four filters, count, empty state and focus', () => {
  const view = catalog();
  view.set('category', 'testing', 'change');
  view.set('platform', 'windows', 'change');
  view.set('tool-search', 'no-such-term', 'input');
  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  view.ids['clear-filters'].dispatch('click');
  for (const id of ['tool-search', 'platform', 'category']) assert.equal(view.ids[id].value, '');
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.visible().length, 4);
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['result-count'].textContent, '4 of 4 tools');
  assert.equal(view.ids['tool-search'].focused, true);
});

test('legacy catalog with no category or recommendation filter still filters and resets', () => {
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
