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
  const recommendedOnly = document.getElementById('recommended-only');
  const recommendedFilter = document.getElementById('recommended-filter');
  const cards = [...document.querySelectorAll('[data-tool]')];
  const count = document.getElementById('result-count');
  const empty = document.getElementById('empty-results');
  const emptyTitle = document.getElementById('empty-title');
  const emptyHint = document.getElementById('empty-hint');
  const showAllTools = document.getElementById('show-all-tools');
  const defaultEmptyHint = emptyHint ? emptyHint.textContent : '';
  const recommendedCount = cards.filter(card => card.dataset.recommended === 'true').length;
  function filter() {
    const words = search.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let visible = 0;
    for (const card of cards) {
      const matches = words.every(word => card.dataset.search.includes(word)) &&
        (!platform.value || card.dataset.platforms.split(' ').includes(platform.value)) &&
        (!category || !category.value || (category.value === '__unclassified__'
          ? !card.dataset.category : card.dataset.category === category.value)) &&
        (!recommendedOnly || !recommendedOnly.checked || card.dataset.recommended === 'true');
      card.hidden = !matches;
      if (matches) visible++;
    }
    count.textContent = `${visible} of ${cards.length} tools`;
    empty.hidden = visible !== 0;
    const recommendedOnlyActive = recommendedOnly && recommendedOnly.checked;
    if (emptyTitle && emptyHint) {
      if (recommendedOnlyActive) {
        emptyTitle.textContent = recommendedCount === 0
          ? 'No tools are currently shown as Recommended.'
          : 'No Recommended tools match these filters.';
        emptyHint.textContent = recommendedCount === 0
          ? 'Turn off “Recommended only” to see all listed tools, including alternatives and unclassified entries, or clear all filters.'
          : 'Try a broader search or category, or include tools without a Recommended designation.';
      } else {
        emptyTitle.textContent = 'No matching tools.';
        emptyHint.textContent = defaultEmptyHint;
      }
    }
    if (showAllTools) showAllTools.hidden = !recommendedOnlyActive;
  }
  search.addEventListener('input', filter);
  platform.addEventListener('change', filter);
  if (category) category.addEventListener('change', filter);
  if (recommendedOnly) recommendedOnly.addEventListener('change', filter);
  if (showAllTools && recommendedOnly) {
    showAllTools.addEventListener('click', () => {
      recommendedOnly.checked = false;
      filter();
      recommendedOnly.focus();
    });
  }
  document.getElementById('clear-filters').addEventListener('click', () => {
    search.value = ''; platform.value = '';
    if (category) category.value = '';
    if (recommendedOnly) recommendedOnly.checked = false;
    filter(); search.focus();
  });
  filter();
  if (recommendedFilter) recommendedFilter.hidden = false;
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
