/* Executes the production script against the DOM contract of the server-rendered pages. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const script = fs.readFileSync(path.join(__dirname, '../theme/site.js'), 'utf8');
const UNCLASSIFIED = '__unclassified__';

function element(dataset = {}) {
  return {
    dataset, value: '', hidden: false, textContent: '', listeners: {}, attributes: {},
    found: {}, ancestors: {}, box: { left: 0, top: 0, width: 0, height: 0 },
    style: { values: {}, setProperty(name, value) { this.values[name] = value; } },
    addEventListener(event, callback) { (this.listeners[event] ||= []).push(callback); },
    dispatch(event, detail = {}) {
      return Promise.all((this.listeners[event] || [])
        .map(callback => callback({ target: this, type: event, ...detail })));
    },
    setAttribute(name, value) { this.attributes[name] = value; },
    toggleAttribute(name, force) {
      if (force) this.attributes[name] = '';
      else delete this.attributes[name];
    },
    getBoundingClientRect() { return this.box; },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
    querySelectorAll(selector) { return [].concat(this.found[selector] || []); },
    closest(selector) { return this.ancestors[selector] || null; },
  };
}

/* Loads the script into a page holding the given elements by id and by selector. */
function page({
  ids = {}, found = {}, reducedMotion = false, narrow = false, clipboard, fetch, ClipboardItem,
} = {}) {
  const view = { active: null, classes: new Set(), selected: null, location: null, timers: new Map() };
  const elements = [...Object.values(ids), ...Object.values(found).flat()];
  for (const node of elements.flatMap(node => [node, ...Object.values(node.found).flat()])) {
    node.focus = () => { view.active = node; };
  }
  const document = {
    documentElement: { classList: { add(name) { view.classes.add(name); } } },
    getElementById(id) { return ids[id] || null; },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
    querySelectorAll(selector) { return [].concat(found[selector] || []); },
    createRange() { return { selectNodeContents(node) { this.node = node; } }; },
  };
  view.preference = { matches: reducedMotion, addEventListener(_, callback) { this.changed = callback; } };
  const media = {
    '(prefers-reduced-motion: reduce)': view.preference,
    '(max-width: 1100px)': { matches: narrow },
  };
  const window = {
    matchMedia(query) {
      assert.ok(Object.hasOwn(media, query), query);
      return media[query];
    },
    getSelection() {
      return {
        removeAllRanges() { view.selected = null; },
        addRange(range) { view.selected = range.node; },
      };
    },
    location: { assign(url) { view.location = url; } },
  };
  if (ClipboardItem) window.ClipboardItem = ClipboardItem;
  const timers = {
    setTimeout(callback, delay) {
      const id = Symbol(delay);
      view.timers.set(id, { callback, delay });
      return id;
    },
    clearTimeout(id) { view.timers.delete(id); },
  };
  view.elapse = () => {
    const due = [...view.timers.values()];
    view.timers.clear();
    for (const { callback } of due) callback();
  };
  vm.runInNewContext(script, { document, window, navigator: { clipboard }, fetch, Blob, ClipboardItem, ...timers });
  return view;
}

function catalog({ registry = true, recommendations = true } = {}) {
  const row = (tool, category, search) => element({ tool, category, search });
  const rows = registry ? [
    row('alternative', 'testing', 'alternative isolated failure linux test environments'),
    row('echo', 'authoring', 'fixture-echo echo create tool macos tool authoring'),
    row('unlisted', UNCLASSIFIED, 'unlisted failure video windows other'),
    row('recommended', 'testing', 'recommended isolated failure linux macos test environments'),
  ] : [
    row('alternative', UNCLASSIFIED, 'alternative isolated failure linux'),
    row('echo', UNCLASSIFIED, 'fixture-echo echo create tool macos'),
    row('unlisted', UNCLASSIFIED, 'unlisted failure video windows'),
    row('recommended', UNCLASSIFIED, 'recommended isolated failure linux macos'),
  ];
  const chips = ['', 'testing', 'authoring', UNCLASSIFIED].map(category => element({ category }));
  chips[0].attributes['aria-pressed'] = 'true';
  for (const chip of chips.slice(1)) chip.attributes['aria-pressed'] = 'false';
  const ids = {
    'tool-search': element(), 'store-search': element(), 'result-count': element(),
    'empty-results': element(),
  };
  ids['store-search'].hidden = true;
  ids['result-count'].textContent = `${rows.length} tools`;
  ids['empty-results'].hidden = true;
  const clear = element();
  ids['empty-results'].found['[data-clear]'] = clear;
  if (registry) {
    ids['category-chips'] = element();
    ids['category-chips'].hidden = true;
    ids['category-chips'].found['[data-category]'] = chips;
    if (recommendations) ids.featured = element();
  }
  const view = page({ ids, found: { '.app-row[data-tool]': rows } });
  return Object.assign(view, {
    ids, rows, chips, clear,
    visible() { return rows.filter(item => !item.hidden).map(item => item.dataset.tool); },
    pressed() {
      return chips.filter(chip => chip.attributes['aria-pressed'] === 'true')
        .map(chip => chip.dataset.category);
    },
    search(value) { ids['tool-search'].value = value; return ids['tool-search'].dispatch('input'); },
    choose(category) {
      return chips.find(chip => chip.dataset.category === category).dispatch('click');
    },
  });
}

