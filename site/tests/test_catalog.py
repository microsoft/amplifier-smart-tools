"""Deterministic catalog validation, renderer, and portable-theme integration."""
import copy
import json
import os
import re
import subprocess
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE/'theme'))
import build
import catalog_metadata as metadata
import graphics

REPO = 'https://github.com/example/fixture-tool.git'
SOURCE = 'https://github.com/example/fixture-tool'
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
TAGLINE = 'Reproduce software failures in isolated environments.'
ARGS = SimpleNamespace(local=False, family_owner=None)
CATALOG = {'key': 'catalog', 'kind': 'catalog', 'title': 'Fixture catalog',
           'description': 'Fixture description'}
CATALOG_URL = 'https://microsoft.github.io/amplifier-smart-tools-catalog/'
UNCLASSIFIED = '__unclassified__'
ALL_CHIP = ('', 'All', 'true')
OTHER_CHIP = (UNCLASSIFIED, 'Other', 'false')
RECOMMENDED = '<span class="tag">Recommended</span>'
REVIEW = '<span class="tag">Recommendation needs review</span>'
CREDIT = '<p class="credit">Developed by <strong>made</strong> at Microsoft</p>'
SKILL_NOTE = 'This installs the Smart Tools skill, not the tools themselves.'
OVERVIEW_URL = 'https://microsoft.github.io/amplifier-smart-tools/'
OVERVIEW = {'key': 'overview', 'kind': 'overview', 'title': 'Fixture overview',
            'description': 'Fixture description'}
# The overview and catalog URLs of a published build, a family owner's preview, and a local preview.
MODES = [
    (False, None, OVERVIEW_URL, CATALOG_URL),
    (False, 'robotdad', 'https://robotdad.github.io/amplifier-smart-tools/',
     'https://robotdad.github.io/amplifier-smart-tools-catalog/'),
    (True, None, '/amplifier-smart-tools/', '/amplifier-smart-tools-catalog/'),
]
ALTERNATE = '<link rel="alternate" type="text/markdown" href="./index.md">'
POST = '''---
title: Fixture post
date: 2026-11-16
author: Fixture Author
summary: Fixture summary.
---
Fixture body.
'''
PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + (640).to_bytes(4, 'big') + (480).to_bytes(4, 'big')
GIF = b'GIF89a' + (320).to_bytes(2, 'little') + (200).to_bytes(2, 'little')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def entry(root, slug, listing=None, snapshot=True, pointer=POINTER,
          manifest=MANIFEST, provenance=PROVENANCE):
    directory = root/'tools'/slug
    write_json(directory/'source.json', pointer)
    if snapshot:
        (directory/'SMART_TOOL.md').write_text(manifest, encoding='utf-8')
        write_json(directory/'provenance.json', provenance)
    if listing is not None:
        write_json(directory/'listing.json', listing)
    return directory


def registry(root, categories=None):
    write_json(root/'categories.json', {'categories': categories if categories is not None else [CATEGORY]})


def render(root):
    return build.catalog({}, ARGS, root)


def listing_page(root, slug, args=ARGS):
    _, tools = build.catalog_tools(root)
    tool = next(tool for tool in tools if tool['slug'] == slug)
    return build.listing_page(tool, tools, args)


def listing_markdown(root, slug):
    _, tools = build.catalog_tools(root)
    return build.listing_markdown(next(tool for tool in tools if tool['slug'] == slug))


class Page(HTMLParser):
    """Rows, cards, chips, links, and identified elements of rendered markup."""

    def __init__(self, source):
        super().__init__()
        self.ids = {}
        self.duplicate_ids = []
        self.rows = []
        self.cards = []
        self.chips = []
        self.links = []
        self.sections = []
        self.item = self.chip = self.anchor = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get('class') or '').split()
        identity = attrs.get('id')
        if identity:
            if identity in self.ids:
                self.duplicate_ids.append(identity)
            self.ids[identity] = attrs
        if tag == 'section':
            self.sections.append(attrs)
        elif tag == 'article' and 'data-tool' in attrs:
            region = self.sections[-1].get('aria-labelledby') if self.sections else None
            self.item = dict(attrs, text='', links=[], marks=[], region=region)
            (self.cards if 'tool-card' in classes else self.rows).append(self.item)
        elif tag == 'button' and 'chip' in classes:
            self.chip = dict(attrs, text='')
            self.chips.append(self.chip)
        elif tag == 'a':
            self.anchor = dict(attrs, text='')
            self.links.append(self.anchor)
            if self.item is not None:
                self.item['links'].append(attrs.get('href'))
        elif tag == 'span' and self.item is not None:
            self.item['marks'].extend(classes)

    def handle_endtag(self, tag):
        if tag == 'section' and self.sections:
            self.sections.pop()
        elif tag == 'article':
            self.item = None
        elif tag == 'button':
            self.chip = None
        elif tag == 'a':
            self.anchor = None

    def handle_data(self, data):
        for target in (self.item, self.chip, self.anchor):
            if target is not None:
                target['text'] += data

    def link(self, text):
        """Destination of the only link with this text."""
        [href] = [anchor['href'] for anchor in self.links if anchor['text'] == text]
        return href


def slugs(items):
    return [item['data-tool'] for item in items]


def chips(page):
    return [(chip['data-category'], chip['text'], chip['aria-pressed']) for chip in page.chips]


def result_count(text):
    return f'<span class="visually-hidden" id="result-count" role="status">{text}</span>'


def facts(source):
    """Terms and values of the only facts row, which holds nothing else."""
    [row] = re.findall(r'<dl class="facts">(.*?)</dl>', source)
    pairs = re.findall(r'<div><dt class="visually-hidden">(.*?)</dt><dd>(.*?)</dd></div>', row)
    assert ''.join(f'<div><dt class="visually-hidden">{term}</dt><dd>{value}</dd></div>'
                   for term, value in pairs) == row
    return dict(pairs)


def use_cases(source):
    return re.findall(r'<li>(.*?)</li>', source.split('<ul class="use-cases">', 1)[1].split('</ul>', 1)[0])


def recommended_names(source):
    """Names of the rows that carry the Recommended tag, which sits only after a row's name link."""
    names = re.findall(
        rf'<h3 class="app-row-name"><a href="[^"]*">([^<]*)</a>{RECOMMENDED}</h3>', source)
    assert len(names) == source.count(RECOMMENDED)
    return names


def post(root, slug, text=POST, files=None):
    directory = root/'site/blog'/slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'post.md').write_text(text, encoding='utf-8')
    for name, content in (files or {}).items():
        (directory/name).write_bytes(content)
    return directory


def build_blog(root):
    """Build the fixture blog and return its output directory."""
    out = root/'generated'
    build.build_blog(root, out, ARGS, OVERVIEW)
    return out/'blog'


def post_page(root, slug='fixture'):
    return (build_blog(root)/slug/'index.html').read_text(encoding='utf-8')


def post_content(source):
    """Rendered body of a post page, between its header and its pagination."""
    return source.split('</header>', 2)[2].split('<nav class="reader-pagination"', 1)[0]


def news_row(day, shown, label, title, url=''):
    if url:
        title = f'<a href="{url}">{title}{graphics.icon("arrow-right", 16)}</a>'
    return (f'<li><p class="news-meta"><time datetime="{day}">{shown}</time><span class="tag">{label}</span></p>'
            f'<p class="news-title">{title}</p></li>')


def news_list(*rows):
    return ('<aside class="news" aria-labelledby="news-title"><h2 id="news-title">What\'s new</h2>'
            f'<ol class="news-list">{"".join(rows)}</ol></aside>')


def chapters(root, **text):
    """Write every specification chapter: the given text, or only its heading."""
    (root/'spec').mkdir(parents=True)
    for name, label in build.CHAPTERS:
        (root/'spec'/f'{name}.md').write_text(text.get(name, f'# {label}\n'), encoding='utf-8')


def llms_sections(text):
    """Check the llms.txt layout and return the (name, url, notes) of each item by H2 title."""
    lines = text.splitlines()
    assert re.fullmatch(r'# \S.*', lines[0]) and re.fullmatch(r'> \S.*', lines[2])
    assert lines[1] == lines[3] == '' and text.endswith('\n') and not text.endswith('\n\n')
    sections, items = {}, None
    for line in lines[1:]:
        if line.startswith('#'):
            assert re.fullmatch(r'## \S.*', line) and line[3:] not in sections, line
            items = sections[line[3:]] = []
        elif line and items is not None:
            item = re.fullmatch(r'- \[([^\]]+)\]\((\S+)\)(?:: (\S.*))?', line)
            assert item, line
            items.append(item.groups())
    return sections


def llms_links(text):
    return [url for items in llms_sections(text).values() for _, url, _ in items]


def overview_llms(overview_url=OVERVIEW_URL, catalog_url=CATALOG_URL, tools='', blog=''):
    """The fixture overview's llms.txt, with the given featured tool items and blog section."""
    benefits = '\n'.join(f'- {title}: {text}' for title, text in build.BENEFITS)
    return f'''# Amplifier Smart Tools

> Fixture description

{build.ABOUT}

To start, give an agent this prompt: {build.FAMILY_PROMPT}

{benefits}

## Specification

- [Introduction]({overview_url}spec/index.md)
- [Structure]({overview_url}spec/structure.md)
- [Manifest]({overview_url}spec/manifest.md)
- [Invocation]({overview_url}spec/invocation.md)
- [Packaging]({overview_url}spec/packaging.md)
- [Examples]({overview_url}spec/examples.md)

## Catalog

- [All tools]({catalog_url}llms.txt): Every listed tool, by category
{tools}{blog}
## Optional

- [Source repository](https://github.com/microsoft/amplifier-smart-tools)
- [Conformance kit](https://github.com/microsoft/amplifier-smart-tools/tree/main/conformance)
'''


def test_catalog_without_registry_lists_rows_by_name_without_category_ui(tmp_path):
    entry(tmp_path, 'zulu')
    entry(tmp_path, 'alpha-two')
    entry(tmp_path, 'alpha', snapshot=False)
    assert metadata.load_catalog_metadata(tmp_path) == (None, {})
    result = render(tmp_path)
    page = Page(result)
    assert slugs(page.rows) == ['alpha', 'alpha-two', 'zulu']
    assert all(row['data-category'] == UNCLASSIFIED and 'hidden' not in row for row in page.rows)
    assert all(row['marks'] == ['app-icon'] for row in page.rows)
    assert all(row['links'] == [f'./tools/{row["data-tool"]}/'] * 2 for row in page.rows)
    assert not page.chips and not page.cards
    assert 'category-chips' not in page.ids
    assert 'featured' not in page.ids
    assert 'Recommended' not in result
    assert 'Recommendation needs review' not in result
    assert result_count('3 tools') in result
    assert page.rows[2]['data-search'] == f'fixture-tool zulu {TAGLINE.lower()} reproduce failures linux macos'
    assert 'No manifest snapshot is available yet.' in page.rows[0]['text']
    assert 'Inspect the source repository' not in page.rows[0]['text']
    assert TAGLINE in page.rows[2]['text']
    assert {'store-search', 'tool-search', 'empty-results'} <= page.ids.keys()


def test_catalog_with_registry_shows_search_chips_featured_and_all_tools(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'alpha')
    entry(tmp_path, 'alternative', {'category': 'testing'})
    entry(tmp_path, 'zulu', LISTING)
    result = render(tmp_path)
    page = Page(result)

    assert result.startswith('<section class="catalog-hero"><h1>Catalog</h1>')
    assert 'hidden' in page.ids['store-search']
    assert page.ids['tool-search']['type'] == 'search'
    order = [result.index(marker) for marker in (
        'id="store-search"', 'id="tool-search"', 'id="category-chips"', 'id="featured"',
        'id="all-tools-heading"', 'id="result-count"', 'class="app-list"',
        'id="empty-results"', 'data-clear', 'id="prompt"')]
    assert order == sorted(order)

    group = page.ids['category-chips']
    assert 'hidden' in group and group['role'] == 'group'
    assert chips(page) == [ALL_CHIP, ('testing', 'Test environments', 'false'), OTHER_CHIP]
    assert all(chip['type'] == 'button' for chip in page.chips)

    assert slugs(page.cards) == ['zulu']
    card = page.cards[0]
    assert card['class'] == 'tool-card wide'
    assert card['region'] == 'featured-heading'
    assert card['links'] == ['./tools/zulu/'] * 2
    assert TAGLINE in card['text']
    assert 'hidden' not in page.ids['featured']

    assert slugs(page.rows) == ['alpha', 'alternative', 'zulu']
    assert [row['data-category'] for row in page.rows] == [UNCLASSIFIED, 'testing', 'testing']
    assert all(row['class'] == 'app-row' and 'hidden' not in row for row in page.rows)
    assert all(row['region'] == 'all-tools-heading' for row in page.rows)
    assert all(row['links'] == [f'./tools/{row["data-tool"]}/'] * 2 for row in page.rows)
    assert all(TAGLINE in row['text'] for row in page.rows)
    assert [row['marks'] for row in page.rows] == [['app-icon'], ['app-icon'], ['app-icon', 'tag']]
    assert recommended_names(result) == ['Zulu']
    assert 'Recommendation needs review' not in result
    assert [row['data-search'] for row in page.rows] == [
        f'fixture-tool {name} {TAGLINE.lower()} reproduce failures linux macos {label}'
        for name, label in (('alpha', 'other'), ('alternative', 'test environments'),
                            ('zulu', 'test environments'))]
    assert result_count('3 tools') in result

    empty = page.ids['empty-results']
    assert 'hidden' in empty and 'empty' in empty['class'].split()
    assert '<button class="button" type="button" data-clear>' in result
    assert all(anchor['text'] != 'Add a tool' for anchor in page.links)
    assert 'catalog-note' not in result
    assert "Listings come from each tool's own manifest." not in result
    assert 'Let your agent browse.' in result
    assert build.FAMILY_PROMPT == 'Go to https://github.com/microsoft/amplifier-smart-tools and install it.'
    assert f'<pre id="prompt">{build.FAMILY_PROMPT}</pre>' in result
    assert result.endswith('<div class="callout"><h3>Ask your agent.</h3>'
                           f'{build.code_box(build.FAMILY_PROMPT, "Prompt", "prompt")}</div></section>')
    assert 'class="note"' not in result
    assert SKILL_NOTE not in result
    assert not hasattr(build, 'SKILL_NOTE')
    assert CATEGORY['scope'] not in result
    assert not page.duplicate_ids


