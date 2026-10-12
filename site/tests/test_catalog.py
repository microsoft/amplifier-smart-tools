"""Deterministic catalog validation, renderer, and portable-theme integration."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE/'theme'))
import build
import catalog_metadata as metadata

REPO = 'https://github.com/example/fixture-tool.git'
COMMIT = 'a' * 40
CATEGORY = {'id': 'testing', 'label': 'Test environments',
          'scope': 'Create isolated test environments.'}
POINTER = {'repository': REPO}
PROVENANCE = {
    'source': {'repository': REPO, 'ref': 'main', 'path': '.', 'commit': COMMIT},
    'original_manifest_path': 'src/fixture/SMART_TOOL.md',
    'last_success': '2026-01-01T12:00:00Z',
}
LISTING = {'category': 'testing', 'recommended': True,
           'reviewed_source': {'repository': REPO, 'path': '.', 'commit': COMMIT}}
MANIFEST = '''---
name: fixture-tool
description: >
  Reproduce software failures in isolated environments.
platforms: [linux, macos]
use_cases: [Reproduce failures]
---
# Usage
'''
ARGS = SimpleNamespace(local=False, family_owner=None)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def entry(root, slug, listing=None, snapshot=True):
    directory = root/'tools'/slug
    write_json(directory/'source.json', POINTER)
    if snapshot:
        (directory/'SMART_TOOL.md').write_text(MANIFEST, encoding='utf-8')
        write_json(directory/'provenance.json', PROVENANCE)
    if listing is not None:
        write_json(directory/'listing.json', listing)
    return directory


def registry(root, categories=None):
    write_json(root/'categories.json', {'categories': categories if categories is not None else [CATEGORY]})


def render(root):
    return build.catalog({}, ARGS, root)


class Cards(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.cards = []
        self.card = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'data-tool' in attrs:
            self.card = dict(attrs, text='', badges=[], ids=[])
            self.cards.append(self.card)
        elif self.card is not None:
            if attrs.get('id'):
                self.card['ids'].append(attrs['id'])
            if tag in ('span', 'summary'):
                classes = (attrs.get('class') or '').split()
                if 'recommendation' in classes:
                    self.card['badges'].append(classes)

    def handle_endtag(self, tag):
        if tag == 'article':
            self.card = None

    def handle_data(self, data):
        if self.card is not None:
            self.card['text'] += data


class CatalogLayout(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.section_stack = []
        self.cards = []
        self.sections = {}
        self.category_tiles = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section':
            self.section_stack.append(attrs.get('id'))
            if attrs.get('id'):
                self.sections[attrs['id']] = attrs
        if tag == 'article' and 'data-tool' in attrs:
            parent = next((identity for identity in reversed(self.section_stack) if identity), None)
            self.cards.append((attrs, parent))
        if tag == 'button' and 'data-category-filter' in attrs:
            self.category_tiles.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'section' and self.section_stack:
            self.section_stack.pop()


def test_legacy_has_no_category_ui_and_preserves_slug_order(tmp_path):
    entry(tmp_path, 'zulu')
    entry(tmp_path, 'alpha', snapshot=False)
    assert metadata.load_catalog_metadata(tmp_path) == (None, {})
    result = render(tmp_path)
    # Captured from the public renderer at 990d2437756e5c4be338cbed30c7a87885516d2c,
    # with this same fixture: optional metadata must not alter legacy HTML.
    assert hashlib.sha256(result.encode()).hexdigest() == 'fd4e43b3981064af78fb7f2fa361f572934a2a2c1d4afa2fe3f8c7255159160e'
    cards = Cards(result).cards
    assert [c['data-tool'] for c in cards] == ['alpha', 'zulu']
    assert all('data-category' not in c and 'hidden' not in c for c in cards)
    assert 'id="category"' not in result
    assert 'catalog-category' not in result
    assert 'Recommended' not in result
    assert '2 tools' in result
    assert 'Snapshot refreshed: 2026-01-01T12:00:00Z' in result
    assert 'All tools are listed below' in result


def test_recommendations_first_categories_and_unclassified_remain(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'alpha')
    entry(tmp_path, 'alternative', {'category': 'testing'})
    entry(tmp_path, 'zulu', LISTING)
    result = render(tmp_path)
    layout = CatalogLayout(result)
    cards = Cards(result).cards
    assert [card['data-tool'] for card in cards] == ['zulu', 'zulu', 'alternative', 'alpha']
    assert [card['data-category'] for card in cards] == ['testing', 'testing', 'testing', '']
    assert [card['data-recommended'] for card in cards] == ['true', 'true', 'false', 'false']
    assert [card['data-name'] for card in cards] == ['Zulu', 'Zulu', 'Alternative', 'Alpha']
    assert all('hidden' not in card for card in cards)
    by_slug = {card['data-tool']: ' '.join(card['text'].split()) for card in cards}
    assert 'Category: Test environments' in by_slug['zulu']
    assert 'Recommended' in by_slug['zulu']
    assert 'Category: Test environments' in by_slug['alternative']
    assert 'Category: Other' in by_slug['alpha']
    assert 'Not currently recommended' not in result

    placements = [(attrs['data-tool'], region) for attrs, region in layout.cards]
    assert placements == [
        ('zulu', 'recommended-region'),
        ('zulu', 'category-group-testing'),
        ('alternative', 'category-group-testing'),
        ('alpha', 'category-group-unclassified'),
    ]
    assert cards[0]['badges'] == []
    assert cards[1]['badges'] == [['recommendation', 'recommended']]
    assert all(not card['ids'] for card in cards)
    assert [card['data-tool'] for card in cards].count('zulu') == 2
    assert 'recommended-region' in layout.sections
    assert 'other-tools' in layout.sections
    assert 'category-group-testing' in layout.sections
    assert 'category-group-unclassified' in layout.sections
    assert result.index('id="catalog-filters"') < result.index('id="recommended-region"')
    assert result.index('id="catalog-filters"') < result.index('id="other-tools"')
    assert result.index('id="recommended-region"') < result.index('id="other-tools"')
    canonical_header = (
        '<section class="hero catalog-hero"><p class="eyebrow">Amplifier Smart Tools / Catalog</p>'
        '<h1>Find a tool.<br>Make something happen.</h1>'
        '<p class="lede">Domain expertise you can put to work. Explore the tools, inspect their '
        'requirements, and bring the right one to your agent.</p><div class="actions">'
        f'{build.link("#discovery", "Get the skill", "button primary")}'
        f'{build.link(build.repo_url("catalog") + "#contributing", "Add a tool", "text-link")}'
        '</div></section>')
    assert canonical_header in result
    assert 'Browse by category' not in result
    assert 'category-navigation' not in result
    assert '<p class="catalog-count" id="result-count" role="status">3 tools</p>' in result
    assert '<span class="catalog-count" id="recommended-count">1 tool</span>' in result
    assert '<span class="catalog-count" id="other-count">3 tools</span>' in result
    assert 'id="category-group-count-testing">2 tools</span>' in result
    assert 'id="category-group-count-unclassified">1 tool</span>' in result
    assert '<select id="category">' in result
    assert '<option value="">All categories</option>' in result
    assert '<option value="testing">Test environments</option>' in result
    assert '<option value="__unclassified__">Other</option>' in result
    for removed in ('category-scope', 'aria-describedby', 'data-scope',
                    'Create isolated test environments.', 'filter-scope',
                    'Other tools', 'Other tool order', 'recommendation-context',
                    'recommendation-empty', 'recommendation-guide',
                    'recommendation-disclosure', 'What does Recommended mean?',
                    'No Recommended tools match these filters',
                    'Not currently recommended'):
        assert removed not in result
    assert 'recommended-only' not in result
    assert 'show-all-tools' not in result
    assert 'id="other-tools-heading">All tools</h2>' in result
    assert ('<div class="sort-field"><label for="tool-sort">Sort by</label>'
            '<select id="tool-sort"><option value="category">Category</option>'
            '<option value="name">Name</option></select></div>') in result
    assert result.count('id="clear-filters"') == 1
    assert '<div class="filters" id="catalog-filters" hidden>' in result
    assert '<div class="catalog-grid" id="other-tools-by-name" hidden></div>' in result
    assert not layout.category_tiles
    assert result.count('<span class="recommendation recommended">Recommended</span>') == 1
    assert '<details class="recommendation-disclosure">' not in result
    assert '<details class="recommendation-guide">' not in result
    assert result.count('<summary>Full description and source</summary>') == 4
    assert result.count(f'Source commit: <code>{COMMIT}</code>') == 4
    assert result.count(f'<code>{COMMIT}</code>') == 4
    assert result.count(PROVENANCE['last_success']) == 4

    css = (SITE / 'theme' / 'style.css').read_text(encoding='utf-8')
    assert ('.catalog-hero h1 {\n'
            '  font-size: clamp(50px,6vw,80px);\n'
            '}') in css
    assert 'font-size: clamp(34px,4vw,48px)' not in css
    assert ('#catalog-filters {\n'
            '  grid-template-columns: minmax(190px,2fr) repeat(3,minmax(120px,1fr)) auto;') in css
    assert '#catalog-filters select {\n  min-width: 0;\n}' in css
    assert ('.filters input,.filters select {\n'
            '  display: block;\n'
            '  width: 100%;\n'
            '  margin-top: 8px;\n'
            '  background: transparent;\n'
            '  border: 1px solid #9a9e90;\n'
            '  border-radius: 0;\n'
            '  padding: 12px;\n'
            '  min-height: 48px;') in css
    phone_styles = css.rsplit('@media(max-width:620px) {', 1)[1]
    assert 'grid-template-columns: repeat(2,minmax(0,1fr));' in phone_styles
    assert '#catalog-filters .search-field {\n    grid-column: 1 / -1;' in phone_styles
    assert 'grid-column: 2;\n    justify-self: end;\n    min-height: 44px;' in phone_styles


def test_zero_recommendations_keep_classified_and_unclassified_tools_visible(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'classified-alpha', {'category': 'testing', 'recommended': False})
    entry(tmp_path, 'classified-beta', {'category': 'testing', 'recommended': False})
    entry(tmp_path, 'unclassified')
    result = render(tmp_path)
    layout = CatalogLayout(result)
    cards = Cards(result).cards
    assert [card['data-tool'] for card in cards] == [
        'classified-alpha', 'classified-beta', 'unclassified']
    assert [card['data-category'] for card in cards] == ['testing', 'testing', '']
    assert [card['data-recommended'] for card in cards] == ['false', 'false', 'false']
    assert all('hidden' not in card for card in cards)
    assert result.count('class="recommendation recommended"') == 0
    assert all('Category: Test environments' in card['text'] for card in cards[:2])
    assert 'Category: Other' in cards[2]['text']
    assert 'Not currently recommended' not in result
    assert {attrs['data-tool']: region for attrs, region in layout.cards} == {
        'classified-alpha': 'category-group-testing',
        'classified-beta': 'category-group-testing',
        'unclassified': 'category-group-unclassified',
    }
    assert 'id="recommended-heading">Recommended</h2>' in result
    assert 'id="recommended-count">0 tools</span>' in result
    assert 'id="recommended-empty"' not in result
    assert 'id="recommended-region" aria-labelledby="recommended-heading" hidden>' in result
    assert 'id="other-tools-heading">All tools</h2>' in result
    assert 'id="other-count">3 tools</span>' in result
    assert 'id="category-group-count-testing">2 tools</span>' in result
    assert 'id="category-group-count-unclassified">1 tool</span>' in result
    assert 'recommended-only' not in result
    assert 'show-all-tools' not in result
    assert '<button id="clear-filters" class="button clear-filters" type="button">Clear filters</button>' in result
    assert all('hidden' not in card for card in Cards(result).cards)


def test_two_categories_can_each_have_a_recommendation(tmp_path):
    second = dict(CATEGORY, id='authoring', label='Tool authoring')
    registry(tmp_path, [CATEGORY, second])
    entry(tmp_path, 'zulu', LISTING)
    entry(tmp_path, 'alpha', dict(LISTING, category='authoring'))
    result = render(tmp_path)
    assert result.count('<span class="recommendation recommended">Recommended</span>') == 2
    assert [c['data-tool'] for c in Cards(result).cards] == ['alpha', 'zulu', 'zulu', 'alpha']
    assert result.count('<summary>Full description and source</summary>') == 4
    assert result.count(f'Source commit: <code>{COMMIT}</code>') == 4
    assert '<details class="recommendation-disclosure">' not in result
    assert 'What does Recommended mean?' not in result


@pytest.mark.parametrize('target,field,value', [
    ('pointer', 'repository', 'https://github.com/example/other.git'),
    ('pointer', 'path', 'distribution'),
    ('pointer', 'ref', 'next'),
    ('provenance', 'repository', 'https://github.com/example/other.git'),
    ('provenance', 'path', 'distribution'),
    ('provenance', 'ref', 'next'),
    ('provenance', 'commit', 'b' * 40),
    ('reviewed', 'repository', 'https://github.com/example/other.git'),
    ('reviewed', 'path', 'distribution'),
    ('reviewed', 'commit', 'b' * 40),
])
def test_every_identity_mismatch_loses_preference(tmp_path, target, field, value):
    registry(tmp_path)
    directory = entry(tmp_path, 'zulu', LISTING)
    entry(tmp_path, 'alpha')
    pointer, prov, listing = copy.deepcopy((POINTER, PROVENANCE, LISTING))
    if target == 'pointer':
        pointer[field] = value
    elif target == 'provenance':
        prov['source'][field] = value
    else:
        listing['reviewed_source'][field] = value
    write_json(directory/'source.json', pointer)
    write_json(directory/'provenance.json', prov)
    write_json(directory/'listing.json', listing)
    result = render(tmp_path)
    assert 'Recommendation needs review' in result
    assert 'class="recommendation recommended"' not in result
    assert [c['data-tool'] for c in Cards(result).cards] == ['zulu', 'alpha']
    assert Cards(result).cards[0]['data-category'] == 'testing'
    assert 'Category: Test environments' in Cards(result).cards[0]['text']
    assert 'Recommendation needs review' in Cards(result).cards[0]['text']
    assert 'Not currently recommended' not in Cards(result).cards[0]['text']
    assert 'Category: Other' in Cards(result).cards[1]['text']
    assert 'Not currently recommended' not in Cards(result).cards[1]['text']


@pytest.mark.parametrize('missing', ['SMART_TOOL.md', 'provenance.json', 'both'])
def test_missing_snapshot_needs_review(tmp_path, missing):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    if missing in ('SMART_TOOL.md', 'both'):
        (directory/'SMART_TOOL.md').unlink()
    if missing in ('provenance.json', 'both'):
        (directory/'provenance.json').unlink()
    assert 'Recommendation needs review' in render(tmp_path)


def test_defaults_and_full_commit_identity():
    assert metadata.validate_pointer(POINTER) == dict(POINTER, ref='main', path='.')
    assert metadata.recommendation_state(POINTER, PROVENANCE, LISTING) == 'recommended'
    assert metadata.recommendation_state(POINTER, {}, LISTING) == 'needs-review'
    assert metadata.recommendation_state({}, {}, None) == 'ordinary'


@pytest.mark.parametrize('length', [40, 64])
@pytest.mark.parametrize('matches', [True, False])
def test_full_commit_pin_must_match_snapshot_commit(tmp_path, length, matches):
    registry(tmp_path)
    directory = entry(tmp_path, 'zulu', LISTING)
    entry(tmp_path, 'alpha')
    pointer, prov, listing = copy.deepcopy((POINTER, PROVENANCE, LISTING))
    pinned = 'a' * length
    recorded = pinned if matches else 'b' * length
    pointer['ref'] = prov['source']['ref'] = pinned
    prov['source']['commit'] = listing['reviewed_source']['commit'] = recorded
    expected = 'recommended' if matches else 'needs-review'
    assert metadata.recommendation_state(pointer, prov, listing) == expected
    write_json(directory/'source.json', pointer)
    write_json(directory/'provenance.json', prov)
    write_json(directory/'listing.json', listing)
    result = render(tmp_path)
    assert ('class="recommendation recommended"' in result) is matches
    assert ('Recommendation needs review' in result) is not matches
    assert [c['data-tool'] for c in Cards(result).cards] == (
        ['zulu', 'zulu', 'alpha'] if matches else ['zulu', 'alpha'])
    placements = [(attrs['data-tool'], region) for attrs, region in CatalogLayout(result).cards]
    assert placements == (
        [('zulu', 'recommended-region'), ('zulu', 'category-group-testing'),
         ('alpha', 'category-group-unclassified')]
        if matches else
        [('zulu', 'category-group-testing'), ('alpha', 'category-group-unclassified')])
    assert next(c for c in Cards(result).cards if c['data-tool'] == 'zulu')['data-category'] == 'testing'


def test_duplicate_designation_even_when_needing_review(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'one', LISTING, snapshot=False)
    entry(tmp_path, 'two', LISTING)
    with pytest.raises(ValueError, match='one recommendation'):
        render(tmp_path)


@pytest.mark.parametrize('data', [
    [], {}, {'categories': None}, {'categories': {}, 'unknown': True},
    {'categories': [dict(CATEGORY, extra=True)]},
    {'categories': [dict(CATEGORY, id='Bad ID')]},
    {'categories': [dict(CATEGORY, label=' ')]},
    {'categories': [dict(CATEGORY, scope=1)]},
    {'categories': [dict(CATEGORY, label='x\ninjected')]},
    {'categories': [CATEGORY, CATEGORY]},
])
def test_invalid_registry(data):
    with pytest.raises(ValueError):
        metadata.validate_categories(data)


def test_unreleased_domain_metadata_has_no_compatibility_alias(tmp_path):
    write_json(tmp_path/'domains.json', {'domains': [CATEGORY]})
    entry(tmp_path, 'tool', {'domain': 'testing', 'recommended': False})
    with pytest.raises(ValueError, match='categories.json'):
        render(tmp_path)


@pytest.mark.parametrize('data', [
    None, [], {}, {'recommended': False},
    {'category': 'unknown'},
    {'category': 'testing', 'recommended': 'true'},
    {'category': 'testing', 'recommended': 1},
    {'category': 'testing', 'recommended': 0},
    {'category': 'testing', 'recommended': None},
    {'category': 'testing', 'recommended': True},
    dict(LISTING, extra=True),
    dict(LISTING, recommended=False),
    {'category': 'testing', 'reviewed_source': LISTING['reviewed_source']},
    dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], ref='main')),
    dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], commit='a'*39)),
    dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], commit='a'*41)),
    dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], path='../outside')),
    dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], repository='https://token@github.com/example/tool')),
])
def test_invalid_listing(data):
    with pytest.raises(ValueError):
        metadata.validate_listing(data, {'testing': CATEGORY})


@pytest.mark.parametrize('flag', [None, False, True])
def test_listing_normalizes_a_copy_without_mutating_input(flag):
    data = copy.deepcopy(LISTING) if flag is True else {'category': 'testing'}
    if flag is False:
        data['recommended'] = False
    before = copy.deepcopy(data)
    normalized = metadata.validate_listing(data, {'testing': CATEGORY})
    assert normalized == dict(before, recommended=flag is True)
    assert normalized is not data
    assert data == before
    if flag is not True:
        assert metadata.recommendation_state(POINTER, PROVENANCE, data) == 'ordinary'


def test_omitted_flag_does_not_occupy_slot_or_rewrite_files(tmp_path):
    registry(tmp_path)
    directory = entry(tmp_path, 'ordinary', {'category': 'testing'})
    entry(tmp_path, 'explicit-false', {'category': 'testing', 'recommended': False})
    entry(tmp_path, 'selected', LISTING)
    paths = [tmp_path/'categories.json', *directory.iterdir()]
    before = {path: path.read_bytes() for path in paths}
    _, listings = metadata.load_catalog_metadata(tmp_path)
    assert listings['ordinary'] == {'category': 'testing', 'recommended': False}
    assert sum(listing['recommended'] for listing in listings.values()) == 1
    render(tmp_path)
    assert all(path.read_bytes() == raw for path, raw in before.items())


@pytest.mark.parametrize('snapshot', [False, True])
def test_source_only_entries_render_searchable_other_without_badges(tmp_path, snapshot):
    registry(tmp_path)
    directory = entry(tmp_path, 'source-only-fixture', snapshot=snapshot)
    before = {path: path.read_bytes() for path in directory.iterdir()}
    result = render(tmp_path)
    cards = Cards(result).cards
    assert len(cards) == 1
    card = cards[0]
    assert card['data-tool'] == 'source-only-fixture'
    assert card['data-category'] == ''
    assert card['data-recommended'] == 'false'
    assert card['data-name'] == 'Source Only Fixture'
    assert 'other' in card['data-search']
    assert 'source only fixture' in card['data-search']
    assert 'Category: Other' in card['text']
    assert card['badges'] == []
    assert 'hidden' not in card
    layout = CatalogLayout(result)
    assert layout.cards[0][1] == 'category-group-unclassified'
    assert 'hidden' not in layout.sections['category-group-unclassified']
    assert 'hidden' in layout.sections['recommended-region']
    assert '<option value="__unclassified__">Other</option>' in result
    assert '<h3 id="category-heading-unclassified"><span>Other</span>' in result
    assert 'id="category-group-count-unclassified">1 tool</span>' in result
    assert result.count('id="catalog-filters"') == 1
    assert 'Not yet classified' not in result
    assert ('No manifest snapshot is available yet.' in card['text']) is not snapshot
    assert metadata.load_catalog_metadata(tmp_path) == ({'testing': CATEGORY}, {})
    assert not (directory/'listing.json').exists()
    assert all(path.read_bytes() == raw for path, raw in before.items())


def test_unknown_category_error_has_relative_path_field_value_and_choices(tmp_path):
    registry(tmp_path, [CATEGORY, dict(CATEGORY, id='authoring')])
    entry(tmp_path, 'tool', {'category': 'unknown'})
    with pytest.raises(ValueError) as error:
        metadata.load_catalog_metadata(tmp_path)
    assert str(error.value) == (
        "tools/tool/listing.json: category: Unknown category 'unknown'; "
        "known ids: ['authoring', 'testing']")
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize('data', [
    {'categories': None},
    {'categories': [dict(CATEGORY, label=' ')]},
])
def test_registry_errors_name_relative_file(tmp_path, data):
    write_json(tmp_path/'categories.json', data)
    with pytest.raises(ValueError) as error:
        metadata.load_catalog_metadata(tmp_path)
    assert str(error.value).startswith('categories.json: ')
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize('field', ['category', 'repository'])
def test_listing_errors_never_echo_credential_values(tmp_path, field):
    registry(tmp_path)
    credential_url = 'https://fixture-user:fixture-secret@github.com/example/tool'
    listing = copy.deepcopy(LISTING)
    if field == 'category':
        listing[field] = credential_url
    else:
        listing['reviewed_source'][field] = credential_url
    entry(tmp_path, 'tool', listing)
    with pytest.raises(ValueError) as error:
        metadata.load_catalog_metadata(tmp_path)
    assert str(error.value).startswith('tools/tool/listing.json: ')
    for value in (credential_url, 'fixture-user', 'fixture-secret'):
        assert value not in str(error.value)


def test_empty_registry_is_valid_and_shows_unclassified(tmp_path):
    registry(tmp_path, [])
    entry(tmp_path, 'tool')
    result = render(tmp_path)
    assert 'Category: Other' in result
    assert 'Not currently recommended' not in result


def test_listings_without_registry_fail(tmp_path):
    entry(tmp_path, 'tool', LISTING)
    with pytest.raises(ValueError, match='categories.json'):
        render(tmp_path)


def test_orphan_listing_fails(tmp_path):
    registry(tmp_path)
    write_json(tmp_path/'tools'/'orphan'/'listing.json', LISTING)
    with pytest.raises(ValueError, match='source pointer'):
        render(tmp_path)


@pytest.mark.parametrize('raw', [
    '{"categories":[],"categories":[]}',
    '{"categories":[{"id":"testing","id":"other","label":"l","scope":"s"}]}',
    '{"recommended":true,"reviewed_source":{"commit":"a","commit":"b"}}',
    '{"recommended":NaN}', '{"recommended":Infinity}', '{"broken":',
])
def test_duplicate_json_keys_and_invalid_json_fail(tmp_path, raw):
    path = tmp_path/'metadata.json'
    path.write_text(raw)
    with pytest.raises(ValueError):
        metadata.read_json(path, tmp_path)


@pytest.mark.parametrize('path', ['', '/absolute', '../outside', 'a/../b',
                                   './a', 'a//b', 'a/', 'a\\b', 'a%2fb',
                                   'https://host/path', 'a?query', 'a#fragment',
                                   'a\x00b', False])
def test_unsafe_relative_paths(path):
    with pytest.raises(ValueError):
        metadata.relative_path(path)


@pytest.mark.parametrize('url', [
    'http://github.com/example/tool', 'https://user:secret@github.com/example/tool',
    'https://@github.com/example/tool', 'https://github.com/example/tool?token=x',
    'https://github.com/example/tool#fragment', 'https://github.com/../tool',
    'https://github.com/example/%2e%2e/tool', 'https://github.com',
    'https://github.com/example\\tool', 'https://github.com/a b/tool',
    'https://github.com/\nexample/tool', 'https://github.com:99999/example/tool',
    'https://github.com:0/example/tool', 'https://..host/example/tool',
    'https://github.com/.', True,
])
def test_unsafe_repositories(url):
    with pytest.raises(ValueError):
        metadata.repository(url)


@pytest.mark.parametrize('value', ['', False, 'branch..name', 'a.lock', '.branch',
                                   'a//b', 'a@{b', 'a b', '/branch', 'a~1',
                                   '-', '-branch', '--upload-pack=example'])
def test_invalid_refs(value):
    with pytest.raises(ValueError):
        metadata.ref(value)


@pytest.mark.parametrize('data', [
    dict(POINTER, extra=True), dict(POINTER, path=None),
    dict(POINTER, ref=False), {'path': '.'},
])
def test_invalid_pointers(data):
    with pytest.raises(ValueError):
        metadata.validate_pointer(data)


@pytest.mark.parametrize('filename', ['source.json', 'listing.json',
                                     'SMART_TOOL.md', 'provenance.json'])
def test_symlink_files_fail(tmp_path, filename):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    target = tmp_path/('saved-' + filename)
    (directory/filename).rename(target)
    (directory/filename).symlink_to(target)
    with pytest.raises(ValueError, match='symlinks'):
        render(tmp_path)


@pytest.mark.parametrize('filename', ['categories.json', 'tools', 'tools/tool'])
def test_symlink_registry_and_directories_fail(tmp_path, filename):
    registry(tmp_path)
    entry(tmp_path, 'tool', LISTING)
    target = tmp_path/'saved'
    original = tmp_path/filename
    original.rename(target)
    original.symlink_to(target, target_is_directory=target.is_dir())
    with pytest.raises(ValueError, match='symlinks'):
        render(tmp_path)


def test_dangling_symlink_is_not_absent_metadata(tmp_path):
    (tmp_path/'categories.json').symlink_to(tmp_path/'missing')
    with pytest.raises(ValueError, match='symlinks'):
        render(tmp_path)


def test_file_reads_cannot_escape_root(tmp_path):
    with pytest.raises(ValueError, match='escape'):
        metadata.read_json(tmp_path/'..'/'outside.json', tmp_path)
    with pytest.raises(ValueError, match='belong'):
        metadata.read_json(tmp_path.parent/'outside.json', tmp_path)


@pytest.mark.parametrize('filename', ['source.json', 'listing.json',
                                     'SMART_TOOL.md', 'provenance.json'])
def test_nonregular_files_rejected_without_reading(tmp_path, filename):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    (directory/filename).unlink()
    os.mkfifo(directory/filename)
    with pytest.raises(ValueError):
        render(tmp_path)


@pytest.mark.parametrize('filename,bad', [
    ('SMART_TOOL.md', '---\nname: fixture\n'),
    ('SMART_TOOL.md', '---\n[]\n---\n'),
    ('SMART_TOOL.md', '---\nname: [unclosed\n---\n'),
    ('SMART_TOOL.md', MANIFEST.replace('[linux, macos]', 'true')),
    ('SMART_TOOL.md', MANIFEST.replace('fixture-tool', 'true')),
    ('provenance.json', '{"source":{}}'),
    ('provenance.json', json.dumps(dict(PROVENANCE, original_manifest_path='../SMART_TOOL.md'))),
    ('provenance.json', json.dumps(dict(PROVENANCE, last_success='not-a-date'))),
])
def test_invalid_snapshot_is_rejected_before_render(tmp_path, filename, bad):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    (directory/filename).write_text(bad)
    with pytest.raises(ValueError):
        render(tmp_path)


def test_half_snapshot_is_still_validated(tmp_path):
    directory = entry(tmp_path, 'tool', snapshot=False)
    write_json(directory/'provenance.json', {'source': {}})
    with pytest.raises(ValueError):
        render(tmp_path)


def test_registry_and_manifest_display_are_escaped(tmp_path):
    registry(tmp_path, [dict(CATEGORY, label='<img onerror="bad">', scope='<script>bad</script>')])
    directory = entry(tmp_path, 'tool', LISTING)
    (directory/'SMART_TOOL.md').write_text(MANIFEST.replace('Reproduce software failures', '<script>bad</script>'))
    result = render(tmp_path)
    assert '<script>bad</script>' not in result
    assert '<img onerror=' not in result
    assert '&lt;script&gt;bad&lt;/script&gt;' in result
    assert 'scope' not in result
    config = {'key': 'catalog', 'kind': 'catalog', 'title': '<script>title</script>',
              'description': '" onload="bad'}
    doc = build.document(config, result, ARGS)
    assert '<title>&lt;script&gt;title&lt;/script&gt;</title>' in doc
    assert 'content="&quot; onload=&quot;bad"' in doc


@pytest.mark.parametrize('label,scope', [
    ('测试环境', '创建隔离环境并重现软件故障。'),
    ('测试<img onerror="bad">&\'', '创建<script>bad</script>&"\'环境'),
])
def test_unicode_category_labels_and_scopes_are_preserved_and_escaped(tmp_path, label, scope):
    registry(tmp_path, [dict(CATEGORY, label=label, scope=scope)])
    entry(tmp_path, 'tool', LISTING)
    result = render(tmp_path)
    escaped_label = build.html.escape(label, quote=True)
    assert f'<option value="testing">{escaped_label}</option>' in result
    assert f'<span>Category: {escaped_label}</span>' in result
    assert 'category-scope' not in result
    assert 'data-scope' not in result
    assert scope not in result
    assert 'value="__unclassified__"' not in result
    assert 'data-category-filter' not in result
    assert 'category-navigation' not in result
    assert '<details class="category-scopes">' not in result
    assert '<img onerror=' not in result and '<script>bad</script>' not in result
    assert Cards(result).cards[0]['data-category'] == 'testing'
    assert f'Category: {label}' in Cards(result).cards[0]['text']


def test_upstream_cannot_recommend_itself(tmp_path):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool')
    (directory/'SMART_TOOL.md').write_text(MANIFEST.replace('name: fixture-tool', 'name: fixture-tool\nrecommended: true\ncategory: testing'))
    assert 'class="recommendation recommended"' not in render(tmp_path)


def test_render_and_validation_never_write_editorial_metadata(tmp_path):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    before = {p: p.read_bytes() for p in (tmp_path/'categories.json', directory/'listing.json')}
    prov = copy.deepcopy(PROVENANCE)
    prov['source']['commit'] = 'b'*40
    write_json(directory/'provenance.json', prov)
    assert 'Recommendation needs review' in render(tmp_path)
    assert all(p.read_bytes() == content for p, content in before.items())


def test_theme_sync_includes_helper_assets_and_builds_catalog(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'tool', LISTING)
    config = {'key': 'catalog', 'kind': 'catalog', 'title': 'Fixture catalog',
              'description': 'Fixture description'}
    write_json(tmp_path/'site'/'site.json', config)
    subprocess.run([sys.executable, str(SITE/'sync_theme.py'), str(tmp_path)], check=True)
    assert (tmp_path/'site/theme/catalog_metadata.py').read_bytes() == (SITE/'theme/catalog_metadata.py').read_bytes()
    assert (tmp_path/'site/theme/assets/mark-loop.png').is_file()
    out = tmp_path/'generated'
    subprocess.run([sys.executable, str(tmp_path/'site/theme/build.py'),
                    '--output', str(out)], check=True)
    assert 'class="recommendation recommended"' in (out/'index.html').read_text()
    for filename in ('site.js', 'style.css'):
        assert (out/'assets'/filename).read_bytes() == (SITE/'theme'/filename).read_bytes()
    assert (out/'.nojekyll').is_file()


def test_overview_and_spec_reader_build_without_catalog_metadata(tmp_path):
    out = tmp_path/'overview'
    subprocess.run([sys.executable, str(SITE/'theme/build.py'), '--output', str(out)], check=True)
    assert 'id="category"' not in (out/'index.html').read_text()
    assert len(list((out/'spec').glob('*.html'))) == 6
    assert (out/'assets/mark-loop.png').is_file()


@pytest.mark.parametrize('relative', ['skills/amplifier-smart-tools/SKILL.md', 'site/README.md'])
def test_recommendation_guidance_separates_creator_and_maintainer_roles(relative):
    guidance = ' '.join((SITE.parent/relative).read_text().split())
    assert 'Submissions are' in guidance
    assert 'category-agnostic' in guidance
    assert 'submitters do not add, choose, or create categories or recommendations' in guidance
    assert 'approved registry' in guidance
    assert 'Other' in guidance
    assert 'recommended: false' not in guidance
    assert 'creators do not nominate or select entries; catalog maintainers make those decisions.' in guidance
    assert 'catalog maintainers selected this tool as a preferred starting point' in guidance
    assert 'claim that specification conformance or task outcomes were checked' in guidance
    assert 'Any review results and scope limitations are stated only when recorded.' in guidance
    assert 'representative-task evidence' not in guidance
    if relative == 'site/README.md':
        assert 'Recommended is a plain, noninteractive badge.' in guidance
        assert 'the badge does not expand or link to recommendation-specific copy.' in guidance
        assert 'One control bar sits above all results:' in guidance
        assert ('Category scopes remain registry metadata and are not inserted into the control bar '
                'or displayed when a category is selected.') in guidance
        assert 'no second category-navigation area.' in guidance
        assert 'has no empty-state placeholder.' in guidance


def test_skill_discovery_validates_catalog_and_avoids_browse_fetches():
    skill = (SITE.parent/'skills/amplifier-smart-tools/SKILL.md').read_text()
    discover = ' '.join(skill.split('## Discover and install\n', 1)[1]
                        .split('\n### Recommendation and readiness', 1)[0].split())
    assert '[shared catalog metadata contract](https://github.com/microsoft/amplifier-smart-tools/blob/main/site/theme/catalog_metadata.py)' in discover
    assert 'catalog-owned editorial metadata, not upstream tool claims' in discover
    for requirement in (
        'duplicate JSON keys',
        'unknown registry/listing keys',
        'fail closed if a category has more than one recommended listing',
        '`ref` (default `main`)',
        '`path` (default `.`)',
        'to exactly match provenance',
        'full provenance commit SHA',
        'safe repository-relative `original_manifest_path`',
        '`last_success` timestamp',
        'If `ref` is a full SHA, it must equal the provenance commit.',
        'For browse-only requests',
        'Never fetch upstream just to complete a browse.',
    ):
        assert requirement in discover


def test_skill_creation_and_catalog_paths_are_scoped():
    skill = (SITE.parent/'skills/amplifier-smart-tools/SKILL.md').read_text()
    create = skill.split('## Create\n', 1)[1].split('\n## Add to the catalog', 1)[0]
    assert create.count('\n1.') == 1 and create.count('\n2.') == 1
    assert '\n3.' not in create
    assert 'We recommend using [smart-tool-creator](https://github.com/microsoft/amplifier-smart-tool-creator)' in create
    assert 'Read its current help' in create
    create_text = ' '.join(create.split())
    assert '[specification](https://github.com/microsoft/amplifier-smart-tools/tree/main/spec) README' in create_text
    assert 'only the chapters needed' in create
    assert '[reference examples](https://github.com/microsoft/amplifier-smart-tools/blob/main/spec/examples.md)' in create
    assert 'uv tool install' not in create
    assert 'catalog' not in create.casefold()

    add_to_catalog = skill.split('## Add to the catalog\n', 1)[1]
    add_text = ' '.join(add_to_catalog.split())
    assert all(add_to_catalog.count(f'\n{number}.') == 1 for number in (1, 2, 3))
    assert 'Build and check the tool through one of the Create paths above.' in add_text
    assert 'only the source pointer' in add_text
    assert 'Submissions are category-agnostic' in add_text
    assert 'Catalog maintainers assign classification from the approved registry' in add_text
    assert 'submitters do not add, choose, or create categories or recommendations' in add_text
    for forbidden in ('listing.json', 'recommended:', 'reviewed_source', 'optional listing'):
        assert forbidden not in add_text
    assert 'catalog refresh action generates those snapshots' in add_text
    assert 'Submit a pull request' in add_text
    assert '[catalog README contribution instructions](https://github.com/microsoft/amplifier-smart-tools-catalog#contributing)' in add_text
    assert 'request a recommendation' not in add_text
    assert 'recommended: false' not in skill
    assert 'full commit' in add_text
    assert 'defaults to `main`' in add_text
    assert 'defaults to `.`' in add_text


def test_catalog_maintainer_procedure_references_canonical_guide():
    guidance = ' '.join((SITE.parent/'site/README.md').read_text().split())
    assert '### Maintainer recommendation review' in guidance
    assert '[maintainer curation guide](https://github.com/microsoft/amplifier-smart-tools-catalog/blob/main/docs/maintainers.md)' in guidance
    assert 'normative maintainer roles and designation, renewal, replacement, and withdrawal procedures' in guidance
    assert 'review standard, merge gate' not in guidance
    assert 'For each designation, catalog maintainers should:' not in guidance
    assert 'Run the specification conformance kit against that revision.' not in guidance


def test_skill_preserves_keep_tools_current_guidance():
    guidance = (SITE.parent/'skills/amplifier-smart-tools/SKILL.md').read_text()
    keep_current = ' '.join(guidance.split('### Keep tools current\n', 1)[1]
                             .split('\n## Create', 1)[0].split())
    assert 'During an authorized tool invocation' in keep_current
    assert 'permission mode allows the update' in keep_current
    assert 'Catalog browsing and read-only availability or readiness checks never update tools' in keep_current
    assert 'if the user asked only for a check, report an available update without applying it unless the user authorizes updating' in keep_current
    assert 'If the install is behind, automatically update the tool, except in the cases outlined above.' in keep_current
    assert 'npx skills update amplifier-smart-tools' in keep_current


def test_website_artifact_retention_and_no_pr_deploy():
    import yaml

    workflow = yaml.safe_load((SITE.parent/'.github/workflows/website.yml').read_text())
    jobs = workflow['jobs']
    upload = next(step for step in jobs['build']['steps']
                  if step.get('uses', '').startswith('actions/upload-pages-artifact@'))
    assert upload['with']['retention-days'] == 7
    assert jobs['deploy']['if'] == "github.event_name == 'workflow_dispatch' && inputs.publish"