test('search and chips appear at load with every row, the count, and Recommended visible', () => {
  const view = catalog();
  assert.equal(view.classes.has('js'), true);
  assert.equal(view.ids['store-search'].hidden, false);
  assert.equal(view.ids['category-chips'].hidden, false);
  assert.deepEqual(view.visible(), ['alternative', 'echo', 'unlisted', 'recommended']);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  assert.deepEqual(view.pressed(), ['']);
  assert.equal(view.ids.featured.hidden, false);
  assert.equal(view.ids['empty-results'].hidden, true);
});

test('every search word must appear in a row, in any case and order', () => {
  const view = catalog();
  view.search('  ISOLATED   failure ');
  assert.deepEqual(view.visible(), ['alternative', 'recommended']);
  assert.equal(view.ids['result-count'].textContent, '2 tools');

  view.search('macos failure');
  assert.deepEqual(view.visible(), ['recommended']);
  assert.equal(view.ids['result-count'].textContent, '1 tool');

  view.search('failure');
  assert.deepEqual(view.visible(), ['alternative', 'unlisted', 'recommended']);
  assert.equal(view.ids['result-count'].textContent, '3 tools');
  assert.deepEqual(view.pressed(), ['']);
});

test('search reaches category labels, manifest names, and displayed names', () => {
  const view = catalog();
  view.search('TEST environments');
  assert.deepEqual(view.visible(), ['alternative', 'recommended']);
  view.search('fixture-echo');
  assert.deepEqual(view.visible(), ['echo']);
  view.search('eCho');
  assert.deepEqual(view.visible(), ['echo']);
  view.search('OtHeR');
  assert.deepEqual(view.visible(), ['unlisted']);
});

test('a chip narrows rows to its category and takes the pressed state', () => {
  const view = catalog();
  view.choose('testing');
  assert.deepEqual(view.visible(), ['alternative', 'recommended']);
  assert.deepEqual(view.pressed(), ['testing']);
  assert.equal(view.ids['result-count'].textContent, '2 tools');
  assert.equal(view.ids['empty-results'].hidden, true);

  view.choose('authoring');
  assert.deepEqual(view.visible(), ['echo']);
  assert.deepEqual(view.pressed(), ['authoring']);
  assert.equal(view.ids['result-count'].textContent, '1 tool');

  view.choose('');
  assert.deepEqual(view.visible(), ['alternative', 'echo', 'unlisted', 'recommended']);
  assert.deepEqual(view.pressed(), ['']);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
});

test('the Other chip keeps unclassified tools discoverable', () => {
  const view = catalog();
  view.choose(UNCLASSIFIED);
  assert.deepEqual(view.visible(), ['unlisted']);
  assert.deepEqual(view.pressed(), [UNCLASSIFIED]);
  view.search('video');
  assert.deepEqual(view.visible(), ['unlisted']);
  view.search('linux');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['empty-results'].hidden, false);
});

test('search and category combine, and each keeps its value when the other changes', () => {
  const view = catalog();
  view.search('failure');
  view.choose('testing');
  assert.deepEqual(view.visible(), ['alternative', 'recommended']);
  assert.equal(view.ids['tool-search'].value, 'failure');

  view.search('macos');
  assert.deepEqual(view.visible(), ['recommended']);
  assert.deepEqual(view.pressed(), ['testing']);

  view.choose('authoring');
  assert.deepEqual(view.visible(), ['echo']);
  assert.equal(view.ids['tool-search'].value, 'macos');
});