def test_zero_recommendations_omit_featured_and_keep_every_row(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'classified-alpha', {'category': 'testing', 'recommended': False})
    entry(tmp_path, 'classified-beta', {'category': 'testing', 'recommended': False})
    entry(tmp_path, 'unclassified')
    result = render(tmp_path)
    page = Page(result)
    assert slugs(page.rows) == ['classified-alpha', 'classified-beta', 'unclassified']
    assert [row['data-category'] for row in page.rows] == ['testing', 'testing', UNCLASSIFIED]
    assert all('hidden' not in row and row['marks'] == ['app-icon'] for row in page.rows)
    assert 'featured' not in page.ids
    assert not page.cards
    assert 'Recommended' not in result
    assert 'Recommendation needs review' not in result
    assert chips(page) == [ALL_CHIP, ('testing', 'Test environments', 'false'), OTHER_CHIP]
    assert result_count('3 tools') in result


def test_two_categories_can_each_have_a_recommendation(tmp_path):
    second = dict(CATEGORY, id='authoring', label='Tool authoring')
    registry(tmp_path, [CATEGORY, second])
    entry(tmp_path, 'zulu', LISTING)
    entry(tmp_path, 'alpha', dict(LISTING, category='authoring'))
    result = render(tmp_path)
    page = Page(result)
    assert slugs(page.cards) == ['alpha', 'zulu']
    assert all(card['region'] == 'featured-heading' for card in page.cards)
    assert slugs(page.rows) == ['alpha', 'zulu']
    assert [row['data-category'] for row in page.rows] == ['authoring', 'testing']
    assert recommended_names(result) == ['Alpha', 'Zulu']
    assert all(row['marks'] == ['app-icon', 'tag'] for row in page.rows)
    assert chips(page) == [ALL_CHIP, ('testing', 'Test environments', 'false'),
                           ('authoring', 'Tool authoring', 'false')]
    assert result_count('2 tools') in result
    assert not page.duplicate_ids


def test_chips_cover_only_populated_categories_in_case_insensitive_label_order(tmp_path):
    registry(tmp_path, [
        CATEGORY,
        dict(CATEGORY, id='audio', label='audio tools'),
        dict(CATEGORY, id='research', label='Research'),
        dict(CATEGORY, id='media', label='Media'),
    ])
    entry(tmp_path, 'one', {'category': 'testing'})
    entry(tmp_path, 'two', {'category': 'research'})
    entry(tmp_path, 'three', {'category': 'audio'})
    entry(tmp_path, 'four', {'category': 'audio'})
    page = Page(render(tmp_path))
    assert chips(page) == [
        ALL_CHIP, ('audio', 'audio tools', 'false'), ('research', 'Research', 'false'),
        ('testing', 'Test environments', 'false')]
    assert {row['data-category'] for row in page.rows} == {chip['data-category'] for chip in page.chips[1:]}


def test_catalog_without_tools_has_only_the_all_chip(tmp_path):
    registry(tmp_path)
    result = render(tmp_path)
    page = Page(result)
    assert chips(page) == [ALL_CHIP]
    assert not page.rows and not page.cards
    assert result_count('0 tools') in result


@pytest.mark.parametrize('text,sentence', [
    ('One sentence. Two sentences.', 'One sentence.'),
    ('Is it broken? Find out.', 'Is it broken?'),
    ('Ship it! Then rest.', 'Ship it!'),
    ('Supports version 1.2 and python3.12 today. More follows.',
     'Supports version 1.2 and python3.12 today.'),
    ('Wrapped\n  across   lines.\nSecond.', 'Wrapped across lines.'),
    ('No terminal punctuation', 'No terminal punctuation'),
    ('Ends at the period.', 'Ends at the period.'),
    ('', ''),
])
def test_first_sentence(text, sentence):
    assert build.first_sentence(text) == sentence


def test_rows_and_cards_show_only_the_first_sentence_but_search_the_full_description(tmp_path):
    registry(tmp_path)
    manifest = MANIFEST.replace('isolated environments.', 'isolated environments. Then compare the traces.')
    entry(tmp_path, 'zulu', LISTING, manifest=manifest)
    page = Page(render(tmp_path))
    for item in (page.rows[0], page.cards[0]):
        assert TAGLINE in item['text']
        assert 'compare the traces' not in item['text']
    assert 'then compare the traces.' in page.rows[0]['data-search']


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
    page = Page(result)
    assert slugs(page.rows) == ['alpha', 'zulu']
    assert [row['data-category'] for row in page.rows] == [UNCLASSIFIED, 'testing']
    assert [row['marks'] for row in page.rows] == [['app-icon'], ['app-icon', 'tag']]
    assert result.count(REVIEW) == result.count(f'</p>{REVIEW}</div>') == 1
    assert 'Recommendation needs review' in page.rows[1]['text']
    assert 'Recommended' not in result
    assert 'featured' not in page.ids
    assert not page.cards
    assert chips(page) == [ALL_CHIP, ('testing', 'Test environments', 'false'), OTHER_CHIP]
    assert '<p class="status-pill">Recommendation needs review</p>' in listing_page(tmp_path, 'zulu')


@pytest.mark.parametrize('missing', ['SMART_TOOL.md', 'provenance.json', 'both'])
def test_missing_snapshot_needs_review(tmp_path, missing):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    if missing in ('SMART_TOOL.md', 'both'):
        (directory/'SMART_TOOL.md').unlink()
    if missing in ('provenance.json', 'both'):
        (directory/'provenance.json').unlink()
    result = render(tmp_path)
    page = Page(result)
    assert page.rows[0]['marks'] == ['app-icon', 'tag']
    assert result.count(REVIEW) == result.count(f'</p>{REVIEW}</div>') == 1
    assert not recommended_names(result)
    assert 'featured' not in page.ids
    assert '<p class="status-pill">Recommendation needs review</p>' in listing_page(tmp_path, 'tool')


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
    page = Page(result)
    assert slugs(page.rows) == ['alpha', 'zulu']
    assert [row['data-category'] for row in page.rows] == [UNCLASSIFIED, 'testing']
    assert slugs(page.cards) == (['zulu'] if matches else [])
    assert ('featured' in page.ids) is matches
    assert recommended_names(result) == (['Zulu'] if matches else [])
    assert result.count(REVIEW) == result.count(f'</p>{REVIEW}</div>') == (0 if matches else 1)
    assert page.rows[1]['marks'] == ['app-icon', 'tag']
    assert page.rows[0]['marks'] == ['app-icon']


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
def test_source_only_entries_render_searchable_other_without_marks(tmp_path, snapshot):
    registry(tmp_path)
    directory = entry(tmp_path, 'source-only-fixture', snapshot=snapshot)
    before = {path: path.read_bytes() for path in directory.iterdir()}
    result = render(tmp_path)
    page = Page(result)
    assert slugs(page.rows) == ['source-only-fixture']
    row = page.rows[0]
    assert row['data-category'] == UNCLASSIFIED
    assert row['data-search'].endswith(' other')
    assert 'source only fixture' in row['data-search']
    assert 'Source Only Fixture' in row['text']
    assert row['marks'] == ['app-icon']
    assert 'hidden' not in row
    assert row['region'] == 'all-tools-heading'
    assert chips(page) == [ALL_CHIP, OTHER_CHIP]
    assert 'featured' not in page.ids
    assert 'Recommended' not in result
    assert result_count('1 tool') in result
    assert ('No manifest snapshot is available yet.' in row['text']) is not snapshot
    assert (TAGLINE in row['text']) is snapshot
    assert facts(listing_page(tmp_path, 'source-only-fixture'))['Category'] == 'Other'
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
    page = Page(render(tmp_path))
    assert chips(page) == [ALL_CHIP, OTHER_CHIP]
    assert [row['data-category'] for row in page.rows] == [UNCLASSIFIED]
    assert page.rows[0]['data-search'].endswith(' other')
    assert facts(listing_page(tmp_path, 'tool'))['Category'] == 'Other'


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
    manifest = (MANIFEST.replace('Reproduce software failures', '<script>bad</script>')
                .replace('[Reproduce failures]', '''['<b onclick="bad">']''')
                .replace('---\n# Usage', '''version: '"><i>'\n---\n# Usage'''))
    entry(tmp_path, 'tool', LISTING, manifest=manifest)
    result = render(tmp_path)
    tool_page = listing_page(tmp_path, 'tool')
    for rendered in (result, tool_page):
        for raw in ('<script>bad</script>', '<img onerror=', '<b onclick', '<i>'):
            assert raw not in rendered
        assert '&lt;script&gt;bad&lt;/script&gt;' in rendered
        assert 'scope' not in rendered
    row = Page(result).rows[0]
    assert row.keys() == {'class', 'data-tool', 'data-category', 'data-search',
                          'text', 'links', 'marks', 'region'}
    assert '<b onclick="bad">' in row['data-search']
    assert '<li>&lt;b onclick=&quot;bad&quot;&gt;</li>' in tool_page
    assert facts(tool_page)['Version'] == 'v&quot;&gt;&lt;i&gt;'
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
    tool_page = listing_page(tmp_path, 'tool')
    page = Page(result)
    escaped_label = build.html.escape(label, quote=True)
    assert f' data-category="testing" aria-pressed="false">{escaped_label}</button>' in result
    assert chips(page) == [ALL_CHIP, ('testing', label, 'false')]
    assert f'<dt class="visually-hidden">Category</dt><dd>{escaped_label}</dd>' in tool_page
    assert page.rows[0]['data-category'] == 'testing'
    for rendered in (result, tool_page):
        assert scope not in rendered
        assert 'data-scope' not in rendered
        assert '<img onerror=' not in rendered and '<script>bad</script>' not in rendered


def test_upstream_cannot_recommend_itself(tmp_path):
    registry(tmp_path)
    manifest = MANIFEST.replace('name: fixture-tool', 'name: fixture-tool\nrecommended: true\ncategory: testing')
    entry(tmp_path, 'tool', manifest=manifest)
    result = render(tmp_path)
    page = Page(result)
    assert page.rows[0]['marks'] == ['app-icon']
    assert page.rows[0]['data-category'] == UNCLASSIFIED
    assert 'featured' not in page.ids
    assert 'Recommended' not in result
    tool_page = listing_page(tmp_path, 'tool')
    assert 'status-pill' not in tool_page
    assert facts(tool_page)['Category'] == 'Other'


def test_render_and_validation_never_write_editorial_metadata(tmp_path):
    registry(tmp_path)
    directory = entry(tmp_path, 'tool', LISTING)
    before = {p: p.read_bytes() for p in (tmp_path/'categories.json', directory/'listing.json')}
    prov = copy.deepcopy(PROVENANCE)
    prov['source']['commit'] = 'b'*40
    write_json(directory/'provenance.json', prov)
    assert 'Recommendation needs review' in render(tmp_path)
    assert all(p.read_bytes() == content for p, content in before.items())


def test_listing_page_presents_a_recommended_tool(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'zulu', LISTING)
    result = listing_page(tmp_path, 'zulu')
    page = Page(result)
    assert result.startswith('<section class="store-head"><span class="app-icon"')
    assert ('<p class="status-pill">Recommended</p><h1>Zulu</h1><dl class="facts">'
            '<div><dt class="visually-hidden">Category</dt><dd>Test environments</dd></div>'
            '<div><dt class="visually-hidden">Platform</dt><dd>Linux, macOS</dd></div>'
            '<div><dt class="visually-hidden">Publisher</dt><dd>example</dd></div></dl>'
            f'<p class="standfirst">{TAGLINE}</p><div class="actions">') in result
    assert page.link('Get') == '#get-started'
    assert page.link('View on GitHub') == SOURCE
    assert all(anchor['text'] != 'Website' for anchor in page.links)
    assert facts(result) == {'Category': 'Test environments', 'Platform': 'Linux, macOS',
                             'Publisher': 'example'}
    assert use_cases(result) == ['Reproduce failures']
    assert 'get-started' in page.ids
    assert f'<pre id="prompt">Go to {SOURCE} and install it.</pre>' in result
    assert all(anchor['text'] != 'Read manifest' for anchor in page.links)
    for provenance in ('class="note"', 'Manifest snapshot', '2026-01-01', COMMIT[:7], 'SMART_TOOL.md'):
        assert provenance not in result
    assert 'More tools.' not in result
    assert not page.rows
    order = [result.index(marker) for marker in (
        'class="store-head"', 'class="facts"', 'class="standfirst"', '</section>',
        'id="get-started"', 'class="use-cases"')]
    assert order == sorted(order)


