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
    options: [], selectedIndex: 0,
    parentElement: null,
    attributes: {}, children: [],
    addEventListener(event, callback) { this.listeners[event] = callback; },
    dispatch(event) { this.listeners[event]?.({ target: this, type: event }); },
    focus() { this.focused = true; },
    setAttribute(name, value) { this.attributes[name] = value; },
    appendChild(child) {
      if (child.parentElement) {
        const oldIndex = child.parentElement.children.indexOf(child);
        if (oldIndex !== -1) child.parentElement.children.splice(oldIndex, 1);
      }
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    querySelector(selector) { return this.children.find(child => child.selector === selector) || null; },
    querySelectorAll(selector) { return this.children.filter(child => child.selector === selector); },
  };
}

function counter(selector) {
  const node = element();
  node.selector = selector;
  return node;
}

function catalog({
  legacy = false,
  zeroRecommendations = false,
  twoRecommendations = false,
  duplicateCountFixture = false,
} = {}) {
  const card = (dataset, heading = dataset.name || dataset.tool) => {
    const result = element(dataset);
    const title = element();
    title.selector = 'h2';
    title.textContent = heading;
    result.children.push(title);
    return result;
  };
  const allToolCards = duplicateCountFixture ? [
    card({ tool: 'digital-twin-universe', name: 'Digital Twin Universe', search: 'digital twin test environments linux', platforms: 'linux', category: 'testing', recommended: 'true' }),
    card({ tool: 'smart-tool-creator', name: 'Smart Tool Creator', search: 'smart tool development macos', platforms: 'macos', category: 'authoring', recommended: 'true' }),
    card({ tool: 'ordinary', name: 'Ordinary', search: 'test environments linux', platforms: 'linux', category: 'testing', recommended: 'false' }),
  ] : zeroRecommendations ? [
    card({ tool: 'classified-alpha', name: 'Classified Alpha', search: 'research linux', platforms: 'linux', category: 'testing', recommended: 'false' }),
    card({ tool: 'classified-beta', name: 'Classified Beta', search: 'research macos', platforms: 'macos', category: 'testing', recommended: 'false' }),
    card({ tool: 'unclassified', name: 'Unclassified', search: 'unclassified research windows other', platforms: 'windows', category: '', recommended: 'false' }),
  ] : [
    card({ tool: 'recommended', name: 'Recommended', search: 'isolated failure linux macos test environments', platforms: 'linux macos', category: 'testing', recommended: 'true' }),
    card({ tool: 'alternative', name: 'Alternative', search: 'isolated failure linux test environments', platforms: 'linux', category: 'testing', recommended: 'false' }),
    card({ tool: 'authoring', name: '', search: 'echo create tool macos tool authoring', platforms: 'macos', category: 'authoring', recommended: 'false' }, 'Echo'),
    card({ tool: 'legacy', name: 'Able', search: 'able failure video windows other', platforms: 'windows', category: '', recommended: 'false' }),
    ...(twoRecommendations ? [
      card({ tool: 'recommended-two', name: 'Another Recommended', search: 'create tool macos', platforms: 'macos', category: 'authoring', recommended: 'true' }),
    ] : []),
  ];
  const featuredCards = legacy ? [] : allToolCards
    .filter(item => item.dataset.recommended === 'true')
    .map(item => card({ ...item.dataset }));
  const cards = legacy ? allToolCards : [...featuredCards, ...allToolCards];
  const ids = Object.fromEntries([
    'tool-search', 'platform', 'result-count', 'empty-results', 'clear-filters',
    ...(legacy ? [] : [
      'catalog-filters', 'category', 'tool-sort', 'other-tools-by-name',
      'recommended-tools', 'recommended-count', 'other-count', 'other-tools',
      'recommended-region', 'other-empty',
    ]),
  ].map(id => [id, element()]));
  if (!legacy) {
    const categorySelect = ids.category;
    categorySelect.value = '';
  }
  ids['empty-results'].hidden = true;
  ids['clear-filters'].textContent = 'Clear filters';
  const recommendedGrid = ids['recommended-tools'];
  const nameGrid = ids['other-tools-by-name'];
  if (!legacy) {
    ids['tool-sort'].value = 'category';
    nameGrid.hidden = true;
  }

  const groups = [];
  const groupGrids = [];
  if (!legacy) {
    ids['catalog-filters'].hidden = true;
    ids['other-tools'].hidden = false;
    ids['other-tools'].querySelectorAll = selector =>
      selector === '[data-tool]' ? allToolCards : [];
    ids['recommended-region'].querySelectorAll = selector =>
      selector === '[data-tool]' ? featuredCards : [];
    recommendedGrid.querySelectorAll = selector =>
      selector === '[data-tool]' ? featuredCards : [];
    ids['other-empty'].hidden = true;
    ids['recommended-region'].hidden = zeroRecommendations;
    for (const category of ['authoring', 'testing', '__unclassified__']) {
      const groupCards = allToolCards.filter(card =>
        (card.dataset.category || '__unclassified__') === category);
      if (!groupCards.length) continue;
      const group = element({ categoryGroup: category });
      const grid = element();
      group.appendChild(grid);
      const groupCount = counter('.group-count');
      group.querySelector = selector => selector === '.group-count' ? groupCount : null;
      group.grid = grid;
      for (const groupCard of groupCards) grid.appendChild(groupCard);
      groups.push(group);
      groupGrids.push(grid);
    }
    for (const recommended of featuredCards) recommendedGrid.appendChild(recommended);
  }

  const document = {
    getElementById(id) { return ids[id] || null; },
    querySelectorAll(selector) {
      if (selector === '[data-tool]') return cards;
      if (selector === '[data-category-group]') return groups;
      return [];
    },
  };
  vm.runInNewContext(script, { document });
  const originalParents = new Map(allToolCards.map(card => [card, card.parentElement]));
  return {
    cards, allToolCards, featuredCards, ids, groups, groupGrids, originalParents, recommendedGrid, nameGrid,
    group(category) { return groups.find(group => group.dataset.categoryGroup === category); },
    visible() { return allToolCards.filter(card => !card.hidden).map(card => card.dataset.tool); },
    visibleFeatured() { return featuredCards.filter(card => !card.hidden).map(card => card.dataset.tool); },
    placed() {
      return [
        ...recommendedGrid.children.filter(child => child.dataset.tool),
        ...nameGrid.children.filter(child => child.dataset.tool),
        ...groupGrids.flatMap(grid => grid.children.filter(child => child.dataset.tool)),
      ];
    },
    set(id, value, event) { ids[id].value = value; ids[id].dispatch(event); },
  };
}