test('Recommended steps aside while a search or category is active', () => {
  const view = catalog();
  view.search('failure');
  assert.equal(view.ids.featured.hidden, true);
  view.search('   ');
  assert.equal(view.ids.featured.hidden, false);
  assert.deepEqual(view.visible(), ['alternative', 'echo', 'unlisted', 'recommended']);

  view.choose('testing');
  assert.equal(view.ids.featured.hidden, true);
  view.search('recommended');
  assert.equal(view.ids.featured.hidden, true);
  view.search('');
  assert.equal(view.ids.featured.hidden, true);
  view.choose('');
  assert.equal(view.ids.featured.hidden, false);
});

test('zero matches show the empty state, and clear resets search and category', () => {
  const view = catalog();
  view.choose('authoring');
  view.search('no-such-term');
  assert.deepEqual(view.visible(), []);
  assert.equal(view.ids['result-count'].textContent, '0 tools');
  assert.equal(view.ids['empty-results'].hidden, false);
  assert.equal(view.ids.featured.hidden, true);
  assert.equal(view.active, null);

  view.clear.dispatch('click');
  assert.equal(view.ids['tool-search'].value, '');
  assert.deepEqual(view.pressed(), ['']);
  assert.deepEqual(view.visible(), ['alternative', 'echo', 'unlisted', 'recommended']);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  assert.equal(view.ids['empty-results'].hidden, true);
  assert.equal(view.ids.featured.hidden, false);
  assert.equal(view.active, view.ids['tool-search']);
});

test('a catalog with a registry and no recommendations filters without a Recommended region', () => {
  const view = catalog({ recommendations: false });
  view.choose('testing');
  view.search('macos');
  assert.deepEqual(view.visible(), ['recommended']);
  view.search('windows');
  assert.equal(view.ids['empty-results'].hidden, false);
  view.clear.dispatch('click');
  assert.equal(view.visible().length, 4);
});

test('a catalog without a registry has no chips and remains searchable', () => {
  const view = catalog({ registry: false });
  assert.equal(view.ids['store-search'].hidden, false);
  assert.equal(view.ids['result-count'].textContent, '4 tools');
  view.search('failure linux');
  assert.deepEqual(view.visible(), ['alternative', 'recommended']);
  assert.equal(view.ids['result-count'].textContent, '2 tools');
  view.search('no-such-term');
  assert.equal(view.ids['empty-results'].hidden, false);
  view.clear.dispatch('click');
  assert.equal(view.visible().length, 4);
  assert.equal(view.active, view.ids['tool-search']);
});

test('pages without catalog search, a menu, copy buttons, videos, or an outline remain unaffected', () => {
  for (const narrow of [false, true]) {
    const view = page({ narrow });
    assert.equal(view.classes.has('js'), true);
  }
});

function reader(narrow) {
  const outline = Object.assign(element(), { open: true });
  page({ found: { '.reader-toc': [outline] }, narrow });
  return outline;
}

test('the page outline stays open beside a wide layout and folds above a narrow one', () => {
  assert.equal(reader(false).open, true);
  assert.equal(reader(true).open, false);
});

function copyRegion(clipboard) {
  const button = element({ copy: 'prompt' });
  const region = element();
  const status = element();
  const code = element();
  code.textContent = 'Go to https://example.com/tool and install it.';
  region.found['[role="status"]'] = status;
  button.ancestors['.copy-region'] = region;
  const view = page({ ids: { prompt: code }, found: { '[data-copy]': [button] }, clipboard });
  return Object.assign(view, { button, status, code });
}

test('a copy button writes its prompt to the clipboard and confirms', async () => {
  const written = [];
  const view = copyRegion({ async writeText(text) { written.push(text); } });
  assert.equal(view.status.textContent, '');
  await view.button.dispatch('click');
  assert.deepEqual(written, ['Go to https://example.com/tool and install it.']);
  assert.equal(view.status.textContent, 'Copied. Paste it into your agent.');
  assert.equal(view.selected, null);
});