@pytest.mark.parametrize('listing,pill', [
    (None, None),
    ({'category': 'testing'}, None),
    (LISTING, 'Recommended'),
    (dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], commit='b' * 40)),
     'Recommendation needs review'),
])
def test_listing_page_status_pill_follows_recommendation_state(tmp_path, listing, pill):
    registry(tmp_path)
    entry(tmp_path, 'tool', listing)
    result = listing_page(tmp_path, 'tool')
    assert result.count('class="status-pill"') == (1 if pill else 0)
    if pill:
        assert f'<p class="status-pill">{pill}</p><h1>Tool</h1>' in result


def test_listing_page_without_registry_has_no_category_fact_or_pill(tmp_path):
    entry(tmp_path, 'alpha')
    entry(tmp_path, 'zulu')
    result = listing_page(tmp_path, 'zulu')
    assert facts(result) == {'Platform': 'Linux, macOS', 'Publisher': 'example'}
    assert 'status-pill' not in result
    assert 'More tools.' not in result


@pytest.mark.parametrize('version', ['2.0.1', 'v2.0.1'])
def test_listing_page_version_fact_has_one_prefix(tmp_path, version):
    entry(tmp_path, 'tool', manifest=MANIFEST.replace('description:', f'version: {version}\ndescription:'))
    assert facts(listing_page(tmp_path, 'tool'))['Version'] == 'v2.0.1'


def test_listing_page_facts_use_cases_and_remaining_description(tmp_path):
    registry(tmp_path)
    cases = [f'Use case {number}' for number in range(1, 9)]
    manifest = f'''---
name: fixture-tool
version: 1.4.2
description: >
  Reproduce software failures in isolated environments.
  Then compare the traces. Keep the evidence.
platforms: [linux, macos, windows, freebsd]
use_cases: {json.dumps(cases)}
---
'''
    pointer = {'repository': 'https://github.com/microsoft/fixture-tool'}
    entry(tmp_path, 'tool', {'category': 'testing'}, pointer=pointer, manifest=manifest)
    result = listing_page(tmp_path, 'tool')
    assert f'<p class="standfirst">{TAGLINE}</p>' in result
    assert list(facts(result).items()) == [
        ('Category', 'Test environments'), ('Platform', 'Linux, macOS, Windows, freebsd'),
        ('Publisher', 'Microsoft'), ('Version', 'v1.4.2')]
    assert use_cases(result) == cases[:6]
    assert '<h2>Use it to.</h2><p>Then compare the traces. Keep the evidence.</p>' in result
    assert f'<pre id="prompt">Go to {pointer["repository"]} and install it.</pre>' in result


def test_listing_page_without_use_cases_or_platforms(tmp_path):
    manifest = (MANIFEST.replace('[linux, macos]', '[]').replace('[Reproduce failures]', '[]')
                .replace('isolated environments.', 'isolated environments. Then compare the traces.'))
    entry(tmp_path, 'tool', manifest=manifest)
    result = listing_page(tmp_path, 'tool')
    assert facts(result)['Platform'] == 'Not declared'
    assert 'use-cases' not in result
    assert '<h2>What it does.</h2></div><p>Then compare the traces.</p>' in result
    assert result.index('id="get-started"') < result.index('What it does.')


def test_listing_page_without_snapshot_stays_readable(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'tool', snapshot=False)
    result = listing_page(tmp_path, 'tool')
    page = Page(result)
    assert '<h1>Tool</h1><dl class="facts">' in result
    assert '</dl><p class="standfirst">No manifest snapshot is available yet.</p>' in result
    assert result.count('No manifest snapshot is available yet.') == 1
    assert '<p>Inspect the source repository for current guidance.</p>' in result
    assert facts(result) == {'Category': 'Other', 'Platform': 'Not declared', 'Publisher': 'example'}
    assert 'class="note"' not in result
    assert all(anchor['text'] != 'Read manifest' for anchor in page.links)
    assert page.link('View on GitHub') == SOURCE
    assert f'<pre id="prompt">Go to {SOURCE} and install it.</pre>' in result


def test_subdirectory_pointer_sends_readers_to_the_tree_url(tmp_path):
    pointer = {'repository': REPO, 'ref': 'release/v1', 'path': 'packages/fixture tool'}
    provenance = dict(PROVENANCE, source=dict(PROVENANCE['source'], ref='release/v1',
                                              path='packages/fixture tool'),
                      original_manifest_path='packages/fixture tool/SMART_TOOL.md')
    entry(tmp_path, 'tool', pointer=pointer, provenance=provenance)
    tree = f'{SOURCE}/tree/release/v1/packages/fixture%20tool'
    _, [tool] = build.catalog_tools(tmp_path)
    assert tool['source_url'] == tree
    result = listing_page(tmp_path, 'tool')
    page = Page(result)
    assert page.link('View on GitHub') == tree
    assert f'<pre id="prompt">Go to {tree} and install it.</pre>' in result
    assert all(anchor['text'] != 'Read manifest' for anchor in page.links)
    for provenance in (COMMIT[:7], 'SMART_TOOL.md', '/blob/'):
        assert provenance not in result
    assert facts(result)['Publisher'] == 'example'
    copy_lines = listing_markdown(tmp_path, 'tool').splitlines()
    assert f'- Source: {tree}' in copy_lines and f'> Go to {tree} and install it.' in copy_lines


def test_pointer_to_another_ref_sends_readers_to_that_ref(tmp_path):
    provenance = dict(PROVENANCE, source=dict(PROVENANCE['source'], ref='next'))
    entry(tmp_path, 'tool', pointer={'repository': REPO, 'ref': 'next'}, provenance=provenance)
    _, [tool] = build.catalog_tools(tmp_path)
    assert tool['source_url'] == f'{SOURCE}/tree/next'
    assert f'<pre id="prompt">Go to {SOURCE}/tree/next and install it.</pre>' in listing_page(tmp_path, 'tool')


@pytest.mark.parametrize('local,website', [
    (False, 'https://robotdad.github.io/possibly/'),
    (True, '/possibly/'),
])
def test_listing_page_links_the_website_of_a_family_tool(tmp_path, local, website):
    entry(tmp_path, 'possibly', pointer={'repository': 'https://github.com/robotdad/possibly.git'})
    entry(tmp_path, 'other')
    args = SimpleNamespace(local=local, family_owner=None)
    page = Page(listing_page(tmp_path, 'possibly', args))
    assert page.link('Website') == website
    assert page.link('View on GitHub') == 'https://github.com/robotdad/possibly'
    assert all(anchor['text'] != 'Website' for anchor in Page(listing_page(tmp_path, 'other', args)).links)


def test_listing_page_more_tools_lists_the_category_then_recommendations(tmp_path):
    registry(tmp_path, [CATEGORY, dict(CATEGORY, id='authoring', label='Tool authoring')])
    entry(tmp_path, 'alpha', {'category': 'testing'})
    entry(tmp_path, 'bravo', {'category': 'testing'})
    entry(tmp_path, 'charlie', dict(LISTING, category='authoring'))
    entry(tmp_path, 'delta')
    entry(tmp_path, 'echo', {'category': 'authoring'})
    result = listing_page(tmp_path, 'alpha')
    page = Page(result)
    assert 'More tools.' in result
    assert slugs(page.rows) == ['bravo', 'charlie']
    assert all(row['links'] == [f'../{row["data-tool"]}/'] * 2 for row in page.rows)
    assert [row['marks'] for row in page.rows] == [['app-icon'], ['app-icon', 'tag']]
    assert recommended_names(result) == ['Charlie']
    assert slugs(Page(listing_page(tmp_path, 'charlie')).rows) == ['echo']
    assert slugs(Page(listing_page(tmp_path, 'delta')).rows) == ['charlie']
    assert slugs(Page(listing_page(tmp_path, 'echo')).rows) == ['charlie']


def test_listing_page_more_tools_stops_at_three(tmp_path):
    registry(tmp_path)
    for slug in ('alpha', 'bravo', 'charlie', 'delta', 'echo'):
        entry(tmp_path, slug, {'category': 'testing'})
    assert slugs(Page(listing_page(tmp_path, 'charlie')).rows) == ['alpha', 'bravo', 'delta']


def test_listing_markdown_presents_a_recommended_tool(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'zulu', LISTING)
    assert listing_markdown(tmp_path, 'zulu') == f'''# Zulu

{TAGLINE}

- Status: Recommended
- Category: Test environments
- Platforms: Linux, macOS
- Publisher: example
- Source: {SOURCE}

## Get started

Give this prompt to your agent:

> Go to {SOURCE} and install it.

## Use it to

- Reproduce failures
'''


def test_listing_markdown_without_registry_platforms_or_use_cases(tmp_path):
    manifest = (MANIFEST.replace('[linux, macos]', '[]').replace('[Reproduce failures]', '[]')
                .replace('isolated environments.', 'isolated environments. Then compare the traces.')
                .replace('description:', 'version: 1.4.2\ndescription:'))
    pointer = {'repository': 'https://github.com/microsoft/fixture-tool'}
    entry(tmp_path, 'tool', pointer=pointer, manifest=manifest)
    assert listing_markdown(tmp_path, 'tool') == f'''# Tool

{TAGLINE} Then compare the traces.

- Publisher: Microsoft
- Version: v1.4.2
- Source: {pointer['repository']}

## Get started

Give this prompt to your agent:

> Go to {pointer['repository']} and install it.
'''


def test_listing_markdown_lists_every_platform_and_use_case_in_plain_punctuation(tmp_path):
    registry(tmp_path)
    manifest = (MANIFEST.replace('[linux, macos]', '[linux, macos, windows, freebsd]')
                .replace('[Reproduce failures]', '[Reproduce failures, "Keep the tool\u2019s evidence"]')
                .replace('Reproduce software failures', 'Reproduce \u201csoftware\u201d failures'))
    entry(tmp_path, 'tool', {'category': 'testing'}, manifest=manifest)
    assert listing_markdown(tmp_path, 'tool') == f'''# Tool

Reproduce "software" failures in isolated environments.

- Category: Test environments
- Platforms: Linux, macOS, Windows, freebsd
- Publisher: example
- Source: {SOURCE}

## Get started

Give this prompt to your agent:

> Go to {SOURCE} and install it.

## Use it to

- Reproduce failures
- Keep the tool's evidence
'''


def test_listing_markdown_without_snapshot_stays_readable(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'tool', snapshot=False)
    assert listing_markdown(tmp_path, 'tool') == f'''# Tool

No manifest snapshot is available yet. Inspect the source repository for current guidance.

- Category: Other
- Publisher: example
- Source: {SOURCE}

## Get started

Give this prompt to your agent:

> Go to {SOURCE} and install it.
'''


@pytest.mark.parametrize('listing,recommended', [
    (None, False),
    ({'category': 'testing'}, False),
    (LISTING, True),
    (dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], commit='b' * 40)), False),
])
def test_listing_markdown_status_line_marks_only_a_recommended_tool(tmp_path, listing, recommended):
    registry(tmp_path)
    entry(tmp_path, 'tool', listing)
    lines = listing_markdown(tmp_path, 'tool').splitlines()
    assert (lines[4] == '- Status: Recommended') is recommended
    assert lines[4 + recommended] == f'- Category: {"Test environments" if listing else "Other"}'
    assert [line for line in lines if 'Status' in line or 'review' in line] == ['- Status: Recommended'] * recommended


def test_build_listings_writes_one_page_per_tool(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'alpha', snapshot=False)
    entry(tmp_path, 'zulu', LISTING)
    out = tmp_path/'generated'
    config = dict(CATALOG)
    build.build_listings(tmp_path, out, ARGS, config)
    assert config == CATALOG
    assert sorted(path.relative_to(out).as_posix() for path in out.rglob('*') if path.is_file()) == [
        'tools/alpha/index.html', 'tools/alpha/index.md', 'tools/zulu/index.html', 'tools/zulu/index.md']
    for slug in ('alpha', 'zulu'):
        assert (out/'tools'/slug/'index.md').read_text(encoding='utf-8') == listing_markdown(tmp_path, slug)
        page = (out/'tools'/slug/'index.html').read_text(encoding='utf-8')
        assert page.count(ALTERNATE) == page.count('rel="alternate"') == 1
        assert (f'<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">{ALTERNATE}'
                f'<link rel="describedby" type="text/plain" href="{CATALOG_URL}llms.txt">'
                '<link rel="stylesheet" href="../../assets/style.css">') in page
    zulu = (out/'tools/zulu/index.html').read_text(encoding='utf-8')
    assert zulu.startswith('<!doctype html>')
    assert '<title>Zulu | Amplifier Smart Tools catalog</title>' in zulu
    assert f'<meta name="description" content="{TAGLINE}">' in zulu
    for asset in ('favicon.svg', 'style.css', 'site.js'):
        assert f'="../../assets/{asset}"' in zulu
    assert './assets/' not in zulu.replace('../../assets/', '')
    assert '<p class="status-pill">Recommended</p><h1>Zulu</h1>' in zulu
    assert f'<pre id="prompt">Go to {SOURCE} and install it.</pre>' in zulu
    assert '<a href="https://microsoft.github.io/amplifier-smart-tools-catalog/" aria-current="page">Catalog</a>' in zulu
    alpha = (out/'tools/alpha/index.html').read_text(encoding='utf-8')
    assert '<title>Alpha | Amplifier Smart Tools catalog</title>' in alpha
    assert '<meta name="description" content="No manifest snapshot is available yet.">' in alpha
    assert slugs(Page(alpha).rows) == ['zulu']
    assert not Page(zulu).duplicate_ids and not Page(alpha).duplicate_ids


