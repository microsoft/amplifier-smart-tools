"""A tool's own website: the page, its llms.txt, and a build from site.yaml."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

SITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE/'theme'))
import build
import graphics

ARGS = SimpleNamespace(local=False, family_owner=None)
REPO = 'https://github.com/robotdad/possibly'
MANIFEST = '---\nname: possibly\nversion: 1.2.0\nplatforms: [linux, macos]\n---\n# Usage\n'
TOOL = {
    'kind': 'tool',
    'key': 'possibly',
    'name': 'Possibly',
    'title': 'Possibly | Fixture',
    'description': 'Possibly weighs   the options\nfor a decision.',
    'promise': ['Weigh the', 'options.'],
    'standfirst': 'It lists what can happen.',
    'tint': '#f2a7c3',
    'links': [{'label': 'Read the guide', 'path': 'docs/guide.md'}],
    'requests': {'title': 'Then try', 'items': ['Weigh issue #7.', 'List the risks.']},
    'sections': [
        {'kind': 'cards', 'id': 'features', 'title': 'What it does.',
         'items': [{'title': 'Options', 'text': 'It names each option.', 'icon': 'search'},
                   {'title': 'Risks', 'text': 'It names each risk.', 'icon': 'spark'}]},
        {'kind': 'steps', 'title': ['How it', 'works.'], 'items': ['Ask.', 'Read.'],
         'links': [{'label': 'Elsewhere', 'url': 'https://example.com/more'}]},
    ],
    'related': ['reality-check'],
}
REPORT = {'kind': 'report', 'title': 'What comes back.', 'request': 'Weigh lunch.', 'caption': 'An example.',
          'findings': [{'state': 'passed', 'title': 'Soup is safe.', 'evidence': ['01-soup.png', 'GET /soup 200']},
                       {'state': 'failed', 'title': 'Stew is late.', 'text': 'Step 2: no stew.'},
                       {'state': 'passed', 'title': 'Bread is there.'},
                       {'state': 'skipped', 'title': 'Dessert.'}]}
EMBED = {'kind': 'embed', 'title': 'Try it.', 'directory': 'site/demo', 'files': ['src/view.html'],
         'label': 'Possibly, with an example', 'height': 640, 'caption': 'An example.'}
ENCLOSURE = {'kind': 'enclosure', 'title': 'What is inside.', 'link': 'calls', 'footer': 'One place.',
             'outside': {'title': 'Outside', 'rows': [{'name': 'Caller', 'text': 'asks', 'icon': 'chat'}]},
             'inside': {'title': 'Inside', 'note': 'One project',
                        'parts': [{'name': 'Core', 'text': 'answers', 'icon': 'box'}]}}
BLOCKS = {'kind': 'blocks', 'title': 'What it makes.', 'text': 'Parts.',
          'items': [{'title': 'Library', 'text': 'It holds the code.'},
                    {'title': 'Yours', 'text': 'It holds what you know.', 'own': True}]}
FIT = {'kind': 'fit', 'title': 'When to use it.',
       'use': {'title': 'Use it', 'items': ['After a change.']},
       'other': {'title': 'Not for', 'items': ['Unit tests.'], 'note': 'It takes minutes.'}}


def tool_root(root):
    (root/'smart-tool.json').write_text(json.dumps({'manifest': 'src/SMART_TOOL.md'}), encoding='utf-8')
    (root/'src').mkdir()
    (root/'src/SMART_TOOL.md').write_text(MANIFEST, encoding='utf-8')
    return root


def copy_button(number):
    return (f'<button class="copy-request" type="button" data-copy="request-{number}" aria-label="Copy">'
            f'{graphics.icon("copy", 16)}{graphics.icon("check", 16)}</button>'
            '<p class="visually-hidden" role="status" aria-live="polite"></p>')


def test_tool_page_opens_with_identity_facts_prompt_and_requests(tmp_path):
    page = build.tool_page(TOOL, ARGS, tool_root(tmp_path))
    assert page.startswith('<div class="tool-site tinted" style="--tint:#f2a7c3"><section class="hero"><div class="hero-grid"><div>')
    assert ('<div><p class="tool-name">Possibly</p><dl class="facts">'
            '<div><dt class="visually-hidden">Version</dt><dd>v1.2.0</dd></div>'
            '<div><dt class="visually-hidden">Platform</dt><dd>Linux, macOS</dd></div></dl></div></div>'
            '<h1>Weigh the<br>options.</h1><p class="standfirst">It lists what can happen.</p>') in page
    assert ('</div><div class="hero-side"><div class="hero-start" id="get-started">'
            '<p class="eyebrow">Ask your agent to install it</p>') in page
    assert f'<pre id="prompt">Go to {REPO} and install it.</pre>' in page.replace('<wbr>', '')
    assert (f'<a class="button action" href="{REPO}">View on GitHub{graphics.icon("arrow-up-right", 18)}</a>'
            f'<a class="text-link" href="{REPO}/blob/main/docs/guide.md">Read the guide') in page
    assert ('<aside class="news requests" aria-labelledby="requests-title"><h2 id="requests-title">Then try</h2>'
            '<ul class="news-list">'
            f'<li class="copy-region"><p id="request-1">Weigh issue #7.</p>{copy_button(1)}</li>'
            f'<li class="copy-region"><p id="request-2">List the risks.</p>{copy_button(2)}</li></ul></aside>') in page


def test_tool_page_has_its_sections_in_order_its_tint_and_more_tools(tmp_path):
    page = build.tool_page(TOOL, ARGS, tool_root(tmp_path))
    assert page.startswith('<div class="tool-site tinted" style="--tint:#f2a7c3"><section class="hero">')
    assert ('</section><section class="section" id="features"><div class="section-head"><h2>What it does.</h2></div>'
            '<div class="benefits cards of-2"><div><span class="tile" style="--swatch:var(--tint-blue)">'
            f'{graphics.icon("search", 22)}</span><strong>Options</strong><p>It names each option.</p></div>') in page
    assert ('</div></section><section class="section joined"><div class="build"><div><h3>How it<br>works.</h3>'
            '<div class="actions"><a class="text-link" href="https://example.com/more">Elsewhere') in page
    assert '<ol class="numbered"><li><h3>Ask.</h3></li><li><h3>Read.</h3></li></ol></div></section>' in page
    assert ('<h3 class="app-row-name"><a href="https://microsoft.github.io/amplifier-smart-tool-reality-check/">'
            'Reality Check</a></h3><p>Tests your app by using it.</p>') in page
    assert page.endswith('</section></div>') and '<figure>' not in page


def test_a_prompt_address_may_break_after_a_slash_but_not_inside_the_scheme():
    box = build.code_box('Go to https://github.com/example/a-tool and install it.', 'Prompt', 'prompt')
    assert '<pre id="prompt">Go to https://github.com/<wbr>example/<wbr>a-tool and install it.</pre>' in box
    assert '<pre id="prompt">a &lt;b&gt; / c</pre>' in build.code_box('a <b> / c', 'Prompt', 'prompt')


def test_tool_page_rejects_a_tint_that_is_not_a_hex_color(tmp_path):
    for tint in ('pink', '#12345', '#123456;background:url(https://example.com)'):
        with pytest.raises(ValueError, match='Tint'):
            build.tool_page(dict(TOOL, tint=tint), ARGS, tmp_path)
    assert build.tool_page({k: v for k, v in TOOL.items() if k != 'tint'}, ARGS, tmp_path).startswith('<div class="tool-site"><section')


def test_site_without_sections_gets_a_picture_then_cards_over_a_band_of_steps(tmp_path):
    config = {'kind': 'tool', 'key': 'possibly', 'name': 'Possibly', 'promise': 'Weigh the options.',
              'prompt': 'Use Possibly.', 'prerequisites': 'Needs Git.', 'guide': 'docs/setup.md',
              'image': 'site/assets/shot.png', 'alt': 'A "shot"', 'caption': 'The app.', 'width': 1200, 'height': 600,
              'detail_title': 'What it does.', 'details': [['Options', 'It names each option.']],
              'flow_title': 'In short.', 'steps': [['Ask.', 'State the decision.']],
              'step_links': [{'label': 'Guide', 'path': 'docs/guide.md'}]}
    page = build.tool_page(config, ARGS, tmp_path)
    assert page.startswith('<div class="tool-site"><section class="hero"><div class="hero-grid"><div>')
    assert '<div class="hero-side"><div class="hero-start" id="get-started">' in page
    assert '<div><p class="tool-name">Possibly</p></div></div><h1>Weigh the options.</h1>' in page
    assert '<pre id="prompt">Use Possibly.</pre>' in page.replace('<wbr>', '')
    assert f'<p class="note">Needs Git. <a class="" href="{REPO}/blob/main/docs/setup.md">Setup guide</a></p>' in page
    assert ('</section><figure><div class="product-image"><a href="./assets/shot.png" aria-label="Open full-size Possibly image">'
            '<img src="./assets/shot.png" alt="A &quot;shot&quot;" width="1200" height="600"></a></div>'
            '<figcaption class="image-caption"><span>The app.</span><span class="demo-actions">'
            '<a class="" href="./assets/shot.png">View full size</a></span></figcaption></figure>'
            '<section class="section" id="features"><div class="section-head"><h2>What it does.</h2></div>'
            '<div class="benefits cards of-1">') in page
    assert f'{graphics.icon("box", 22)}</span><strong>Options</strong><p>It names each option.</p></div></div><div class="build">' in page
    assert (f'<h3>In short.</h3><div class="actions"><a class="text-link" href="{REPO}/blob/main/docs/guide.md">Guide') in page
    assert '<ol class="numbered"><li><h3>Ask.</h3><p>State the decision.</p></li></ol></div></section></div>' in page
    assert 'class="news requests"' not in page and 'app-list' not in page
    assert build.tool_page({**config, 'flow_title': None}, ARGS, tmp_path).count('<h3>How it works.</h3>') == 1


def test_media_section_shows_a_video_a_titled_picture_and_a_phone_zoom(tmp_path):
    media = {'kind': 'media', 'image': 'site/assets/shot.png', 'alt': 'A shot', 'caption': 'The app.', 'width': 1200, 'height': 600}
    video = build.tool_page(dict(TOOL, sections=[dict(media, video='site/assets/demo.mp4')]), ARGS, tmp_path)
    assert ('</section><figure><div class="product-image"><video data-demo-video controls muted loop playsinline '
            'preload="metadata" poster="./assets/shot.png" width="1200" height="600" aria-label="A shot">'
            '<source src="./assets/demo.mp4" type="video/mp4">') in video
    assert 'data-motion-toggle' in video and '<img' not in video
    titled = build.tool_page(dict(TOOL, sections=[dict(media, title='See it.', zoom=True)]), ARGS, tmp_path)
    assert ('<section class="section"><div class="section-head"><h2>See it.</h2></div>'
            '<figure><div class="product-image zoom"><a href="./assets/shot.png"') in titled
    bare = build.tool_page(dict(TOOL, sections=[{k: v for k, v in media.items() if k != 'caption'} | {'video': 'site/assets/demo.mp4'}]), ARGS, tmp_path)
    assert '</video></div></figure>' in bare and 'image-caption' not in bare and 'data-motion-toggle' not in bare


def test_report_section_tallies_states_and_lists_evidence(tmp_path):
    page = build.tool_page(dict(TOOL, sections=[REPORT]), ARGS, tmp_path)
    assert ('<div class="report"><div class="report-head"><div><p class="eyebrow">Request</p>'
            '<p class="report-request">Weigh lunch.</p></div><ul class="tally"><li class="passed">2 passed</li>'
            '<li class="failed">1 failed</li><li class="skipped">1 not checked</li></ul></div><ol class="findings">'
            f'<li class="finding passed"><span class="state">{graphics.icon("check", 18)}</span>'
            '<div><p class="finding-state">Passed</p><h3>Soup is safe.</h3></div>'
            '<ul class="evidence"><li>01-soup.png</li><li>GET /soup 200</li></ul></li>'
            f'<li class="finding failed"><span class="state">{graphics.icon("close", 18)}</span>'
            '<div><p class="finding-state">Failed</p><h3>Stew is late.</h3><p>Step 2: no stew.</p></div></li>') in page
    assert (f'<li class="finding skipped"><span class="state">{graphics.icon("minus", 18)}</span>'
            '<div><p class="finding-state">Not checked</p><h3>Dessert.</h3></div></li></ol></div>'
            '<p class="image-caption">An example.</p></section>') in page


def test_embed_section_frames_its_page_and_keeps_its_files_in_the_repository(tmp_path):
    page = build.tool_page(dict(TOOL, sections=[EMBED]), ARGS, tmp_path)
    assert ('<section class="section"><div class="section-head stacked"><h2>Try it.</h2></div><figure><div class="product-image">'
            '<iframe class="embed" src="./demo/" title="Possibly, with an example" height="640" loading="lazy"></iframe></div>'
            '<figcaption class="image-caption"><span>An example.</span></figcaption></figure></section>') in page
    introduced = build.tool_page(dict(TOOL, sections=[dict(EMBED, text='Open it.')]), ARGS, tmp_path)
    assert '<div class="section-head stacked"><h2>Try it.</h2><p>Open it.</p></div>' in introduced
    bare = build.tool_page(dict(TOOL, sections=[{'kind': 'embed', 'directory': 'site/demo', 'label': '<x>'}]), ARGS, tmp_path)
    assert '<figure><div class="product-image"><iframe class="embed" src="./demo/" title="&lt;x&gt;" height="600" loading="lazy"></iframe></div></figure>' in bare
    assert build.embed_sources(tmp_path, EMBED) == (tmp_path/'site/demo', [tmp_path/'src/view.html'])
    assert build.embed_sources(tmp_path, {'directory': 'site/demo'}) == (tmp_path/'site/demo', [])
    for outside in ({'directory': '../demo'}, {'directory': 'site/demo', 'files': ['/etc/hosts']}):
        with pytest.raises(ValueError, match='repository'):
            build.embed_sources(tmp_path, outside)


def test_enclosure_blocks_and_fit_sections(tmp_path):
    page = build.tool_page(dict(TOOL, sections=[ENCLOSURE, BLOCKS, FIT]), ARGS, tmp_path)
    assert ('<div class="flow enclosure"><div class="flow-panel"><h3>Outside</h3>'
            f'<div class="flow-item"><span class="tile">{graphics.icon("chat", 22)}</span>'
            '<div><strong>Caller</strong><span>asks</span></div></div></div>'
            f'<div class="flow-arrow"><span>calls</span>{graphics.icon("arrow-right", 28)}</div>'
            '<div class="flow-panel wall"><h3>Inside</h3><p class="eyebrow">One project</p><div class="enclosure-parts">'
            f'<div class="flow-item"><span class="tile">{graphics.icon("box", 22)}</span>'
            '<div><strong>Core</strong><span>answers</span></div></div></div></div></div>'
            '<p class="dimension">One place.</p></section>') in page
    assert ('<section class="section split"><div><h2>What it makes.</h2><p>Parts.</p></div><div class="blocks">'
            '<div class="block"><h3>Library</h3><p>It holds the code.</p></div>'
            f'<div class="block own">{graphics.icon("plus", 44)}<h3>Yours</h3><p>It holds what you know.</p></div></div></section>') in page
    assert ('<div class="fit"><div class="fit-list use"><h3>Use it</h3>'
            f'<ul><li>{graphics.icon("check", 18)}<span>After a change.</span></li></ul></div>'
            f'<div class="fit-list"><h3>Not for</h3><ul><li>{graphics.icon("minus", 18)}<span>Unit tests.</span></li></ul>'
            '<p class="note">It takes minutes.</p></div></div></section>') in page


def test_tool_page_escapes_its_wording(tmp_path):
    report = dict(REPORT, request='<q>', findings=[{'state': 'failed', 'title': '<f>', 'text': '<t>', 'evidence': ['<e>']}])
    blocks = dict(BLOCKS, items=[{'title': '<k>', 'text': '<l>'}])
    config = dict(TOOL, name='<b>Tool</b>', promise=['A & B', '<i>'], standfirst='"Quoted" <s>',
                  requests={'items': ['<script>alert(1)</script>']}, sections=[report, blocks])
    page = build.tool_page(config, ARGS, tmp_path)
    assert '<p class="tool-name">&lt;b&gt;Tool&lt;/b&gt;</p>' in page
    assert '<h1>A &amp; B<br>&lt;i&gt;</h1><p class="standfirst">&quot;Quoted&quot; &lt;s&gt;</p>' in page
    assert '<h2 id="requests-title">Then ask</h2>' in page
    assert '<p id="request-1">&lt;script&gt;alert(1)&lt;/script&gt;</p>' in page
    assert '<h3>&lt;f&gt;</h3><p>&lt;t&gt;</p></div><ul class="evidence"><li>&lt;e&gt;</li></ul>' in page
    for raw in ('<script>', '<b>', '<i>', '<s>', '<q>', '<f>', '<t>', '<e>', '<k>', '<l>'):
        assert raw not in page


def test_tool_llms_lists_the_prompt_requests_sections_and_each_link_once(tmp_path):
    sections = [*TOOL['sections'], REPORT, ENCLOSURE, BLOCKS, FIT]
    sections[1] = dict(sections[1], links=[{'label': 'Read the guide', 'path': 'docs/guide.md'},
                                           {'label': 'Elsewhere', 'url': 'https://example.com/more'}])
    assert build.tool_llms(dict(TOOL, sections=sections), tool_root(tmp_path)) == f'''# Possibly

> Weigh the options.

Possibly weighs the options for a decision.

Give this prompt to your agent:

> Go to {REPO} and install it.

## Then try

- Weigh issue #7.
- List the risks.

## What it does.

- Options: It names each option.
- Risks: It names each risk.

## How it works.

- Ask.
- Read.

## What is inside.

- Core: answers
- Caller: asks

## What it makes.

- Library: It holds the code.
- Yours: It holds what you know.

## When to use it.

- Use it: After a change.
- Not for: Unit tests.

## Links

- [Source repository]({REPO})
- [Manifest]({REPO}/blob/main/src/SMART_TOOL.md)
- [Read the guide]({REPO}/blob/main/docs/guide.md)
- [Elsewhere](https://example.com/more)
'''


def test_tool_site_builds_from_site_yaml_with_a_synced_theme(tmp_path):
    tool_root(tmp_path)
    (tmp_path/'site/assets').mkdir(parents=True)
    (tmp_path/'site/assets/shot.png').write_bytes(b'png')
    (tmp_path/'site/demo/data').mkdir(parents=True)
    (tmp_path/'site/demo/index.html').write_text('<p>demo</p>', encoding='utf-8')
    (tmp_path/'site/demo/data/check.json').write_text('{}', encoding='utf-8')
    (tmp_path/'src/view.html').write_text('<p>view</p>', encoding='utf-8')
    media = {'kind': 'media', 'image': 'site/assets/shot.png', 'alt': 'A shot', 'caption': 'The app.', 'width': 1200, 'height': 600}
    config = dict(TOOL, sections=[media, *TOOL['sections'], dict(EMBED, content={'title': 'An example'})])
    (tmp_path/'site/site.yaml').write_text(yaml.safe_dump(config), encoding='utf-8')
    subprocess.run([sys.executable, str(SITE/'sync_theme.py'), str(tmp_path)], check=True)
    out = tmp_path/'generated'
    subprocess.run([sys.executable, str(tmp_path/'site/theme/build.py'), '--output', str(out)], check=True)
    page = (out/'index.html').read_text(encoding='utf-8')
    assert '<title>Possibly | Fixture</title>' in page
    assert '<link rel="describedby" type="text/plain" href="https://robotdad.github.io/possibly/llms.txt">' in page
    assert f'<a href="{REPO}">GitHub</a>' in page
    assert build.tool_page(config, ARGS, tmp_path) in page
    assert (out/'llms.txt').read_text(encoding='utf-8') == build.tool_llms(config, tmp_path)
    assert (out/'assets/shot.png').read_bytes() == b'png'
    assert [(path.relative_to(out/'demo').as_posix(), path.read_text(encoding='utf-8')) for path in sorted((out/'demo').rglob('*.*'))] == [
        ('content.json', '{"title": "An example"}'), ('data/check.json', '{}'), ('index.html', '<p>demo</p>'), ('view.html', '<p>view</p>')]
    assert (out/'assets/favicon.svg').read_text(encoding='utf-8') == graphics.favicon(TOOL['key'])


def test_a_tool_with_artwork_has_it_as_its_favicon_and_others_have_the_wrench():
    icon = graphics.favicon('reality-check')
    assert icon.startswith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">')
    assert f'<rect width="64" height="64" rx="14" fill="{graphics.TILE}"/>{graphics.ARTWORK["reality-check"]}</svg>' in icon
    assert graphics.favicon('catalog') == graphics.favicon('overview') == graphics.FAVICON


def test_theme_styles_and_script_carry_the_tool_site_hooks():
    css = (SITE/'theme/style.css').read_text(encoding='utf-8')
    for rule in ('.tool-id {', '.hero-side {', '.requests .news-list li {', '.copy-request {', '.tinted .requests {',
                 '.section.joined {', '.report {', '.finding {', '.flow.enclosure {', '.flow-panel.wall {', '.blocks {',
                 '.block.own {', '.fit {', '.hero + figure {', '.product-image:has(> .embed) {', '.product-image .embed {'):
        assert f'\n{rule}\n' in css
    assert '.copy-request[data-copied] .icon + .icon,\n.copy-markdown[data-copied] .icon + .icon {' in css
    family = json.loads((SITE/'theme/family.json').read_text(encoding='utf-8'))['pages']
    for key in ('reality-check', 'digital-twin-universe', 'smart-tool-creator'):
        assert family[key]['owner'] == 'microsoft' and family[key]['tagline']
        assert key in graphics.ARTWORK