test('a copy button selects the prompt when the clipboard is unavailable', async () => {
  const view = copyRegion({ async writeText() { throw new Error('denied'); } });
  await view.button.dispatch('click');
  assert.equal(view.selected, view.code);
  assert.equal(view.status.textContent, 'Text selected. Use your usual copy command.');
});

const MARKDOWN = '# Fixture post\n\nFixture body.\n';
const COPY = 'https://example.com/blog/fixture/index.md';

class ClipboardItem {
  constructor(data) { this.data = data; }
}

/* A clipboard that takes items, as a browser with ClipboardItem does, or only text. */
function clipboard(items, log, refuse) {
  const store = text => {
    if (refuse) throw new Error('denied');
    log.written.push(text);
  };
  if (!items) return { async writeText(text) { log.offered += 1; store(text); } };
  return {
    async write([item]) {
      log.offered += 1;
      const blob = await item.data['text/plain'];
      assert.equal(blob.type, 'text/plain');
      store(await blob.text());
    },
  };
}

function markdownLink({ items = false, refuse = false, respond } = {}) {
  const link = Object.assign(element(), { href: COPY });
  const region = element();
  const status = element();
  const requested = [];
  const log = { offered: 0, written: [] };
  region.found['[role="status"]'] = status;
  link.ancestors['.copy-region'] = region;
  const view = page({
    found: { '[data-copy-markdown]': [link] },
    clipboard: clipboard(items, log, refuse),
    ClipboardItem: items ? ClipboardItem : undefined,
    fetch(url) {
      requested.push(url);
      return respond ? respond() : Promise.resolve({ ok: true, text: async () => MARKDOWN });
    },
  });
  return Object.assign(view, {
    link, status, requested, log, prevented: false,
    click() { return link.dispatch('click', { preventDefault() { view.prevented = true; } }); },
  });
}

for (const items of [true, false]) {
  const kind = items ? 'clipboard items' : 'clipboard text only';

  test(`a Copy as Markdown link copies the page's Markdown and confirms, with ${kind}`, async () => {
    const view = markdownLink({ items });
    assert.deepEqual([view.requested, view.status.textContent], [[], '']);
    await view.click();
    assert.equal(view.prevented, true);
    assert.deepEqual(view.requested, [COPY]);
    assert.deepEqual(view.log, { offered: 1, written: [MARKDOWN] });
    assert.equal(view.status.textContent, 'Copied as Markdown.');
    assert.deepEqual(view.link.attributes, { 'data-copied': '' });
    assert.equal(view.location, null);
    await view.click();
    assert.deepEqual([...view.timers.values()].map(timer => timer.delay), [1600]);
    view.elapse();
    assert.deepEqual([view.link.attributes, view.status.textContent], [{}, '']);
  });

  const failures = {
    'the request fails': { respond: () => Promise.reject(new Error('offline')) },
    'the response is an error': {
      respond: async () => ({ ok: false, statusText: 'Not Found', text: async () => 'Not Found' }),
    },
    'the clipboard refuses': { refuse: true },
  };
  for (const [reason, options] of Object.entries(failures)) {
    test(`a Copy as Markdown link opens the Markdown when ${reason}, with ${kind}`, async () => {
      const view = markdownLink({ items, ...options });
      await view.click();
      assert.equal(view.prevented, true);
      assert.deepEqual(view.requested, [COPY]);
      assert.deepEqual(view.log.written, []);
      assert.deepEqual([view.link.attributes, view.status.textContent, view.timers.size], [{}, '', 0]);
      assert.equal(view.location, COPY);
    });
  }
}

test('clipboard items are offered inside the click, before the Markdown arrives', async () => {
  let arrive;
  const view = markdownLink({ items: true, respond: () => new Promise(resolve => { arrive = resolve; }) });
  const click = view.click();
  assert.deepEqual(view.log, { offered: 1, written: [] });
  assert.equal(view.status.textContent, '');
  arrive({ ok: true, text: async () => MARKDOWN });
  await click;
  assert.deepEqual(view.log, { offered: 1, written: [MARKDOWN] });
  assert.equal(view.status.textContent, 'Copied as Markdown.');
  assert.equal(view.location, null);
});