def test_catalog_llms_lists_recommendations_then_categories_by_label_with_other_last(tmp_path):
    registry(tmp_path, [CATEGORY, dict(CATEGORY, id='audio', label='audio tools'),
                        dict(CATEGORY, id='writing', label='Writing'), dict(CATEGORY, id='empty', label='Empty')])
    entry(tmp_path, 'zulu', LISTING)
    entry(tmp_path, 'alpha', {'category': 'audio'})
    entry(tmp_path, 'bravo', {'category': 'writing'})
    entry(tmp_path, 'charlie', snapshot=False)
    entry(tmp_path, 'delta', {'category': 'testing'}, manifest=MANIFEST.replace(
        'isolated environments.', 'isolated environments. Then compare the traces.'))
    config = dict(CATALOG)
    assert build.catalog_llms(config, ARGS, tmp_path) == f'''# Amplifier Smart Tools catalog

> Fixture description

To let an agent find and install these tools, give it this prompt: {build.FAMILY_PROMPT}

## Recommended

- [Zulu]({CATALOG_URL}tools/zulu/index.md): {TAGLINE}

## audio tools

- [Alpha]({CATALOG_URL}tools/alpha/index.md): {TAGLINE}

## Test environments

- [Delta]({CATALOG_URL}tools/delta/index.md): {TAGLINE}
- [Zulu]({CATALOG_URL}tools/zulu/index.md): {TAGLINE}

## Writing

- [Bravo]({CATALOG_URL}tools/bravo/index.md): {TAGLINE}

## Other

- [Charlie]({CATALOG_URL}tools/charlie/index.md): No manifest snapshot is available yet.
'''
    assert config == CATALOG


def test_markdown_copies_keep_a_category_label_as_written(tmp_path):
    registry(tmp_path, [dict(CATEGORY, label='Pr\u00fcfung')])
    entry(tmp_path, 'tool', {'category': 'testing'})
    assert '\n## Pr\u00fcfung\n' in build.catalog_llms(dict(CATALOG), ARGS, tmp_path)
    assert '\n- Category: Pr\u00fcfung\n' in listing_markdown(tmp_path, 'tool')


def test_catalog_llms_without_registry_lists_all_tools_by_name(tmp_path):
    entry(tmp_path, 'zulu')
    entry(tmp_path, 'alpha-two')
    entry(tmp_path, 'alpha', snapshot=False)
    assert build.catalog_llms(CATALOG, ARGS, tmp_path) == f'''# Amplifier Smart Tools catalog

> Fixture description

To let an agent find and install these tools, give it this prompt: {build.FAMILY_PROMPT}

## All tools

- [Alpha]({CATALOG_URL}tools/alpha/index.md): No manifest snapshot is available yet.
- [Alpha Two]({CATALOG_URL}tools/alpha-two/index.md): {TAGLINE}
- [Zulu]({CATALOG_URL}tools/zulu/index.md): {TAGLINE}
'''


def test_catalog_llms_omits_recommended_when_no_tool_is_recommended(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'drifted', dict(LISTING, reviewed_source=dict(LISTING['reviewed_source'], commit='b' * 40)))
    entry(tmp_path, 'ordinary', {'category': 'testing'})
    sections = llms_sections(build.catalog_llms(CATALOG, ARGS, tmp_path))
    assert list(sections) == ['Test environments']
    assert [name for name, _, _ in sections['Test environments']] == ['Drifted', 'Ordinary']


@pytest.mark.parametrize('local,owner,overview_url,catalog_url', MODES)
def test_catalog_llms_links_every_tool_to_a_file_the_build_writes(tmp_path, local, owner, overview_url, catalog_url):
    registry(tmp_path)
    entry(tmp_path, 'alpha', snapshot=False)
    entry(tmp_path, 'bravo', {'category': 'testing'})
    entry(tmp_path, 'zulu', LISTING)
    args = SimpleNamespace(local=local, family_owner=owner)
    out = tmp_path/'generated'
    build.build_listings(tmp_path, out, args, CATALOG)
    links = llms_links(build.catalog_llms(CATALOG, args, tmp_path))
    assert links == [f'{catalog_url}tools/{slug}/index.md' for slug in ('zulu', 'bravo', 'zulu', 'alpha')]
    assert all((out/url.removeprefix(catalog_url)).is_file() for url in links)


@pytest.mark.parametrize('key,kind,current', [
    ('catalog', 'catalog', 'Catalog'),
    ('overview', 'blog', 'Blog'),
    ('overview', 'reader', 'Specification'),
    ('overview', 'overview', None),
    ('possibly', 'tool', None),
])
def test_document_shell(key, kind, current):
    doc = build.document(dict(CATALOG, key=key, kind=kind), '<p>body</p>', ARGS)
    page = Page(doc)
    destinations = [
        (CATALOG_URL, 'Catalog'),
        (f'{OVERVIEW_URL}blog/', 'Blog'),
        ('https://github.com/microsoft/amplifier-smart-tools/tree/main/spec', 'Specification'),
        (build.repo_url(key), 'GitHub'),
    ]
    assert doc.count(CREDIT) == doc.count('class="credit"') == doc.count('made') == doc.count('Microsoft') == 1
    assert f'<a class="skip" href="#main">Skip to content</a>{graphics.GLYPH_DEFS}<header class="masthead">' in doc
    footer = doc.split('<footer class="site-footer">', 1)[1].split('</footer>', 1)[0]
    assert footer.startswith(f'<div class="wrap footer-grid"><a class="brand" href="{OVERVIEW_URL}">')
    assert footer.endswith(f'</nav>{CREDIT}</div>')
    for credit in ('Office of the CTO', 'Math', 'Design', 'Engineering', 'class="organization"',
                   'attribution', 'class="team"'):
        assert credit not in doc
    assert doc.count('<svg class="brand-mark"') == 3
    assert page.link('Skip to content') == '#main'
    assert '<main class="wrap" id="main"><p>body</p></main>' in doc
    nav = doc.split('<nav class="nav" aria-label="Main navigation">', 1)[1].split('</nav>', 1)[0]
    assert re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', nav) == [
        (url, ' aria-current="page"' if label == current else '', label) for url, label in destinations]
    links = footer.split('<nav class="footer-links" aria-label="Footer">', 1)[1].split('</nav>', 1)[0]
    assert links == ''.join(f'<a href="{url}">{label}</a>' for url, label in destinations)
    rows = doc.split('<ul class="menu-rows">', 1)[1].split('</ul>', 1)[0]
    assert re.findall(r'<li><a href="([^"]+)"><span>([^<]+)</span><svg ', rows) == destinations
    assert rows.count('<li>') == len(destinations)
    assert doc.count('aria-current') == (1 if current else 0)
    assert 'Build' not in doc and '#build' not in doc
    assert ('<button class="menu-toggle" type="button" data-menu-toggle aria-expanded="false" '
            'aria-controls="menu" aria-label="Open menu">') in doc
    menu = page.ids['menu']
    assert menu['class'] == 'menu' and menu['role'] == 'dialog' and menu['aria-modal'] == 'true'
    assert doc.index('id="menu"') < doc.index('data-menu-close') < doc.index('class="menu-rows"')
    assert doc.index('</main>') < doc.index('<footer class="site-footer">') < doc.index('id="menu"')
    assert '<link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">' in doc
    for image in ('<img', '.gif', '.png', '.mp4'):
        assert image not in doc
    assert not page.duplicate_ids


@pytest.mark.parametrize('local,owner,overview_url,catalog_url', MODES)
def test_document_head_names_the_markdown_copy_and_the_llms_file(local, owner, overview_url, catalog_url):
    args = SimpleNamespace(local=local, family_owner=owner)
    icon = '<link rel="icon" href="./assets/favicon.svg" type="image/svg+xml">'
    stylesheet = '<link rel="stylesheet" href="./assets/style.css">'
    for key, kind, site in (('overview', 'overview', overview_url), ('overview', 'blog', overview_url),
                            ('overview', 'reader', overview_url), ('catalog', 'catalog', catalog_url),
                            ('possibly', 'tool', None)):
        config = dict(CATALOG, key=key, kind=kind)
        described = f'<link rel="describedby" type="text/plain" href="{site}llms.txt">' if site else ''
        bare = build.document(config, '', args)
        copied = build.document(config, '', args, markdown='./index.md')
        assert f'{icon}{described}{stylesheet}' in bare.split('</head>', 1)[0]
        assert f'{icon}{ALTERNATE}{described}{stylesheet}' in copied.split('</head>', 1)[0]
        assert copied.replace(ALTERNATE, '') == bare
        assert 'rel="alternate"' not in bare and 'text/markdown' not in bare
        assert bare.count('rel="describedby"') == bare.count('llms.txt') == (1 if site else 0)


@pytest.mark.parametrize('accent', ['red', '#12345', '#1234567', '#12345g',
                                    '#123456;background:url(https://example.com)'])
def test_document_rejects_accent_that_is_not_a_hex_color(accent):
    with pytest.raises(ValueError, match='Accent'):
        build.document(dict(CATALOG, accent=accent), '', ARGS)


def test_rendered_catalog_carries_every_hook_the_script_reads(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'reality-check', LISTING)
    entry(tmp_path, 'digital-twin-universe', {'category': 'testing'})
    doc = build.document(CATALOG, render(tmp_path), ARGS)
    page = Page(doc)
    script = (SITE/'theme/site.js').read_text(encoding='utf-8')
    identities = re.findall(r"getElementById\('([^']+)'\)", script)
    assert {'menu', 'tool-search', 'store-search', 'category-chips', 'result-count',
            'featured', 'empty-results'} <= set(identities)
    assert set(identities) <= page.ids.keys()
    for attribute in ('data-copy', 'data-menu-toggle', 'data-menu-close', 'data-clear'):
        assert f'[{attribute}]' in script
        assert re.search(rf'<button [^>]*\b{attribute}\b', doc)
    assert 'data-copy="prompt"' in doc and 'prompt' in page.ids
    assert '<div class="copy-region">' in doc and '<p class="status-message" role="status"' in doc
    assert ".app-row[data-tool]" in script
    assert slugs(page.rows) == ['digital-twin-universe', 'reality-check']
    assert not page.duplicate_ids


def test_stylesheet_fonts_ship_with_the_theme():
    css = (SITE/'theme/style.css').read_text(encoding='utf-8')
    fonts = re.findall(r'url\("\./(fonts/[^"]+)"\)', css)
    assert len(fonts) == len(re.findall(r'url\(', css)) >= 1
    for font in fonts:
        assert (SITE/'theme/assets'/font).is_file()
    licenses = list((SITE/'theme/assets/fonts').glob('*-OFL.txt'))
    assert len(licenses) == len(fonts)
    assert [path.name for path in (SITE/'theme/assets').iterdir()] == ['fonts']


def test_tools_with_their_own_artwork_show_it_on_the_ink_tile(tmp_path):
    assert set(graphics.ARTWORK) == {'reality-check', 'smart-tool-creator', 'digital-twin-universe'}
    for slug in (*graphics.ARTWORK, 'plain'):
        entry(tmp_path, slug)
    result = render(tmp_path)
    page = Page(result)
    assert {row['data-tool']: row['marks'] for row in page.rows} == {
        **{slug: ['app-icon', 'art'] for slug in graphics.ARTWORK}, 'plain': ['app-icon']}
    assert result.count(f'style="--field:{graphics.TILE}"') == len(graphics.ARTWORK)
    assert result.count('style="--field:var(--field-fallback)"') == 1
    for slug, drawing in graphics.ARTWORK.items():
        assert result.count(drawing) == 1
        assert graphics.tool_art(slug) == drawing


def test_mark_is_a_wrench_that_holds_a_spark():
    for name in ('MARK_BODY', 'MARK_SPARK'):
        assert re.fullmatch(r'M[-0-9. ACLMZ]+Z', getattr(graphics, name))
    assert graphics.MARK == f'<path d="{graphics.MARK_BODY}"/><path d="{graphics.MARK_SPARK}"/>'
    assert graphics.glyph('') == graphics.MARK
    assert graphics.mark() == (
        '<svg class="brand-mark" viewBox="-2 -2 68 68" aria-hidden="true">'
        f'<path d="{graphics.MARK_BODY}" fill="currentColor"/>'
        f'<path class="mark-spark" d="{graphics.MARK_SPARK}"/></svg>')
    assert graphics.mark('footer-mark').startswith('<svg class="footer-mark" ')
    doc = build.document(CATALOG, '', ARGS)
    assert doc.count(graphics.mark()) == doc.count('class="mark-spark"') == 3
    css = (SITE/'theme/style.css').read_text(encoding='utf-8')
    assert '\n.mark-spark {\n  fill: ' in css


def test_favicon_is_well_formed_and_follows_the_color_scheme():
    root = ElementTree.fromstring(graphics.FAVICON)
    svg = '{http://www.w3.org/2000/svg}'
    assert root.tag == f'{svg}svg' and root.attrib == {'viewBox': '-4 -4 72 72'}
    style, body, spark = root
    assert [child.tag for child in root] == [f'{svg}style', f'{svg}path', f'{svg}path']
    assert body.attrib == {'d': graphics.MARK_BODY}
    assert spark.attrib == {'class': 'spark', 'd': graphics.MARK_SPARK}
    light, dark = style.text.split('@media(prefers-color-scheme:dark)')
    fills = r'path\{fill:(#[0-9a-f]{6})\}\.spark\{fill:(#[0-9a-f]{6})\}'
    assert re.fullmatch(fills, light) and re.fullmatch(r'\{' + fills + r'\}', dark)
    assert len(set(re.findall(r'#[0-9a-f]{6}', style.text))) == 4


