/* Progressive enhancement only. All content and links work without JavaScript. */
for (const button of document.querySelectorAll('[data-copy]')) {
  button.addEventListener('click', async () => {
    const code = document.getElementById(button.dataset.copy);
    const status = button.closest('.copy-region').querySelector('[role="status"]');
    try {
      await navigator.clipboard.writeText(code.textContent);
      status.textContent = 'Copied. Paste this into your agent or terminal.';
    } catch {
      const range = document.createRange();
      range.selectNodeContents(code);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = 'Text selected. Use your usual copy command.';
    }
  });
}
const search = document.getElementById('tool-search');
if (search) {
  const platform = document.getElementById('platform');
  const category = document.getElementById('category');
  const toolSort = document.getElementById('tool-sort');
  const filters = document.getElementById('catalog-filters');
  const cards = [...document.querySelectorAll('[data-tool]')];
  const recommendedRegion = document.getElementById('recommended-region');
  const featuredCards = recommendedRegion
    ? [...recommendedRegion.querySelectorAll('[data-tool]')] : [];
  const otherTools = document.getElementById('other-tools');
  const allToolCards = otherTools
    ? [...otherTools.querySelectorAll('[data-tool]')] : cards;
  const originalParents = new Map(allToolCards.map(card => [card, card.parentElement]));
  const groups = [...document.querySelectorAll('[data-category-group]')];
  const nameGrid = document.getElementById('other-tools-by-name');
  const count = document.getElementById('result-count');
  const recommendedCount = document.getElementById('recommended-count');
  const otherCount = document.getElementById('other-count');
  const otherEmpty = document.getElementById('other-empty');
  const empty = document.getElementById('empty-results');
  const clearFilters = document.getElementById('clear-filters');
  const plural = total => `${total} ${total === 1 ? 'tool' : 'tools'}`;
  function categoryOf(card) {
    return card.dataset.category || '__unclassified__';
  }
  function nameOf(card) {
    return (card.dataset.name || card.querySelector('h2')?.textContent ||
      card.dataset.tool || '').trim();
  }
  function compareByName(left, right) {
    const byName = nameOf(left).localeCompare(nameOf(right), undefined, { sensitivity: 'base' });
    return byName || String(left.dataset.tool || '').localeCompare(
      String(right.dataset.tool || ''), undefined, { sensitivity: 'base' });
  }
  function applySort() {
    if (!toolSort || !nameGrid) return false;
    const byName = toolSort.value === 'name';
    if (byName) {
      for (const card of [...allToolCards].sort(compareByName)) nameGrid.appendChild(card);
      nameGrid.hidden = false;
    } else {
      for (const card of allToolCards) originalParents.get(card)?.appendChild(card);
      nameGrid.hidden = true;
    }
    return byName;
  }
  function matchesBase(card) {
    const words = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return words.every(word => card.dataset.search.includes(word)) &&
      (!platform.value || card.dataset.platforms.split(' ').includes(platform.value));
  }
  function filter() {
    const nameSorted = applySort();
    const baseMatches = new Map(cards.map(card => [card, matchesBase(card)]));
    const matchesCategory = card => baseMatches.get(card) &&
      (!category || !category.value || categoryOf(card) === category.value);
    const visibleCards = cards.filter(matchesCategory);
    const visibleSet = new Set(visibleCards);
    for (const card of cards) card.hidden = !visibleSet.has(card);

    const visibleRecommended = featuredCards.filter(matchesCategory).length;
    const visibleOther = allToolCards.filter(matchesCategory).length;
    count.textContent = plural(visibleOther);
    if (recommendedCount) recommendedCount.textContent = plural(visibleRecommended);
    if (otherCount) otherCount.textContent = plural(visibleOther);
    if (recommendedRegion) recommendedRegion.hidden = visibleRecommended === 0;

    for (const group of groups) {
      const groupCards = allToolCards.filter(card =>
        categoryOf(card) === group.dataset.categoryGroup);
      const groupVisible = groupCards.filter(card => !card.hidden).length;
      group.hidden = nameSorted || groupVisible === 0;
      const groupCount = group.querySelector('.group-count');
      if (groupCount) groupCount.textContent = plural(groupVisible);
    }
    if (otherTools) otherTools.hidden = false;
    if (nameGrid) nameGrid.hidden = !nameSorted || visibleOther === 0;
    if (empty) empty.hidden = visibleOther !== 0;
    if (otherEmpty) otherEmpty.hidden = visibleOther !== 0 || visibleRecommended === 0;
  }
  search.addEventListener('input', filter);
  platform.addEventListener('change', filter);
  if (category) category.addEventListener('change', filter);
  if (toolSort) toolSort.addEventListener('change', filter);
  clearFilters.addEventListener('click', () => {
    search.value = ''; platform.value = '';
    if (category) category.value = '';
    filter(); search.focus();
  });
  if (filters) filters.hidden = false;
  filter();
}

// GIFs have no pause API. Use a matching still when motion is paused or reduced.
const motionImages = [...document.querySelectorAll('[data-motion-src]')];
const demoVideos = [...document.querySelectorAll('[data-demo-video]')];
if (motionImages.length || demoVideos.length) {
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let paused = preference.matches;
  function setMotion() {
    for (const img of motionImages) {
      img.src = paused ? img.dataset.stillSrc : img.dataset.motionSrc;
    }
    for (const video of demoVideos) {
      if (paused) video.pause();
      else video.play().catch(() => { /* Native controls remain available. */ });
    }
    for (const button of document.querySelectorAll('[data-motion-toggle]')) {
      button.hidden = false;
      button.textContent = paused ? 'Play motion' : 'Pause motion';
      button.setAttribute('aria-pressed', String(paused));
    }
  }
  for (const button of document.querySelectorAll('[data-motion-toggle]')) {
    button.addEventListener('click', () => { paused = !paused; setMotion(); });
  }
  preference.addEventListener('change', event => { paused = event.matches; setMotion(); });
  setMotion();
}