function menuPage() {
  const menu = element();
  const toggle = element();
  const close = element();
  toggle.attributes['aria-expanded'] = 'false';
  toggle.box = { left: 300, top: 20, width: 48, height: 40 };
  menu.found['[data-menu-close]'] = close;
  const view = page({ ids: { menu }, found: { '[data-menu-toggle]': [toggle] } });
  return Object.assign(view, {
    menu, toggle, close,
    open() { return 'data-open' in menu.attributes; },
  });
}

test('the menu opens from its toggle and closes from its close button', () => {
  const view = menuPage();
  assert.equal(view.open(), false);
  assert.equal(view.toggle.attributes['aria-expanded'], 'false');

  view.toggle.dispatch('click');
  assert.equal(view.open(), true);
  assert.equal(view.toggle.attributes['aria-expanded'], 'true');
  assert.equal(view.active, view.close);
  assert.deepEqual(view.menu.style.values, { '--menu-x': '324px', '--menu-y': '40px' });

  view.close.dispatch('click');
  assert.equal(view.open(), false);
  assert.equal(view.toggle.attributes['aria-expanded'], 'false');
  assert.equal(view.active, view.toggle);
});

test('Escape and a link inside the menu close it; other keys and clicks do not', () => {
  const view = menuPage();
  const link = element();
  link.ancestors.a = link;

  view.toggle.dispatch('click');
  view.menu.dispatch('keydown', { key: 'Tab' });
  view.menu.dispatch('click', { target: element() });
  assert.equal(view.open(), true);

  view.menu.dispatch('keydown', { key: 'Escape' });
  assert.equal(view.open(), false);
  assert.equal(view.toggle.attributes['aria-expanded'], 'false');
  assert.equal(view.active, view.toggle);

  view.toggle.dispatch('click');
  view.menu.dispatch('click', { target: link });
  assert.equal(view.open(), false);
  assert.equal(view.toggle.attributes['aria-expanded'], 'false');
});

function demo({ reducedMotion = false, play = () => Promise.resolve() } = {}) {
  const video = () => Object.assign(element(), {
    playing: null,
    play() { this.playing = true; return play(); },
    pause() { this.playing = false; },
  });
  const toggle = () => {
    const button = element();
    button.hidden = true;
    button.textContent = 'Pause motion';
    button.attributes['aria-pressed'] = 'false';
    return button;
  };
  const videos = [video(), video()];
  const toggles = [toggle(), toggle()];
  const view = page({
    found: { '[data-demo-video]': videos, '[data-motion-toggle]': toggles }, reducedMotion,
  });
  return Object.assign(view, {
    videos, toggles,
    playing() { return videos.map(item => item.playing); },
    controls() {
      return toggles.map(button => [button.hidden, button.textContent, button.attributes['aria-pressed']]);
    },
  });
}

test('demo videos play at load and every motion toggle pauses and resumes all of them', () => {
  const view = demo();
  assert.deepEqual(view.playing(), [true, true]);
  assert.deepEqual(view.controls(), [[false, 'Pause motion', 'false'], [false, 'Pause motion', 'false']]);

  view.toggles[1].dispatch('click');
  assert.deepEqual(view.playing(), [false, false]);
  assert.deepEqual(view.controls(), [[false, 'Play motion', 'true'], [false, 'Play motion', 'true']]);

  view.toggles[0].dispatch('click');
  assert.deepEqual(view.playing(), [true, true]);
  assert.deepEqual(view.controls(), [[false, 'Pause motion', 'false'], [false, 'Pause motion', 'false']]);
});

test('demo videos follow the reduced-motion preference at load and when it changes', () => {
  const view = demo({ reducedMotion: true });
  assert.deepEqual(view.playing(), [false, false]);
  assert.deepEqual(view.controls(), [[false, 'Play motion', 'true'], [false, 'Play motion', 'true']]);

  view.preference.changed({ matches: false });
  assert.deepEqual(view.playing(), [true, true]);
  assert.deepEqual(view.controls(), [[false, 'Pause motion', 'false'], [false, 'Pause motion', 'false']]);

  view.preference.changed({ matches: true });
  assert.deepEqual(view.playing(), [false, false]);
});

test('a blocked autoplay leaves the page working', async () => {
  const view = demo({ play: () => Promise.reject(new Error('blocked')) });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(view.controls(), [[false, 'Pause motion', 'false'], [false, 'Pause motion', 'false']]);
  view.toggles[0].dispatch('click');
  assert.deepEqual(view.playing(), [false, false]);
});