def test_theme_version_matches_family_registry():
    version = json.loads((SITE/'theme/family.json').read_text(encoding='utf-8'))['version']
    assert f'Theme v{version},' in build.__doc__


def test_overview_sections(tmp_path):
    result = build.overview({}, ARGS, tmp_path)
    page = Page(result)
    assert result.startswith('<section class="hero"><div class="hero-grid"><div>')
    assert '</div>\n    </div></div></section>' in result
    row = build.TEXT['diagram']['tool']['row']
    assert f'<strong>{row["name"]}</strong><span>{row["text"]}</span>' in result
    for absent in ('<img', '<aside', 'class="news', 'class="plate'):
        assert absent not in result
    for title, text in build.BENEFITS:
        assert f'<strong>{build.esc(title)}</strong><p>{build.esc(text)}</p>' in result
    assert page.link('Browse the catalog') == CATALOG_URL
    assert page.link('Build a tool') == '#build'
    assert page.ids.keys() == {'get-started', 'prompt', 'why', 'build', 'what'}
    assert page.ids['get-started']['class'] == 'hero-start'
    assert ('<div class="hero-start" id="get-started">'
            '<p class="eyebrow">Teach your agent about Smart Tools</p>'
            f'{build.code_box(build.FAMILY_PROMPT, "Prompt", "prompt")}</div>') in result
    assert f'<pre id="prompt">{build.FAMILY_PROMPT}</pre>' in result
    for absent in ('class="standfirst"', 'class="note"', SKILL_NOTE, 'Get started.', 'Ask your agent.',
                   'class="callout"', 'A sub-agent you call like a CLI.'):
        assert absent not in result
    assert 'Start with these.' not in result
    assert not page.cards
    order = [result.index(marker) for marker in (
        'id="get-started"', 'id="prompt"', 'class="actions"', '</section>', 'id="why"',
        'class="benefits cards"', 'id="build"', 'class="numbered"', 'id="what"', 'class="flow"')]
    assert order == sorted(order)
    assert result.count('<section') == 3
    why, what = result.split('<section class="section" id="why">', 1)[1].split(
        '\n    <section class="section" id="what">')
    assert what == ('<div class="section-head"><h2>What are Smart Tools?</h2></div>'
                    f'<p class="about">{build.html.escape(build.ABOUT, quote=True)}</p>'
                    f'{graphics.flow_diagram(build.TEXT["diagram"])}</section>')
    assert result.count('class="about"') == 1
    assert '\n.about {\n' in (SITE/'theme/style.css').read_text(encoding='utf-8')
    assert why.startswith('<div class="section-head"><h2>Why Smart Tools?</h2></div>'
                          '<div class="benefits cards"><div><span class="tile" style="--swatch:var(--tint-blue)">')
    assert page.ids['build']['class'] == 'build'
    conformance = 'https://github.com/microsoft/amplifier-smart-tools/tree/main/conformance'
    steps = ''.join(f'<li><h3>{title}</h3></li>' for title in build.BUILD_STEPS)
    assert why.endswith(
        '</div><div class="build" id="build"><div><h3>Package what<br>you know.</h3>'
        f'<div class="actions">{build.text_link("Read the specification", build.SPEC)}'
        f'{build.text_link("Run the conformance kit", conformance)}</div></div>'
        f'<ol class="numbered">{steps}</ol></div></section>')
    assert page.link('Read the specification') == build.SPEC
    assert page.link('Run the conformance kit') == conformance
    assert not page.duplicate_ids


@pytest.mark.parametrize('local,owner,catalog_url', [
    (False, None, CATALOG_URL),
    (False, 'robotdad', 'https://robotdad.github.io/amplifier-smart-tools-catalog/'),
    (True, None, '/amplifier-smart-tools-catalog/'),
])
def test_overview_featured_cards_link_to_catalog_tool_pages(tmp_path, local, owner, catalog_url):
    featured = [
        {'slug': 'reality-check', 'name': 'Reality Check', 'tagline': 'Tests your app by using it.'},
        {'slug': 'unknown-tool', 'name': '<b>Unknown</b>', 'tagline': 'Draws <i>its</i> initial.'},
    ]
    result = build.overview({'featured': featured}, SimpleNamespace(local=local, family_owner=owner), tmp_path)
    page = Page(result)
    assert slugs(page.cards) == ['reality-check', 'unknown-tool']
    assert [card['class'] for card in page.cards] == ['tool-card wide art', 'tool-card wide']
    assert f'style="--field:{graphics.TILE}"' in result
    assert graphics.ARTWORK['reality-check'] in result
    assert [card['links'] for card in page.cards] == [
        [f'{catalog_url}tools/reality-check/'] * 2, [f'{catalog_url}tools/unknown-tool/'] * 2]
    assert 'Tests your app by using it.' in page.cards[0]['text']
    assert '<b>Unknown</b>' not in result and '<i>its</i>' not in result
    assert 'Start with these.' in result
    assert page.link('Browse all tools') == catalog_url
    order = [result.index(marker) for marker in (
        'id="get-started"', 'Start with these.', 'id="why"', 'class="benefits cards"', 'id="build"',
        'id="what"', 'class="flow"')]
    assert order == sorted(order)
    assert result.count('<section') == 4
    assert not page.duplicate_ids


@pytest.mark.parametrize('slug', ['', 'Reality-Check', 'reality_check', 'a--b', '-a', 'a-',
                                  'a b', 'a/b', '../escape', 'tool?page=1', 'tool#top', 'tool\n'])
def test_overview_rejects_featured_slug_that_is_not_a_catalog_directory_name(tmp_path, slug):
    featured = [{'slug': slug, 'name': 'Fixture', 'tagline': 'Fixture tagline.'}]
    with pytest.raises(ValueError, match='Featured slug'):
        build.overview({'featured': featured}, ARGS, tmp_path)


def test_overview_orders_hero_featured_why_and_what(tmp_path):
    post(tmp_path, 'fixture')
    config = {'featured': [{'slug': 'fixture-tool', 'name': 'Fixture', 'tagline': 'Fixture tagline.'}],
              'news': [{'date': '2026-11-13', 'label': 'Release', 'title': 'Fixture Tool 1.0'}]}
    result = build.overview(config, ARGS, tmp_path)
    assert re.findall(r'<section class="([^"]+)"(?: id="([^"]+)")?>', result) == [
        ('hero', ''), ('section', ''), ('section', 'why'), ('section', 'what')]
    assert result.count('<section') == result.count('</section>') == 4
    assert re.findall(r'<h[12][^>]*>(.*?)</h[12]>', result) == [
        'Expertise, built<br>into the tool.', "What's new", 'Start with these.', 'Why Smart Tools?',
        'What are Smart Tools?']
    hero = result.split('</section>', 1)[0]
    news = build.news(config, tmp_path, CATALOG_URL)
    assert news.count('<li>') == 2
    assert hero.endswith(f'</div>\n    </div>{news}</div>')
    assert result.count('<aside') == result.count('class="news"') == 1
    assert not Page(result).duplicate_ids


@pytest.mark.parametrize('config', [OVERVIEW, dict(OVERVIEW, featured=[], news=[])])
def test_overview_llms_without_featured_tools_or_posts(tmp_path, config):
    assert build.CHAPTERS == [
        ('README', 'Introduction'), ('structure', 'Structure'), ('manifest', 'Manifest'),
        ('invocation', 'Invocation'), ('packaging', 'Packaging'), ('examples', 'Examples')]
    assert build.overview_llms(config, ARGS, tmp_path) == overview_llms()
    assert list(llms_sections(overview_llms())) == ['Specification', 'Catalog', 'Optional']


@pytest.mark.parametrize('local,owner,overview_url,catalog_url', MODES)
def test_overview_llms_lists_featured_tools_and_posts_newest_first(tmp_path, local, owner, overview_url, catalog_url):
    post(tmp_path, 'alpha', POST.replace('2026-11-16', '2026-11-05').replace('Fixture', 'Alpha'))
    post(tmp_path, 'bravo', POST.replace('Fixture post', '\u201cBravo\u201d post').replace('Fixture', 'Bravo'))
    config = dict(OVERVIEW, featured=[
        {'slug': 'reality-check', 'name': 'Reality Check', 'tagline': 'Tests your app by using it.'},
        {'slug': 'fixture-tool', 'name': 'Fixture Tool', 'tagline': 'Fixture tagline.'}],
        news=[{'date': '2026-11-13', 'label': 'Release', 'title': 'Fixture Tool 1.0'}])
    before = copy.deepcopy(config)
    result = build.overview_llms(config, SimpleNamespace(local=local, family_owner=owner), tmp_path)
    assert result == overview_llms(
        overview_url, catalog_url,
        tools=(f'- [Reality Check]({catalog_url}tools/reality-check/index.md): Tests your app by using it.\n'
               f'- [Fixture Tool]({catalog_url}tools/fixture-tool/index.md): Fixture tagline.\n'),
        blog=('\n## Blog\n\n'
              f'- ["Bravo" post]({overview_url}blog/bravo/index.md): Bravo summary.\n'
              f'- [Alpha post]({overview_url}blog/alpha/index.md): Alpha summary.\n'))
    assert config == before
    assert 'Fixture Tool 1.0' not in result


def test_llms_files_follow_the_llms_txt_layout(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'alpha', snapshot=False)
    entry(tmp_path, 'zulu', LISTING)
    post(tmp_path, 'fixture')
    featured = [{'slug': 'zulu', 'name': 'Zulu', 'tagline': 'Fixture tagline.'}]
    catalog = llms_sections(build.catalog_llms(CATALOG, ARGS, tmp_path))
    overview = llms_sections(build.overview_llms(dict(OVERVIEW, featured=featured), ARGS, tmp_path))
    assert {title: [name for name, _, _ in items] for title, items in catalog.items()} == {
        'Recommended': ['Zulu'], 'Test environments': ['Zulu'], 'Other': ['Alpha']}
    assert {title: [name for name, _, _ in items] for title, items in overview.items()} == {
        'Specification': [label for _, label in build.CHAPTERS], 'Catalog': ['All tools', 'Zulu'],
        'Blog': ['Fixture post'], 'Optional': ['Source repository', 'Conformance kit']}
    assert all(notes for _, _, notes in [*sum(catalog.values(), []), *overview['Catalog'], *overview['Blog']])
    assert all(notes is None for _, _, notes in overview['Specification'] + overview['Optional'])
    assert overview['Catalog'][:2] == [
        ('All tools', f'{CATALOG_URL}llms.txt', 'Every listed tool, by category'),
        catalog['Recommended'][0][:2] + ('Fixture tagline.',)]


def test_news_lists_site_entries_and_blog_posts_newest_first(tmp_path):
    post(tmp_path, 'alpha', POST.replace('2026-11-16', '2026-11-05').replace('Fixture', 'Alpha'))
    post(tmp_path, 'bravo', POST.replace('2026-11-16', '2026-12-25').replace('Fixture', 'Bravo'))
    config = {'news': [
        {'date': '2026-11-03', 'label': 'Release', 'title': 'Fixture Tool 1.0', 'tool': 'fixture-tool'},
        {'date': '2026-11-16', 'label': 'Welcome', 'title': 'Welcome to the fixture'},
        {'date': '2025-12-31', 'label': 'Release', 'title': 'Fixture Tool 0.9', 'tool': 'fixture-tool'},
    ]}
    before = copy.deepcopy(config)
    assert build.news(config, tmp_path, CATALOG_URL) == news_list(
        news_row('2026-12-25', 'Dec 25, 2026', 'Blog', 'Bravo post', './blog/bravo/'),
        news_row('2026-11-16', 'Nov 16, 2026', 'Welcome', 'Welcome to the fixture'),
        news_row('2026-11-05', 'Nov 5, 2026', 'Blog', 'Alpha post', './blog/alpha/'),
        news_row('2026-11-03', 'Nov 3, 2026', 'Release', 'Fixture Tool 1.0', f'{CATALOG_URL}tools/fixture-tool/'),
        news_row('2025-12-31', 'Dec 31, 2025', 'Release', 'Fixture Tool 0.9', f'{CATALOG_URL}tools/fixture-tool/'))
    assert config == before


def test_news_on_one_date_lists_site_entries_before_blog_posts(tmp_path):
    post(tmp_path, 'alpha', POST.replace('Fixture', 'Alpha'))
    post(tmp_path, 'bravo', POST.replace('Fixture', 'Bravo'))
    config = {'news': [{'date': '2026-11-16', 'label': 'Welcome', 'title': 'First entry'},
                       {'date': '2026-11-17', 'label': 'Release', 'title': 'Newer entry'},
                       {'date': '2026-11-16', 'label': 'Release', 'title': 'Second entry'}]}
    assert build.news(config, tmp_path, CATALOG_URL) == news_list(
        news_row('2026-11-17', 'Nov 17, 2026', 'Release', 'Newer entry'),
        news_row('2026-11-16', 'Nov 16, 2026', 'Welcome', 'First entry'),
        news_row('2026-11-16', 'Nov 16, 2026', 'Release', 'Second entry'),
        news_row('2026-11-16', 'Nov 16, 2026', 'Blog', 'Bravo post', './blog/bravo/'),
        news_row('2026-11-16', 'Nov 16, 2026', 'Blog', 'Alpha post', './blog/alpha/'))