test('recommendations and ordinary tools start in separate visible regions with live totals', () => {
  const view = catalog({ duplicateCountFixture: true });
  assert.deepEqual(view.visible(), ['digital-twin-universe', 'smart-tool-creator', 'ordinary']);
  assert.deepEqual(view.visibleFeatured(), ['digital-twin-universe', 'smart-tool-creator']);
  assert.equal(view.cards.length, 5);
  assert.equal(new Set(view.cards.map(card => card.dataset.tool)).size, 3);
  assert.equal(view.ids['catalog-filters'].hidden, false);
  assert.equal(view.ids['tool-sort'].value, 'category');
  assert.equal(view.nameGrid.hidden, true);
  assert.equal(view.ids['result-count'].textContent, '3 tools');
  assert.equal(view.ids['recommended-count'].textContent, '2 tools');
  assert.equal(view.ids['other-count'].textContent, '3 tools');
  assert.equal(view.allToolCards.filter(card => card.dataset.recommended === 'true').length, 2);
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['recommended-region'].hidden, false);
  assert.equal(view.ids['other-empty'].hidden, true);
  assert.deepEqual(view.groups.map(group => group.hidden), [false, false]);

  view.set('tool-search', 'digital twin', 'input');
  view.set('category', 'testing', 'change');
  view.set('platform', 'linux', 'change');
  assert.deepEqual(view.visible(), ['digital-twin-universe']);
  assert.deepEqual(view.visibleFeatured(), ['digital-twin-universe']);
  assert.equal(view.ids['result-count'].textContent, '1 tool');
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '1 tool');
});

