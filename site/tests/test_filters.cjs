/* Executes production filtering against the server-rendered catalog's DOM contract. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '../theme/site.js'), 'utf8');

function element(dataset = {}) {
  return {
    dataset, value: '', checked: false, hidden: false, textContent: '', listeners: {},
    attributes: {}, children: [],
    addEventListener(event, callback) { this.listeners[event] = callback; },
    dispatch(event) { this.listeners[event]?.({ target: this, type: event }); },
    focus() { this.focused = true; },
    setAttribute(name, value) { this.attributes[name] = value; },
    querySelector(selector) { return this.children.find(child => child.selector === selector) || null; },
    querySelectorAll(selector) { return this.children.filter(child => child.selector === selector); },
  };
}

function counter(selector) {
  const node = element();
  node.selector = selector;
  return node;
}

function catalog({ legacy = false, zeroRecommendations = false } = {}) {
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
  const ids = Object.fromEntries([
    'tool-search', 'platform', 'result-count', 'empty-results', 'clear-filters',
    ...(legacy ? [] : [
      'catalog-filters', 'category-navigation', 'category', 'recommended-only',
      'recommended-count', 'other-count', 'other-tools', 'no-recommended',
      'recommended-empty', 'show-all-tools',
    ]),
  ].map(id => [id, element()]));
  ids['empty-results'].hidden = true;
  ids['clear-filters'].textContent = legacy ? 'Clear filters' : 'Clear all filters';

  const groups = [];
  if (!legacy) {
    ids['catalog-filters'].hidden = true;
    ids['category-navigation'].hidden = true;
    ids['other-tools'].hidden = false;
    ids['no-recommended'].hidden = !zeroRecommendations;
    ids['recommended-empty'].hidden = true;
    ids['show-all-tools'].hidden = true;
    for (const category of ['authoring', 'testing', '__unclassified__']) {
      const groupCards = cards.filter(card => card.dataset.recommended !== 'true' &&
        (card.dataset.category || '__unclassified__') === category);
      if (!groupCards.length) continue;
      const group = element({ categoryGroup: category });
      group.children.push(counter('.group-count'));
      group.querySelectorAll = selector => selector === '[data-tool]' ? groupCards : [];
      groups.push(group);
    }
  }

  const categoryButtons = [];
  if (!legacy) {
    for (const identity of ['', 'authoring', 'testing']) {
      const button = element({ categoryFilter: identity });
      button.children.push(counter('.category-tile-count'));
      categoryButtons.push(button);
    }
  }

  const document = {
    getElementById(id) { return ids[id] || null; },
    querySelectorAll(selector) {
      if (selector === '[data-tool]') return cards;
      if (selector === '[data-category-group]') return groups;
      if (selector === '[data-category-filter]') return categoryButtons;
      return [];
    },
  };
  vm.runInNewContext(script, { document });
  return {
    cards, ids, groups, categoryButtons,
    group(category) { return groups.find(group => group.dataset.categoryGroup === category); },
    button(identity) { return categoryButtons.find(button => button.dataset.categoryFilter === identity); },
    visible() { return cards.filter(card => !card.hidden).map(card => card.dataset.tool); },
    set(id, value, event) { ids[id].value = value; ids[id].dispatch(event); },
  };
}

test('recommendations and ordinary tools start in separate visible regions with live totals', () => {
  const view = catalog();
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.ids['catalog-filters'].hidden, false);
  assert.equal(view.ids['category-navigation'].hidden, false);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '3 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.deepEqual(view.groups.map(group => group.hidden), [false, false, false]);
});

test('category tiles update the native select, aria-pressed, group counts, and group visibility', () => {
  const view = catalog();
  const all = view.button('');
  const testing = view.button('testing');
  const authoring = view.button('authoring');
  testing.dispatch('click');
  assert.equal(view.ids.category.value, 'testing');
  assert.equal(testing.attributes['aria-pressed'], 'true');
  assert.equal(all.attributes['aria-pressed'], 'false');
  assert.equal(authoring.attributes['aria-pressed'], 'false');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '1 tool');
  assert.equal(view.group('testing').querySelector('.group-count').textContent, '1 tool');
  assert.equal(view.group('authoring').hidden, true);

  all.dispatch('click');
  assert.equal(view.ids.category.value, '');
  assert.equal(all.attributes['aria-pressed'], 'true');
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
});

test('Recommended only combines with keyword, platform, and category using AND', () => {
  const view = catalog();
  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  assert.deepEqual(view.visible(), ['recommended']);
  assert.equal(view.ids['result-count'].textContent, '1 tool');
  assert.equal(view.ids['other-tools'].hidden, true);

  view.set('category', 'testing', 'change');
  view.set('tool-search', '  ISOLATED   failure ', 'input');
  view.set('platform', 'macos', 'change');
  assert.deepEqual(view.visible(), ['recommended']);
  view.set('category', 'authoring', 'change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['recommended-empty'].hidden, false);
  assert.equal(view.ids['show-all-tools'].hidden, false);
  assert.equal(view.ids['other-tools'].hidden, true);

  view.ids['show-all-tools'].dispatch('click');
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.ids['recommended-only'].focused, true);
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['empty-results'].hidden, false);
  assert.equal(view.ids['show-all-tools'].hidden, true);
});

test('zero recommendations are stated honestly and recovery reveals all tools', () => {
  const view = catalog({ zeroRecommendations: true });
  assert.deepEqual(view.visible(), ['classified-alpha', 'classified-beta', 'unclassified']);
  assert.equal(view.ids['no-recommended'].hidden, false);
  assert.equal(view.ids['no-recommended'].textContent,
    'No tools are currently designated Recommended. Browse all tools below.');
  assert.equal(view.ids['recommended-count'].textContent, '0 tools');
  assert.equal(view.ids['other-count'].textContent, '3 tools');
  assert.equal(view.ids['recommended-only'].checked, false);

  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['show-all-tools'].hidden, false);
  assert.match(view.ids['no-recommended'].textContent, /Turn off Recommended only/);
  assert.equal(view.ids['other-tools'].hidden, true);

  view.ids['show-all-tools'].dispatch('click');
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.equal(view.ids['recommended-only'].focused, true);
  assert.deepEqual(view.visible(), ['classified-alpha', 'classified-beta', 'unclassified']);
  assert.equal(view.ids['recommended-count'].textContent, '0 tools');
  assert.equal(view.ids['other-count'].textContent, '3 tools');
  assert.equal(view.ids['no-recommended'].textContent,
    'No tools are currently designated Recommended. Browse all tools below.');
  assert.equal(view.ids['show-all-tools'].hidden, true);
});

test('category and shared filters keep unclassified tools discoverable', () => {
  const view = catalog();
  view.set('category', '__unclassified__', 'change');
  assert.deepEqual(view.visible(), ['legacy']);
  view.set('tool-search', 'failure', 'input');
  view.set('platform', 'windows', 'change');
  assert.deepEqual(view.visible(), ['legacy']);
  assert.equal(view.ids['other-count'].textContent, '1 tool');
  assert.equal(view.group('__unclassified__').querySelector('.group-count').textContent, '1 tool');
  view.set('platform', 'linux', 'change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.group('__unclassified__').hidden, true);
});

test('tile counts respond to keyword, platform, and Recommended-only filters', () => {
  const view = catalog();
  const all = view.button('');
  const testing = view.button('testing');
  const authoring = view.button('authoring');
  view.set('tool-search', 'isolated', 'input');
  assert.equal(all.querySelector('.category-tile-count').textContent, '2 tools');
  assert.equal(testing.querySelector('.category-tile-count').textContent, '2 tools');
  assert.equal(authoring.querySelector('.category-tile-count').textContent, '0 tools');
  view.set('platform', 'macos', 'change');
  assert.equal(all.querySelector('.category-tile-count').textContent, '1 tool');
  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  assert.equal(testing.querySelector('.category-tile-count').textContent, '1 tool');
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '0 tools');
});

test('clear resets filters and returns focus to search', () => {
  const view = catalog();
  view.set('category', 'testing', 'change');
  view.set('platform', 'windows', 'change');
  view.set('tool-search', 'no-such-term', 'input');
  view.ids['recommended-only'].checked = true;
  view.ids['recommended-only'].dispatch('change');
  view.ids['clear-filters'].dispatch('click');
  for (const id of ['tool-search', 'platform', 'category']) assert.equal(view.ids[id].value, '');
  assert.equal(view.ids['recommended-only'].checked, false);
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  assert.equal(view.ids['tool-search'].focused, true);
  assert.equal(view.categoryButtons[0].attributes['aria-pressed'], 'true');
});

test('legacy catalog without category controls remains filterable', () => {
  const view = catalog({ legacy: true });
  view.set('tool-search', 'failure', 'input');
  view.set('platform', 'linux', 'change');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  view.ids['clear-filters'].dispatch('click');
  assert.equal(view.visible().length, 4);
});

test('other family pages without catalog search remain unaffected', () => {
  vm.runInNewContext(script, {
    document: { getElementById() { return null; }, querySelectorAll() { return []; } },
  });
});