def test_news_shows_at_most_five_items(tmp_path):
    entries = [{'date': f'2026-10-0{day}', 'label': 'Release', 'title': f'Entry {day}'} for day in range(1, 5)]
    for day in (5, 6, 7):
        post(tmp_path, f'post-{day}', POST.replace('2026-11-16', f'2026-09-0{day}').replace('Fixture', f'Post {day}'))
    assert build.news({'news': entries}, tmp_path, CATALOG_URL) == news_list(
        *(news_row(f'2026-10-0{day}', f'Oct {day}, 2026', 'Release', f'Entry {day}') for day in (4, 3, 2, 1)),
        news_row('2026-09-07', 'Sep 7, 2026', 'Blog', 'Post 7 post', './blog/post-7/'))
    assert build.news({'news': entries[:2]}, tmp_path, CATALOG_URL).count('<li>') == 5
    assert build.news({'news': entries[:1]}, tmp_path, CATALOG_URL).count('<li>') == 4
    assert build.news({}, tmp_path, CATALOG_URL) == news_list(
        *(news_row(f'2026-09-0{day}', f'Sep {day}, 2026', 'Blog', f'Post {day} post', f'./blog/post-{day}/')
          for day in (7, 6, 5)))


@pytest.mark.parametrize('config', [{}, {'news': []}])
def test_overview_without_news_or_posts_has_no_news_list(tmp_path, config):
    assert build.news(config, tmp_path, CATALOG_URL) == ''
    result = build.overview(config, ARGS, tmp_path)
    for absent in ('<aside', 'class="news', "What's new", '<time', '<ol class="news-list">'):
        assert absent not in result
    assert '</div>\n    </div></div></section>' in result


@pytest.mark.parametrize('local,owner,catalog_url', [
    (False, None, CATALOG_URL),
    (False, 'robotdad', 'https://robotdad.github.io/amplifier-smart-tools-catalog/'),
    (True, None, '/amplifier-smart-tools-catalog/'),
])
def test_overview_news_tool_entry_links_to_its_catalog_page(tmp_path, local, owner, catalog_url):
    config = {'news': [{'date': '2026-11-13', 'label': 'Release', 'title': 'Reality Check 0.9.1', 'tool': 'reality-check'},
                       {'date': '2026-11-03', 'label': 'Welcome', 'title': 'Welcome'}]}
    result = build.overview(config, SimpleNamespace(local=local, family_owner=owner), tmp_path)
    page = Page(result)
    assert news_list(
        news_row('2026-11-13', 'Nov 13, 2026', 'Release', 'Reality Check 0.9.1', f'{catalog_url}tools/reality-check/'),
        news_row('2026-11-03', 'Nov 3, 2026', 'Welcome', 'Welcome')) in result
    assert page.link('Reality Check 0.9.1') == f'{catalog_url}tools/reality-check/'
    assert 'Welcome' not in [anchor['text'] for anchor in page.links]
    assert not page.duplicate_ids


@pytest.mark.parametrize('slug', ['', 'Reality-Check', 'reality_check', 'a--b', '-a', 'a-', 'a b', 'a/b',
                                  '../escape', 'tool?page=1', 'tool#top', 'tool\n', 'https://example.com/'])
def test_news_rejects_tool_that_is_not_a_catalog_directory_name(tmp_path, slug):
    item = {'date': '2026-11-16', 'label': 'Release', 'title': 'Fixture', 'tool': slug}
    with pytest.raises(ValueError, match='News tool must be a catalog directory name'):
        build.news({'news': [item]}, tmp_path, CATALOG_URL)
    with pytest.raises(ValueError, match='News tool'):
        build.overview({'news': [item]}, ARGS, tmp_path)


@pytest.mark.parametrize('value', ['', 'November 16, 2026', '16/11/2026', '2026-11', '2026-1-5', '2026-13-01',
                                   '2026-02-30', '2026-11-16T10:00:00', ' 2026-11-16', '20261116', '2026-W47-1', 20261116])
def test_news_rejects_date_that_is_not_a_date(tmp_path, value):
    item = {'date': value, 'label': 'Release', 'title': 'Fixture'}
    with pytest.raises(ValueError):
        build.news({'news': [item]}, tmp_path, CATALOG_URL)


def test_news_text_is_escaped(tmp_path):
    post(tmp_path, 'fixture', POST.replace('Fixture post', "'<b>Post</b> & more'"))
    item = {'date': '2026-11-17', 'label': '<i>Label</i>', 'title': '<script>title()</script> & "more"'}
    assert build.news({'news': [item]}, tmp_path, CATALOG_URL) == news_list(
        news_row('2026-11-17', 'Nov 17, 2026', '&lt;i&gt;Label&lt;/i&gt;',
                 '&lt;script&gt;title()&lt;/script&gt; &amp; &quot;more&quot;'),
        news_row('2026-11-16', 'Nov 16, 2026', 'Blog', '&lt;b&gt;Post&lt;/b&gt; &amp; more', './blog/fixture/'))


def test_blog_posts_read_front_matter_newest_first(tmp_path):
    post(tmp_path, 'alpha', POST.replace('2026-11-16', '2026-03-05'))
    directory = post(tmp_path, 'bravo', POST.replace('summary:', 'affiliation: Fixture Team\nsummary:'))
    post(tmp_path, 'charlie', POST.replace('2026-11-16', '2025-12-31'))
    posts = build.blog_posts(tmp_path)
    assert [item['slug'] for item in posts] == ['bravo', 'alpha', 'charlie']
    assert [item['date'] for item in posts] == [date(2026, 11, 16), date(2026, 3, 5), date(2025, 12, 31)]
    assert posts[0] == {
        'slug': 'bravo', 'directory': directory, 'body': 'Fixture body.\n', 'title': 'Fixture post',
        'date': date(2026, 11, 16), 'author': 'Fixture Author', 'summary': 'Fixture summary.',
        'affiliation': 'Fixture Team'}
    assert posts[1]['affiliation'] == ''


def test_blog_without_posts_writes_nothing(tmp_path):
    assert build.blog_posts(tmp_path) == []
    (tmp_path/'site/blog/drafts').mkdir(parents=True)
    (tmp_path/'site/blog/post.md').write_text(POST, encoding='utf-8')
    assert build.blog_posts(tmp_path) == []
    build_blog(tmp_path)
    assert not (tmp_path/'generated').exists()


@pytest.mark.parametrize('slug', ['Fixture', 'fixture_post', 'fixture.post', 'a--b', '-a', 'a-', 'a b'])
def test_blog_rejects_post_directory_that_is_not_a_lowercase_slug(tmp_path, slug):
    post(tmp_path, slug)
    with pytest.raises(ValueError, match='post directory must be a lowercase slug'):
        build.blog_posts(tmp_path)


@pytest.mark.parametrize('text', [
    'Fixture body.\n',
    POST.removeprefix('---\n'),
    'Fixture preface.\n' + POST,
    '---\ntitle: Fixture post\n',
])
def test_blog_rejects_post_that_does_not_start_with_front_matter(tmp_path, text):
    post(tmp_path, 'fixture', text)
    with pytest.raises(ValueError, match='fixture: post must start with front matter'):
        build.blog_posts(tmp_path)


@pytest.mark.parametrize('key', ['title', 'date', 'author', 'summary'])
def test_blog_rejects_front_matter_without_a_required_key(tmp_path, key):
    post(tmp_path, 'fixture', re.sub(rf'^{key}: .*\n', '', POST, flags=re.MULTILINE))
    with pytest.raises(ValueError, match='fixture: front matter needs title, date, author, and summary'):
        build.blog_posts(tmp_path)


@pytest.mark.parametrize('front_matter', ['', '- title\n- date\n- author\n- summary\n', 'Fixture post\n'])
def test_blog_rejects_front_matter_that_is_not_a_mapping(tmp_path, front_matter):
    post(tmp_path, 'fixture', f'---\n{front_matter}---\nFixture body.\n')
    with pytest.raises(ValueError, match='fixture: front matter needs title, date, author, and summary'):
        build.blog_posts(tmp_path)


@pytest.mark.parametrize('value', ['November 16, 2026', '"2026-11-16"', '20261116', '2026-11',
                                   '16/11/2026', '[2026, 11, 16]'])
def test_blog_rejects_date_that_is_not_a_date(tmp_path, value):
    post(tmp_path, 'fixture', POST.replace('date: 2026-11-16', f'date: {value}'))
    with pytest.raises(ValueError, match='fixture: date must be written as YYYY-MM-DD'):
        build.blog_posts(tmp_path)


@pytest.mark.parametrize('source', ['missing.png', 'images', 'images/figure.png', '../figure.png',
                                    'https://example.com/figure.png'])
def test_blog_rejects_image_that_is_not_a_file_beside_the_post(tmp_path, source):
    directory = post(tmp_path, 'fixture', POST + f'\n![Figure]({source})\n', {'figure.png': PNG})
    (directory/'images').mkdir()
    for existing in (directory/'images/figure.png', directory.parent/'figure.png'):
        existing.write_bytes(PNG)
    with pytest.raises(ValueError, match='fixture: an image must be a file beside the post'):
        build_blog(tmp_path)


@pytest.mark.parametrize('body', ['Inline ![Figure](figure.png) image.', '[![Figure](figure.png)](https://example.com/)',
                                  '![Figure](figure.png)\n*Caption on the next line.*'])
def test_blog_rejects_image_that_shares_its_paragraph(tmp_path, body):
    post(tmp_path, 'fixture', POST + f'\n{body}\n', {'figure.png': PNG})
    with pytest.raises(ValueError, match='fixture: an image must stand alone in its paragraph'):
        build_blog(tmp_path)


def test_blog_rejects_front_matter_that_is_not_yaml(tmp_path):
    post(tmp_path, 'fixture', POST.replace('title: Fixture post', 'title: [unclosed'))
    with pytest.raises(ValueError, match='fixture: front matter is not valid YAML'):
        build.blog_posts(tmp_path)


@pytest.mark.parametrize('key', ['title', 'date', 'author', 'summary'])
def test_blog_rejects_front_matter_with_an_empty_value(tmp_path, key):
    post(tmp_path, 'fixture', re.sub(rf'^{key}: .*$', f'{key}:', POST, flags=re.MULTILINE))
    with pytest.raises(ValueError, match='fixture: front matter needs title, date, author, and summary'):
        build.blog_posts(tmp_path)


def test_blog_rejects_date_with_a_time(tmp_path):
    post(tmp_path, 'fixture', POST.replace('date: 2026-11-16', 'date: 2026-11-16 10:00:00'))
    with pytest.raises(ValueError, match='fixture: date must be written as YYYY-MM-DD'):
        build.blog_posts(tmp_path)


def test_post_image_name_may_hold_a_space(tmp_path):
    post(tmp_path, 'fixture', POST + '\n![Figure](<my figure.png>)\n', {'my figure.png': PNG})
    assert '<img src="./my%20figure.png" alt="Figure" width="640" height="480" loading="lazy">' in post_page(tmp_path)
    assert (tmp_path/'generated/blog/fixture/my figure.png').read_bytes() == PNG


def test_post_caption_is_one_italic_run(tmp_path):
    post(tmp_path, 'fixture', POST + '\n![Figure](figure.png)\n\n*one* and *two*\n', {'figure.png': PNG})
    content = post_content(post_page(tmp_path))
    assert '<figcaption' not in content
    assert '<p><em>one</em> and <em>two</em></p>' in content


@pytest.mark.parametrize('content', [PNG[:8], PNG[:20], GIF[:8], PNG[:16] + bytes(8)])
def test_image_size_is_unknown_for_a_cut_or_empty_header(tmp_path, content):
    image = tmp_path/'image'
    image.write_bytes(content)
    assert build.image_size(image) is None