test('Name is a global stable alphabetical list; Category restores original groups without duplicates', () => {
  const view = catalog();
  const originalParents = new Map(view.originalParents);
  view.set('tool-sort', 'name', 'change');

  assert.deepEqual(view.nameGrid.children.map(card => card.dataset.tool),
    ['legacy', 'alternative', 'authoring', 'recommended']);
  assert.deepEqual(view.recommendedGrid.children.map(card => card.dataset.tool), ['recommended']);
  assert.deepEqual(view.groups.map(group => group.hidden), [true, true, true]);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  assert.equal(view.ids['other-count'].textContent, '4 tools');
  assert.deepEqual(view.placed().map(card => card.dataset.tool),
    ['recommended', 'legacy', 'alternative', 'authoring', 'recommended']);
  assert.equal(new Set(view.placed()).size, view.cards.length);

  view.set('tool-sort', 'category', 'change');
  assert.equal(view.nameGrid.hidden, true);
  assert.deepEqual(view.groups.map(group => group.hidden), [false, false, false]);
  for (const [card, parent] of originalParents) assert.equal(card.parentElement, parent);
  assert.deepEqual(view.placed().map(card => card.dataset.tool),
    ['recommended', 'authoring', 'recommended', 'alternative', 'legacy']);
  assert.equal(new Set(view.placed()).size, view.cards.length);
});

test('two featured recommendations remain above Name-sorted All tools and survive clear', () => {
  const view = catalog({ twoRecommendations: true });
  view.set('tool-sort', 'name', 'change');

  assert.deepEqual(view.recommendedGrid.children.map(card => card.dataset.tool),
    ['recommended', 'recommended-two']);
  assert.equal(view.featuredCards.filter(card => card.dataset.recommended === 'true').length, 2);
  assert.equal(view.allToolCards.filter(card => card.dataset.recommended === 'true').length, 2);
  assert.deepEqual(view.nameGrid.children.map(card => card.dataset.tool),
    ['legacy', 'alternative', 'recommended-two', 'authoring', 'recommended']);
  assert.deepEqual(view.placed().slice(0, 2).map(card => card.dataset.tool),
    ['recommended', 'recommended-two']);
  assert.equal(view.ids['result-count'].textContent, '5 tools');
  assert.equal(view.ids['recommended-count'].textContent, '2 tools');
  assert.equal(view.ids['other-count'].textContent, '5 tools');
  assert.equal(new Set(view.placed()).size, view.cards.length);

  view.set('tool-search', 'no-such-tool', 'input');
  assert.equal(view.ids['result-count'].textContent, '0 tools');
  assert.equal(view.ids['recommended-count'].textContent, '0 tools');
  assert.equal(view.ids['other-count'].textContent, '0 tools');
  view.ids['clear-filters'].dispatch('click');

  assert.equal(view.ids['tool-sort'].value, 'name');
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy', 'recommended-two']);
  assert.deepEqual(view.visibleFeatured(), ['recommended', 'recommended-two']);
  assert.deepEqual(view.nameGrid.children.map(card => card.dataset.tool),
    ['legacy', 'alternative', 'recommended-two', 'authoring', 'recommended']);
  assert.equal(view.ids['result-count'].textContent, '5 tools');
  assert.equal(view.ids['recommended-count'].textContent, '2 tools');
  assert.equal(view.ids['other-count'].textContent, '5 tools');
});

test('ordering changes only Tools while shared filters retain their counts', () => {
  const view = catalog();
  view.set('tool-search', 'failure', 'input');
  view.set('platform', 'linux', 'change');
  view.set('category', 'testing', 'change');
  view.set('tool-sort', 'name', 'change');

  assert.equal(view.ids['tool-search'].value, 'failure');
  assert.equal(view.ids.platform.value, 'linux');
  assert.equal(view.ids.category.value, 'testing');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  assert.equal(view.ids['result-count'].textContent, '2 tools');
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '2 tools');
  assert.equal(view.group('testing').querySelector('.group-count').textContent, '2 tools');
  assert.deepEqual(view.nameGrid.children.filter(card => !card.hidden).map(card => card.dataset.tool),
    ['alternative', 'recommended']);
  assert.equal(view.ids['recommended-region'].hidden, false);
  assert.equal(view.ids['other-empty'].hidden, true);
});

test('category selection updates counts without inserting category-scope copy', () => {
  const view = catalog();
  view.set('category', 'testing', 'change');
  assert.equal(view.ids.category.value, 'testing');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  assert.equal(view.ids['recommended-region'].hidden, false);
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '2 tools');
  assert.equal(view.group('testing').querySelector('.group-count').textContent, '2 tools');
  assert.equal(view.group('authoring').hidden, true);

  view.set('category', '', 'change');
  assert.equal(view.ids.category.value, '');
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
});