def test_build_blog_writes_the_index_and_one_page_per_post(tmp_path):
    post(tmp_path, 'alpha', POST.replace('2026-11-16', '2026-03-05').replace('Fixture', 'Alpha'))
    post(tmp_path, 'bravo', POST.replace('Fixture', 'Bravo') + '\n![Figure](figure.png)\n',
         {'figure.png': PNG})
    post(tmp_path, 'charlie', POST.replace('2026-11-16', '2025-12-31').replace('Fixture', 'Charlie'))
    out = tmp_path/'generated'
    config = dict(OVERVIEW)
    build.build_blog(tmp_path, out, ARGS, config)
    assert config == OVERVIEW
    assert sorted(path.relative_to(out).as_posix() for path in out.rglob('*') if path.is_file()) == [
        'blog/alpha/index.html', 'blog/alpha/index.md', 'blog/bravo/figure.png', 'blog/bravo/index.html',
        'blog/bravo/index.md', 'blog/charlie/index.html', 'blog/charlie/index.md', 'blog/index.html']
    assert (out/'blog/bravo/index.md').read_text(encoding='utf-8') == (
        '# Bravo post\n\nNovember 16, 2026\nWritten by Bravo Author\n\nBravo body.\n\n'
        f'![Figure]({OVERVIEW_URL}blog/bravo/figure.png)\n')
    assert (out/'blog/charlie/index.md').read_text(encoding='utf-8') == (
        '# Charlie post\n\nDecember 31, 2025\nWritten by Charlie Author\n\nCharlie body.\n')

    index = (out/'blog/index.html').read_text(encoding='utf-8')
    assert index.startswith('<!doctype html>')
    assert '<title>Blog | Amplifier Smart Tools</title>' in index
    assert ('<meta name="description" content="Posts about building and using Amplifier Smart Tools.">'
            in index)
    assert './assets/' not in index.replace('../assets/', '')
    rows = index.split('<main class="wrap" id="main"><section class="catalog-hero"><h1>Blog</h1></section>'
                       '<div class="post-list">', 1)[1].split('</div></main>', 1)[0]
    listed = re.findall(r'<article class="post-row"><p class="post-date">(.*?)</p><div><h2>'
                        r'<a href="(.*?)">(.*?)</a></h2><p>(.*?)</p></div></article>', rows)
    assert listed == [('November 16, 2026', './bravo/', 'Bravo post', 'Bravo summary.'),
                      ('March 5, 2026', './alpha/', 'Alpha post', 'Alpha summary.'),
                      ('December 31, 2025', './charlie/', 'Charlie post', 'Charlie summary.')]
    assert rows.count('<article') == len(listed)

    bravo = (out/'blog/bravo/index.html').read_text(encoding='utf-8')
    assert bravo.startswith('<!doctype html>')
    assert '<title>Bravo post | Amplifier Smart Tools</title>' in bravo
    assert '<meta name="description" content="Bravo summary.">' in bravo
    assert './assets/' not in bravo.replace('../../assets/', '')
    described = f'<link rel="describedby" type="text/plain" href="{OVERVIEW_URL}llms.txt">'
    assert (f'<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">{ALTERNATE}{described}'
            '<link rel="stylesheet" href="../../assets/style.css">') in bravo
    assert (f'<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">{described}'
            '<link rel="stylesheet" href="../assets/style.css">') in index
    assert 'rel="alternate"' not in index and 'data-copy-markdown' not in index
    for page, prefix in ((index, '../assets/'), (bravo, '../../assets/')):
        for asset in ('favicon.svg', 'style.css', 'site.js'):
            assert f'="{prefix}{asset}"' in page
        assert f'<a href="{OVERVIEW_URL}blog/" aria-current="page">Blog</a>' in page
        assert page.count('aria-current') == 1
        assert not Page(page).duplicate_ids


def test_post_page_has_a_header_with_facts_and_a_way_back(tmp_path):
    post(tmp_path, 'fixture', POST.replace('2026-11-16', '2026-03-05')
         .replace('summary:', 'affiliation: Fixture Team\nsummary:'))
    post(tmp_path, 'unaffiliated')
    blog = build_blog(tmp_path)
    page = (blog/'fixture/index.html').read_text(encoding='utf-8')
    assert ('<main class="wrap" id="main"><article class="reader-content post">'
            '<header class="post-header"><p class="eyebrow"><a href="../">Blog</a></p>'
            '<h1>Fixture post</h1><div class="post-meta copy-region"><dl class="facts">') in page
    assert list(facts(page).items()) == [
        ('Published', 'March 5, 2026'), ('Author', 'Fixture Author'),
        ('Affiliation', 'Fixture Team'), ('Reading time', '1 min read')]
    assert ('</dl><a class="copy-markdown" href="./index.md" data-copy-markdown>'
            f'{graphics.icon("copy", 14)}{graphics.icon("check", 14)}Copy as Markdown</a>'
            '<p class="visually-hidden" role="status" aria-live="polite"></p></div></header>'
            '<p>Fixture body.</p>\n<nav class="reader-pagination" aria-label="Blog">'
            '<a class="text-link" href="../">All posts</a></nav></article></main>') in page
    assert page.count('<article') == page.count('<h1>') == 1
    assert page.count('data-copy-markdown') == page.count('role="status"') == page.count(ALTERNATE) == 1
    assert Page(page).link('Copy as Markdown') == './index.md'
    assert (blog/'fixture/index.md').is_file() and (blog/'unaffiliated/index.md').is_file()
    script = (SITE/'theme/site.js').read_text(encoding='utf-8')
    for hook in ('[data-copy-markdown]', '.copy-region', '[role="status"]', "'data-copied'"):
        assert hook in script
    css = (SITE/'theme/style.css').read_text(encoding='utf-8')
    for rule in ('.post-meta {', '.post-meta .facts {', '.copy-markdown {', '.copy-markdown[data-copied] .icon + .icon {',
                 '@keyframes copied {'):
        assert f'\n{rule}\n' in css
    unaffiliated = (blog/'unaffiliated/index.html').read_text(encoding='utf-8')
    assert list(facts(unaffiliated).items()) == [
        ('Published', 'November 16, 2026'), ('Author', 'Fixture Author'), ('Reading time', '1 min read')]
    assert 'Affiliation' not in unaffiliated


def test_post_markdown_has_a_title_a_byline_and_the_body(tmp_path):
    body = '\nBefore \u2014 after.\n\n![A screenshot](shot.png)\n\n*The caption.*\n\n'
    post(tmp_path, 'fixture', POST.replace('2026-11-16', '2026-03-05')
         .replace('summary:', 'affiliation: Fixture Team\nsummary:').replace('Fixture body.\n', body), {'shot.png': PNG})
    post(tmp_path, 'unaffiliated', POST.replace('Fixture post', 'Fixture\u2019s post'))
    unaffiliated, affiliated = build.blog_posts(tmp_path)
    address = 'https://microsoft.github.io/amplifier-smart-tools/blog/'
    assert build.post_markdown(affiliated, 'March 5, 2026', f'{address}fixture/') == (
        '# Fixture post\n\nMarch 5, 2026\nWritten by Fixture Author\nFixture Team\n\n'
        f'Before  -  after.\n\n![A screenshot]({address}fixture/shot.png)\n\n*The caption.*\n')
    assert build.post_markdown(unaffiliated, 'November 16, 2026', f'{address}unaffiliated/') == (
        "# Fixture's post\n\nNovember 16, 2026\nWritten by Fixture Author\n\nFixture body.\n")
    elsewhere = dict(affiliated, body='![Elsewhere](https://example.test/shot.png)\n\n![Missing](missing.png)\n')
    assert build.post_markdown(elsewhere, 'March 5, 2026', f'{address}fixture/').endswith(
        '\n\n![Elsewhere](https://example.test/shot.png)\n\n![Missing](missing.png)\n')
    blog = build_blog(tmp_path)
    assert (blog/'fixture/index.md').read_text(encoding='utf-8') == build.post_markdown(
        affiliated, 'March 5, 2026', f'{address}fixture/')
    assert (blog/'unaffiliated/index.md').read_text(encoding='utf-8') == build.post_markdown(
        unaffiliated, 'November 16, 2026', f'{address}unaffiliated/')
    assert (blog/'fixture/shot.png').read_bytes() == PNG


@pytest.mark.parametrize('words,minutes', [(0, 1), (114, 1), (460, 2), (700, 3)])
def test_post_reading_time_is_whole_minutes_and_at_least_one(tmp_path, words, minutes):
    post(tmp_path, 'fixture', POST.replace('Fixture body.', ' '.join(['word'] * words)))
    assert facts(post_page(tmp_path))['Reading time'] == f'{minutes} min read'


def test_post_image_alone_in_a_paragraph_becomes_a_figure_beside_the_page(tmp_path):
    files = {'shot.png': PNG, 'demo.gif': GIF, 'drawing.svg': b'<svg xmlns="http://www.w3.org/2000/svg"/>'}
    body = ('Before.\n\n![A screenshot](shot.png)\n\n*The caption with `code`.*\n\nBetween.\n\n'
            '![A demo](demo.gif)\n\nAfter *the* demo.\n\n![A drawing](drawing.svg)\n')
    post(tmp_path, 'fixture', POST.replace('Fixture body.\n', body), files)
    blog = build_blog(tmp_path)
    page = (blog/'fixture/index.html').read_text(encoding='utf-8')
    assert post_content(page) == (
        '<p>Before.</p>\n'
        '<figure><div class="product-image"><img src="./shot.png" alt="A screenshot" width="640" '
        'height="480" loading="lazy"></div><figcaption class="image-caption">The caption with '
        '<code>code</code>.</figcaption></figure>'
        '<p>Between.</p>\n'
        '<figure><div class="product-image"><img src="./demo.gif" alt="A demo" width="320" '
        'height="200" loading="lazy"></div></figure>'
        '<p>After <em>the</em> demo.</p>\n'
        '<figure><div class="product-image"><img src="./drawing.svg" alt="A drawing" '
        'loading="lazy"></div></figure>')
    assert sorted(path.name for path in (blog/'fixture').iterdir()) == sorted([*files, 'index.html', 'index.md'])
    for name, content in files.items():
        assert (blog/'fixture'/name).read_bytes() == content


@pytest.mark.parametrize('content,size', [
    (PNG, (640, 480)),
    (GIF, (320, 200)),
    (GIF.replace(b'GIF89a', b'GIF87a'), (320, 200)),
    (b'<svg xmlns="http://www.w3.org/2000/svg"/>', None),
    (b'', None),
])
def test_image_size_reads_png_and_gif_headers(tmp_path, content, size):
    image = tmp_path/'image'
    image.write_bytes(content)
    assert build.image_size(image) == size


def test_post_text_is_escaped_and_raw_html_is_not_passed_through(tmp_path):
    post(tmp_path, 'fixture', '''---
title: '<b>Title</b> & "more"'
date: 2026-11-16
author: <i>Author</i>
affiliation: <u>Team</u>
summary: <script>summary()</script>
---
<script>body()</script>

A <b onclick="bad">bold</b> word.

![<img onerror="bad">](shot.png)
''', {'shot.png': PNG})
    blog = build_blog(tmp_path)
    page = (blog/'fixture/index.html').read_text(encoding='utf-8')
    index = (blog/'index.html').read_text(encoding='utf-8')
    title = '&lt;b&gt;Title&lt;/b&gt; &amp; &quot;more&quot;'
    summary = '&lt;script&gt;summary()&lt;/script&gt;'
    for rendered in (page, index):
        for raw in ('<b>', '<i>', '<u>', '<script>summary', '<script>body', '<b onclick',
                    '<img onerror', '"more"'):
            assert raw not in rendered
    assert f'<title>{title} | Amplifier Smart Tools</title>' in page
    assert f'<meta property="og:title" content="{title} | Amplifier Smart Tools">' in page
    assert f'<meta name="description" content="{summary}">' in page
    assert f'<h1>{title}</h1>' in page
    assert facts(page)['Author'] == '&lt;i&gt;Author&lt;/i&gt;'
    assert facts(page)['Affiliation'] == '&lt;u&gt;Team&lt;/u&gt;'
    assert post_content(page) == (
        '<p>&lt;script&gt;body()&lt;/script&gt;</p>\n'
        '<p>A &lt;b onclick=&quot;bad&quot;&gt;bold&lt;/b&gt; word.</p>\n'
        '<figure><div class="product-image"><img src="./shot.png" '
        'alt="&lt;img onerror=&quot;bad&quot;&gt;" width="640" height="480" loading="lazy"></div></figure>')
    assert f'<h2><a href="./fixture/">{title}</a></h2><p>{summary}</p>' in index


def test_blog_guidance_matches_the_renderer(tmp_path):
    section = (SITE/'README.md').read_text(encoding='utf-8').split('\n## Blog\n', 1)[1].split('\n## ', 1)[0]
    guidance = ' '.join(section.split())
    for sentence in (
        'Each post is a directory at `site/blog/<slug>/` with a `post.md` and its images beside it.',
        '`post.md` starts with front matter, then the body in Markdown:',
        '`affiliation` is optional.',
        'The build writes the post list to `blog/index.html`, newest first, and each post to '
        '`blog/<slug>/index.html`.',
        'An image alone in a paragraph becomes a figure, and an italic line directly after it '
        'becomes the caption.',
        'Images must be files in the post directory.',
    ):
        assert sentence in guidance
    post(tmp_path, 'fixture', section.split('```\n', 2)[1] + 'Fixture body.\n')
    [example] = build.blog_posts(tmp_path)
    assert example['date'] == date(2026, 11, 16)
    assert example['affiliation'] == 'Team or organization'
    assert facts(post_page(tmp_path)).keys() == {'Published', 'Author', 'Affiliation', 'Reading time'}


@pytest.mark.parametrize('link,published', [
    ('manifest.md', './manifest.md'),
    ('./manifest.md', './manifest.md'),
    ('invocation.md#exit-codes', './invocation.md#exit-codes'),
    ('README.md', './index.md'),
    ('./README.md#parts', './index.md#parts'),
    ('../ROADMAP.md', 'https://github.com/microsoft/amplifier-smart-tools/blob/main/ROADMAP.md'),
    ('../conformance/README.md#run',
     'https://github.com/microsoft/amplifier-smart-tools/blob/main/conformance/README.md#run'),
    ('notes.md', 'https://github.com/microsoft/amplifier-smart-tools/blob/main/spec/notes.md'),
    ('https://example.com/manifest.md', 'https://example.com/manifest.md'),
    ('//example.com/manifest.md', '//example.com/manifest.md'),
    ('#parts', '#parts'),
    ('missing.md', 'missing.md'),
    ('../missing/README.md#run', '../missing/README.md#run'),
    ('../conformance/', 'https://github.com/microsoft/amplifier-smart-tools/tree/main/conformance'),
    ('../conformance#kit', 'https://github.com/microsoft/amplifier-smart-tools/tree/main/conformance#kit'),
    ('../../outside.md', '../../outside.md'),
])
def test_spec_markdown_links_resolve_from_the_published_copy(tmp_path, link, published):
    root = tmp_path/'repository'
    chapters(root, structure=f'# Structure\n\nRead [the *next* part]({link}) of the tool\u2019s layout.\n')
    for existing in (root/'ROADMAP.md', root/'conformance/README.md', root/'spec/notes.md', tmp_path/'outside.md'):
        existing.parent.mkdir(exist_ok=True)
        existing.write_text('Fixture file.\n', encoding='utf-8')
    assert build.spec_markdown(root, 'structure') == (
        f"# Structure\n\nRead [the *next* part]({published}) of the tool's layout.\n")


def test_build_reader_writes_a_markdown_copy_beside_every_chapter(tmp_path):
    chapters(tmp_path, README='# Fixture specification\n\nStart with [Structure](structure.md).\n',
             manifest='# Manifest\n\nBack to the [introduction](README.md#parts), or on to [Packaging](packaging.md).\n')
    out = tmp_path/'generated'
    out.mkdir()
    config = dict(OVERVIEW)
    build.build_reader(tmp_path, out, ARGS, config)
    assert config == OVERVIEW
    names = ['index', 'structure', 'manifest', 'invocation', 'packaging', 'examples']
    assert sorted(path.relative_to(out).as_posix() for path in out.rglob('*') if path.is_file()) == sorted(
        f'spec/{name}.{kind}' for name in names for kind in ('html', 'md'))
    assert (out/'spec/index.md').read_text(encoding='utf-8') == (
        '# Fixture specification\n\nStart with [Structure](./structure.md).\n')
    assert (out/'spec/manifest.md').read_text(encoding='utf-8') == (
        '# Manifest\n\nBack to the [introduction](./index.md#parts), or on to [Packaging](./packaging.md).\n')
    assert (out/'spec/examples.md').read_text(encoding='utf-8') == '# Examples\n'
    for name in names:
        page = (out/'spec'/f'{name}.html').read_text(encoding='utf-8')
        assert ('<link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">'
                f'<link rel="alternate" type="text/markdown" href="./{name}.md">'
                f'<link rel="describedby" type="text/plain" href="{OVERVIEW_URL}llms.txt">'
                '<link rel="stylesheet" href="../assets/style.css">') in page
        assert page.count('rel="alternate"') == 1
    # The page links to the rendered chapters, and its copy links to their copies.
    assert 'Start with <a href="./structure.html">Structure</a>.' in (out/'spec/index.html').read_text(encoding='utf-8')
    assert 'Back to the <a href="./index.html#parts">introduction</a>' in (
        out/'spec/manifest.html').read_text(encoding='utf-8')


def test_overview_llms_links_its_own_pages_to_files_the_build_writes(tmp_path):
    chapters(tmp_path)
    post(tmp_path, 'fixture')
    out = tmp_path/'generated'
    out.mkdir()
    build.build_reader(tmp_path, out, ARGS, OVERVIEW)
    build.build_blog(tmp_path, out, ARGS, OVERVIEW)
    links = llms_links(build.overview_llms(OVERVIEW, ARGS, tmp_path))
    own = [url.removeprefix(OVERVIEW_URL) for url in links if url.startswith(OVERVIEW_URL)]
    assert own == ['spec/index.md', 'spec/structure.md', 'spec/manifest.md', 'spec/invocation.md',
                   'spec/packaging.md', 'spec/examples.md', 'blog/fixture/index.md']
    assert all((out/copied).is_file() for copied in own)
    assert [url for url in links if not url.startswith(OVERVIEW_URL)] == [
        f'{CATALOG_URL}llms.txt', 'https://github.com/microsoft/amplifier-smart-tools',
        'https://github.com/microsoft/amplifier-smart-tools/tree/main/conformance']


def text_leaves(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from text_leaves(child, f'{path}.{key}'.lstrip('.'))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from text_leaves(child, f'{path}[{index}]')
    else:
        yield path, value


def test_every_text_entry_is_a_filled_string():
    leaves = dict(text_leaves(build.TEXT))
    assert leaves['overview.hero.headline[0]'] == 'Expertise, built'
    assert [path for path, value in leaves.items() if not isinstance(value, str) or not value.strip()] == []


def test_pages_show_the_text_file_wording_escaped(tmp_path, monkeypatch):
    registry(tmp_path)
    entry(tmp_path, 'tool', LISTING)
    monkeypatch.setitem(build.STORE, 'standfirst', 'Tools & <more> for "agents"')
    monkeypatch.setitem(build.STORE, 'search', 'Find "a" tool')
    monkeypatch.setitem(build.SHARED, 'get', 'Open')
    result = render(tmp_path)
    assert '<p class="standfirst">Tools &amp; &lt;more&gt; for "agents"</p>' in result
    assert 'placeholder="Find &quot;a&quot; tool" aria-label="Find &quot;a&quot; tool"' in result
    assert 'aria-label="Open Tool">Open</a>' in result
    assert 'Expert tools your agent can call.' not in result


def test_theme_sync_copies_every_theme_file_and_builds_catalog(tmp_path):
    registry(tmp_path)
    entry(tmp_path, 'tool', LISTING)
    post(tmp_path, 'fixture')
    write_json(tmp_path/'site'/'site.json', CATALOG)
    subprocess.run([sys.executable, str(SITE/'sync_theme.py'), str(tmp_path)], check=True)
    synced = {path.relative_to(tmp_path/'site/theme').as_posix()
              for path in (tmp_path/'site/theme').rglob('*') if path.is_file()}
    source = {path.relative_to(SITE/'theme').as_posix()
              for path in (SITE/'theme').rglob('*')
              if path.is_file() and '__pycache__' not in path.parts}
    assert synced == source
    assert {'build.py', 'graphics.py', 'catalog_metadata.py', 'family.json', 'text.yaml', 'LICENSE',
            'assets/fonts/instrument-sans-variable.woff2'} <= synced
    for name in synced:
        assert (tmp_path/'site/theme'/name).read_bytes() == (SITE/'theme'/name).read_bytes()
    out = tmp_path/'generated'
    subprocess.run([sys.executable, str(tmp_path/'site/theme/build.py'),
                    '--output', str(out)], check=True)
    catalog = (out/'index.html').read_text(encoding='utf-8')
    index = Page(catalog)
    assert slugs(index.cards) == ['tool']
    assert index.rows[0]['marks'] == ['app-icon', 'tag']
    assert recommended_names(catalog) == ['Tool']
    assert index.rows[0]['links'] == ['./tools/tool/'] * 2
    tool_page = (out/'tools/tool/index.html').read_text(encoding='utf-8')
    assert '<p class="status-pill">Recommended</p><h1>Tool</h1>' in tool_page
    described = f'<link rel="describedby" type="text/plain" href="{CATALOG_URL}llms.txt">'
    assert described in catalog and 'rel="alternate"' not in catalog
    assert f'{ALTERNATE}{described}' in tool_page
    assert (out/'tools/tool/index.md').read_text(encoding='utf-8') == listing_markdown(tmp_path, 'tool')
    llms = (out/'llms.txt').read_text(encoding='utf-8')
    assert llms == build.catalog_llms(CATALOG, ARGS, tmp_path)
    assert llms_links(llms) == [f'{CATALOG_URL}tools/tool/index.md'] * 2
    for filename in ('site.js', 'style.css'):
        assert (out/'assets'/filename).read_bytes() == (SITE/'theme'/filename).read_bytes()
    for font in (SITE/'theme/assets/fonts').iterdir():
        assert (out/'assets/fonts'/font.name).read_bytes() == font.read_bytes()
    assert (out/'assets/favicon.svg').read_text(encoding='utf-8') == graphics.FAVICON
    assert (out/'.nojekyll').is_file()
    assert not (out/'blog').exists()


def test_overview_spec_reader_and_blog_build_without_catalog_metadata(tmp_path):
    out = tmp_path/'overview'
    subprocess.run([sys.executable, str(SITE/'theme/build.py'), '--output', str(out)], check=True)
    index = (out/'index.html').read_text(encoding='utf-8')
    page = Page(index)
    config = json.loads((SITE/'site.json').read_text(encoding='utf-8'))
    assert slugs(page.cards) == [item['slug'] for item in config['featured']]
    assert all(card['links'] == [f'{CATALOG_URL}tools/{card["data-tool"]}/'] * 2 for card in page.cards)
    assert 'category-chips' not in page.ids and 'tool-search' not in page.ids
    for item in config['news']:
        assert item.keys() - {'tool'} == {'date', 'label', 'title'}
        assert date.fromisoformat(item['date']).isoformat() == item['date']
        assert item['label'].strip() and item['title'].strip()
    news = build.news(config, SITE.parent, CATALOG_URL)
    assert 1 <= news.count('<li>') == min(5, len(config['news']) + len(build.blog_posts(SITE.parent)))
    assert f'{news}</div></section>' in index
    assert index.count('<aside class="news"') == 1
    assert not page.duplicate_ids
    assert not (out/'tools').exists()
    chapters = [path.read_text(encoding='utf-8') for path in (out/'spec').glob('*.html')]
    assert len(chapters) == 6
    for chapter in chapters:
        assert chapter.count('class="reader-toc"') == 1
        sidebar, content = chapter.split('<aside class="reader-sidebar">', 1)[1].split('</aside>', 1)
        assert 'reader-toc' not in sidebar
        assert content.startswith('<details class="reader-toc" open><summary>On this page</summary>'
                                  '<nav aria-label="On this page">')
        assert '</nav></details><article class="reader-content">' in content
    assert sorted(path.name for path in (out/'spec').iterdir()) == sorted(
        f'{"index" if name == "README" else name}.{kind}' for name, _ in build.CHAPTERS for kind in ('html', 'md'))
    for name, _ in build.CHAPTERS:
        copied = 'index.md' if name == 'README' else f'{name}.md'
        chapter = (out/'spec'/copied).read_text(encoding='utf-8')
        assert chapter == build.spec_markdown(SITE.parent, name)
        assert all((out/'spec'/target).is_file() for target in re.findall(r'\]\(\./([^)#\s]+)', chapter))
        assert f'<link rel="alternate" type="text/markdown" href="./{copied}">' in (
            out/'spec'/copied).with_suffix('.html').read_text(encoding='utf-8')
    assert "document.querySelector('.reader-toc')" in (SITE/'theme/site.js').read_text(encoding='utf-8')
    assert '="../assets/style.css"' in (out/'spec/index.html').read_text(encoding='utf-8')
    posts = sorted(path.name for path in (SITE/'blog').iterdir() if path.is_dir())
    assert posts
    assert sorted(path.parent.name for path in (out/'blog').glob('*/index.html')) == posts
    assert sorted(path.name for path in (out/'blog').iterdir()) == sorted([*posts, 'index.html'])
    written = build.blog_posts(SITE.parent)
    for item in written:
        copied = (out/'blog'/item['slug']/'index.md').read_text(encoding='utf-8')
        published = f'{item["date"]:%B} {item["date"].day}, {item["date"].year}'
        address = f'{OVERVIEW_URL}blog/{item["slug"]}/'
        assert copied == build.post_markdown(item, published, address)
        assert copied.startswith(f'# {build.plain(item["title"])}\n\n{published}\nWritten by {item["author"]}\n')
        images = re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', copied)
        assert images == [f'{address}{name}' for name in re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', item['body'])]
        assert all((out/'blog'/item['slug']/image.removeprefix(address)).is_file() for image in images)
        assert ALTERNATE in (out/'blog'/item['slug']/'index.html').read_text(encoding='utf-8')
    llms = (out/'llms.txt').read_text(encoding='utf-8')
    assert llms == build.overview_llms(config, ARGS, SITE.parent)
    assert list(llms_sections(llms)) == ['Specification', 'Catalog', 'Blog', 'Optional']
    own = [url.removeprefix(OVERVIEW_URL) for url in llms_links(llms) if url.startswith(OVERVIEW_URL)]
    assert own == [f'spec/{"index" if name == "README" else name}.md' for name, _ in build.CHAPTERS] + [
        f'blog/{item["slug"]}/index.md' for item in written]
    assert all((out/copied).is_file() for copied in own)
    assert f'<link rel="describedby" type="text/plain" href="{OVERVIEW_URL}llms.txt">' in index
    assert 'rel="alternate"' not in index
    blog = (out/'blog/index.html').read_text(encoding='utf-8')
    assert blog.count('<article class="post-row">') == len(posts)
    assert '="../assets/style.css"' in blog
    assert (out/'assets/favicon.svg').read_text(encoding='utf-8') == graphics.FAVICON
    assert (out/'assets/fonts/instrument-sans-variable.woff2').is_file()


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
        assert 'one per effective recommendation, and is absent when there is none.' in guidance
        assert 'A recommended tool carries a "Recommended" label in the list.' in guidance
        assert 'gold dot' not in guidance
        assert 'A stale designation shows "Recommendation needs review" and has no card.' in guidance
        assert ('A live status for screen readers reports the number of matching unique '
                'listings.') in guidance
        assert 'Search and category chips sit above the results.' in guidance
        assert 'Category scopes remain registry metadata and are not displayed.' in guidance
        assert 'While a search or category is active, Recommended is hidden.' in guidance
        assert ('Without JavaScript, the search and chips stay hidden and every listing '
                'remains visible.') in guidance
        assert ('The page shows the icon, the name, one line of facts (category, platforms, '
                'publisher, version), the first sentence, a prompt that asks an agent to install '
                'the tool from its source, up to six use cases, and other tools in the same '
                'category.') in guidance
        assert 'An entry without a snapshot remains readable.' in guidance
        assert ('A catalog without a registry has no chips, no Recommended, and no Category '
                'fact.') in guidance


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