test('zero matching recommendations hide that region; global empty state is not duplicated', () => {
  const view = catalog();
  view.set('category', 'testing', 'change');
  view.set('tool-search', '  ISOLATED   failure ', 'input');
  view.set('platform', 'macos', 'change');
  assert.deepEqual(view.visible(), ['recommended']);
  assert.deepEqual(view.visibleFeatured(), ['recommended']);
  assert.equal(view.ids['result-count'].textContent, '1 tool');
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '1 tool');
  assert.equal(view.ids['recommended-region'].hidden, false);
  assert.equal(view.ids['other-empty'].hidden, true);
  assert.equal(view.ids['other-tools'].hidden, false);

  view.set('category', 'authoring', 'change');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 tools');
  assert.equal(view.ids['empty-results'].hidden, false);
  assert.equal(view.ids['recommended-region'].hidden, true);
  assert.equal(view.ids['other-empty'].hidden, true);
  assert.equal(view.ids['other-tools'].hidden, false);
});

test('zero recommendations hide the whole region and omit a recommendation empty message', () => {
  const view = catalog({ zeroRecommendations: true });
  assert.deepEqual(view.visible(), ['classified-alpha', 'classified-beta', 'unclassified']);
  assert.equal(view.ids['recommended-count'].textContent, '0 tools');
  assert.equal(view.ids['other-count'].textContent, '3 tools');
  assert.equal(view.ids['recommended-region'].hidden, true);
  assert.equal(view.ids['other-empty'].hidden, true);
  assert.equal(view.ids['other-tools'].hidden, false);

  view.set('tool-search', 'not-present', 'input');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 tools');
  assert.equal(view.ids['recommended-count'].textContent, '0 tools');
  assert.equal(view.ids['other-count'].textContent, '0 tools');
  assert.equal(view.ids['empty-results'].hidden, false);
  assert.equal(view.ids['other-empty'].hidden, true);
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

test('Other search and filter preserve Name sorting and unique counts without recommendations', () => {
  const view = catalog({ zeroRecommendations: true });
  view.set('tool-search', 'OtHeR', 'input');
  assert.deepEqual(view.visible(), ['unclassified']);
  assert.equal(view.ids['result-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '1 tool');
  assert.equal(view.ids['recommended-count'].textContent, '0 tools');
  assert.equal(view.ids['recommended-region'].hidden, true);
  assert.deepEqual(view.visibleFeatured(), []);
  view.set('category', '__unclassified__', 'change');
  view.set('tool-sort', 'name', 'change');
  assert.equal(view.group('__unclassified__').hidden, true);
  assert.equal(view.nameGrid.hidden, false);
  assert.deepEqual(view.visible(), ['unclassified']);
  view.set('tool-search', 'Unclassified', 'input');
  assert.deepEqual(view.visible(), ['unclassified']);
  view.set('tool-sort', 'category', 'change');
  assert.equal(view.group('__unclassified__').hidden, false);
  assert.equal(view.group('__unclassified__').querySelector('.group-count').textContent, '1 tool');
  view.ids['clear-filters'].dispatch('click');
  assert.equal(view.ids['result-count'].textContent, '3 tools');
});

test('search includes category labels and the displayed tool name', () => {
  const view = catalog();
  view.set('tool-search', 'TEST environments', 'input');
  assert.deepEqual(view.visible(), ['recommended', 'alternative']);
  assert.equal(view.ids['recommended-count'].textContent, '1 tool');
  assert.equal(view.ids['other-count'].textContent, '2 tools');
  view.set('tool-search', 'eCho', 'input');
  assert.deepEqual(view.visible(), ['authoring']);
  assert.equal(view.ids['other-count'].textContent, '1 tool');
});

test('clear resets filters and returns focus to search', () => {
  const view = catalog();
  view.set('tool-sort', 'name', 'change');
  view.set('category', 'testing', 'change');
  view.set('platform', 'windows', 'change');
  view.set('tool-search', 'no-such-term', 'input');
  view.ids['clear-filters'].dispatch('click');
  for (const id of ['tool-search', 'platform', 'category']) assert.equal(view.ids[id].value, '');
  assert.equal(view.ids['tool-sort'].value, 'name');
  assert.deepEqual(view.visible(), ['recommended', 'alternative', 'authoring', 'legacy']);
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  assert.equal(view.ids['tool-search'].focused, true);
  assert.deepEqual(view.nameGrid.children.map(card => card.dataset.tool),
    ['legacy', 'alternative', 'authoring', 'recommended']);
  assert.deepEqual(view.groups.map(group => group.hidden), [true, true, true]);
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
