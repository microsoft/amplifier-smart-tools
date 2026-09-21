#!/usr/bin/env python3
"""Build a standalone Smart Tools page. Theme v0.1.0, MIT licensed."""
import argparse
import html
import json
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

THEME = Path(__file__).resolve().parent
FAMILY = json.loads((THEME / 'family.json').read_text())
PAGES = FAMILY['pages']
SPEC = 'https://github.com/microsoft/amplifier-smart-tools/tree/main/spec'


def plain(value):
    """Use plain punctuation in displayed metadata without editing source snapshots."""
    text = str(value).translate(str.maketrans({'\u2014': ' - ', '\u2013': '-', '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u00b7': '/', '\u00d7': 'x', '\u2192': ' to '}))
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()


def esc(value):
    return html.escape(plain(value), quote=True)


def safe_url(value):
    parsed = urlsplit(str(value))
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Expected a credential-free HTTPS URL')
    return str(value)


def link(url, text, classes=''):
    return f'<a class="{classes}" href="{html.escape(url, quote=True)}">{esc(text)}</a>'


def repo_url(key):
    p = PAGES[key]
    return f'https://github.com/{p["owner"]}/{p["repository"]}'


def page_url(key, args):
    p = PAGES[key]
    if args.local:
        return f'/{p["repository"]}/'
    owner = args.family_owner if p['owner'] == 'microsoft' and args.family_owner else p['owner']
    return f'https://{owner}.github.io/{p["repository"]}/'


def plate_art(variant=0):
    angle = [0, 22, 45, 67, 90][variant % 5]
    return f'''<svg viewBox="0 0 400 400" fill="none" aria-hidden="true">
      <g stroke="currentColor" stroke-width=".7" opacity=".28"><circle cx="200" cy="200" r="165"/><circle cx="200" cy="200" r="113"/><circle cx="200" cy="200" r="62"/><path d="M0 200H400M200 0V400M25 25L375 375M25 375L375 25"/></g>
      <g transform="rotate({angle} 200 200)" stroke="currentColor"><path d="M72 286L145 96L308 142L261 322Z" stroke-width="1.2"/><path d="M72 286L308 142M145 96L261 322" opacity=".45"/><rect x="139" y="90" width="12" height="12" fill="var(--paper)"/><rect x="302" y="136" width="12" height="12" fill="var(--paper)"/><circle cx="72" cy="286" r="6" fill="var(--paper)"/><circle cx="261" cy="322" r="6" fill="var(--paper)"/></g>
      <circle cx="200" cy="200" r="9" fill="var(--gold)"/><circle cx="200" cy="200" r="22" stroke="var(--gold)" opacity=".5"/>
    </svg>'''


def code_box(text, title, identity):
    return f'''<div class="copy-region"><div class="code-box"><div class="code-head"><span>{esc(title)}</span><button class="copy" data-copy="{identity}" aria-label="Copy {esc(title)}">Copy</button></div><pre id="{identity}">{esc(text)}</pre></div><p class="status-message" role="status" aria-live="polite"></p></div>'''


def related(keys, args):
    return '<div class="related">' + ''.join(f'<a href="{page_url(k, args)}">{PAGES[k]["name"]}<span>Explore the tool</span></a>' for k in keys) + '</div>'


def overview(config, args):
    descriptor = json.dumps({
        "manifest": "src/my_smart_tool/SMART_TOOL.md",
        "cli_argv": ["my-smart-tool"],
        "deterministic_smoke": ["manifest"],
    }, indent=2)
    return f'''<section class="hero"><div class="hero-grid"><div>
      <p class="eyebrow">Amplifier Smart Tools</p>
      <h1>Expertise, built<br>into the tool.</h1>
      <p class="lede">A format for packaging domain expertise into tools with their own AI capability. Built as libraries. Usable from any agent, application, or terminal.</p>
      <div class="actions">{link(page_url('catalog',args),'Find a smart tool','button primary')}{link('#build','Build a smart tool','text-link')}{link(SPEC,'Read the specification','text-link')}</div>
    </div><figure class="plate"><span class="plate-label">EXPERTISE THAT TRAVELS</span><img class="plate-motion" src="./assets/expertise-loop.png" data-motion-src="./assets/expertise-loop.gif" data-still-src="./assets/expertise-loop.png" alt="Points spread into rotating shapes, resolve into three nested squares, and return to their starting positions." width="600" height="600">
      <button class="motion-toggle plate-toggle" data-motion-toggle hidden type="button" aria-pressed="false">Pause motion</button><figcaption class="plate-caption"><span>LIBRARY AT THE CORE</span><span>OPEN AT THE EDGES</span></figcaption>
    </figure></div></section>
    <div class="principles"><div><strong>Library first.</strong><p>Every capability is available to code, with a thin CLI for agents and scripts.</p></div><div><strong>Intelligence inside.</strong><p>The tool carries the context and model-backed methods its domain needs.</p></div><div><strong>Ordinary work stays ordinary.</strong><p>Deterministic operations run without model credentials.</p></div></div>
    <section class="section two-col" id="what"><div><p class="eyebrow">What is an Amplifier Smart Tool?</p><h2>A familiar interface.<br>A capable tool.</h2></div><div>
      <p>An Amplifier Smart Tool is a self-contained library and command-line tool that ships with its own AI capability. It accepts arguments and returns results, just like other software you already use.</p>
      <p>For model-backed work, the tool manages the domain context, instructions, and execution. The caller supplies the intent and inputs. Expertise stays with the tool, and the result comes back to the caller.</p>
      <p>Alongside those capabilities, ordinary code handles deterministic work. A caller using only those paths never needs to configure a model provider.</p>
    </div></section>
    <section class="section"><div class="section-heading"><div><p class="eyebrow">How it fits together</p><h2>One library. Several ways in.</h2></div><p>The library owns the capability. Each adapter exposes it in the form a caller needs.</p></div>
      <div class="architecture" aria-label="Library architecture"><div class="entry-points"><div><strong>Application or agent</strong><span>Import the library directly</span></div><div><strong>Command line</strong><span>A required thin adapter</span></div><div><strong>MCP or web interface</strong><span>Optional adapters</span></div></div><div class="library-core"><p class="eyebrow">The library is the tool</p><h3>Domain expertise and capabilities</h3><div class="capability-paths"><div><strong>Deterministic operations</strong><span>Ordinary code. No model required.</span></div><div><strong>Model-backed operations</strong><span>Embedded intelligence for domain work.</span></div></div></div></div>
      <p class="note">No capability belongs only to a wrapper. Removing an optional interface must leave the library and CLI usable.</p>
      <div class="compact-links">{link(SPEC+'structure.html','Read the structure specification')}{link(SPEC+'invocation.html','Understand invocation and help')}</div>
    </section>
    <section class="section two-col"><div><p class="eyebrow">The distinction</p><h2>The tool brings<br>its own intelligence.</h2></div><div>
      <p>Skills give an agent instructions. MCP provides a way to expose and call capabilities. An Amplifier Smart Tool packages a capability that can invoke a model itself, with the domain knowledge needed to do the work.</p>
      <p>These fit together. A tool can use skills internally, expose an optional MCP adapter, or be discovered through a skill. Its intelligence lives behind the library boundary, so the caller does not have to recreate its domain workflow.</p>
      <p>The caller can also be an application, a script, or a scheduled job. Using an Amplifier Smart Tool does not require adopting a particular agent.</p>
    </div></section>
    <section class="section two-col" id="build"><div><p class="eyebrow">Build an Amplifier Smart Tool</p><h2>Package what<br>you know.</h2><p style="margin-top:24px">Start with a domain capability worth sharing. The specification defines how to make it discoverable, callable, and installable.</p><div class="actions">{link(SPEC,'Start with the specification','button primary')}</div></div>
      <ol class="numbered"><li><h3>Put the capability in a library.</h3><p>Expose every useful operation through the library. Add genuine model-backed work alongside deterministic paths that load and run without a provider.</p>{link(SPEC+'structure.html','Library structure','text-link')}</li>
      <li><h3>Describe it where the code lives.</h3><p>Ship one SMART_TOOL.md manifest with the name, purpose, platforms, and prerequisites. Add library-owned usage guidance and capability help.</p>{link(SPEC+'manifest.html','Manifest format','text-link')}</li>
      <li><h3>Add the CLI and package it.</h3><p>Keep argument parsing and I/O in a thin CLI. Support installation from Git, and provide a smart-tool.json descriptor at the distribution root.</p>{link(SPEC+'packaging.html','Packaging and installation','text-link')}</li>
      <li><h3>Check the format. Prove the work.</h3><p>Run the conformance kit against the distribution. Test the actual capabilities separately, then follow the catalog contribution guide to make the tool discoverable.</p>{link(repo_url('overview')+'/tree/main/conformance','Conformance kit','text-link')}</li></ol>
    </section>
    <section class="section two-col"><div><p class="eyebrow">A small, explicit contract</p><h2>Make the entry<br>points easy to find.</h2><p style="margin-top:24px">The descriptor points to the manifest and tells a caller how to launch the CLI. The manifest carries the tool's identity and requirements.</p><p class="note">This example assumes the package installs a my-smart-tool executable with a provider-free manifest command.</p></div><div>
      {code_box(descriptor,'smart-tool.json / example','descriptor')}
      {code_box('uv run conformance/run.py path/to/your-smart-tool','From the specification checkout','conformance')}
      <p class="note">Conformance checks the format and reports checks it cannot perform. It does not certify output quality or replace product tests.</p>
    </div></section>
    <section class="section"><div class="callout"><p class="eyebrow">The Amplifier Smart Tools catalog</p><h2>Find a tool for your work.</h2><p>The catalog is the place to explore available tools, inspect their requirements, and install the shared discovery skill for your coding agent.</p><div class="actions">{link(page_url('catalog',args),'Explore the catalog','button primary')}{link(repo_url('catalog')+'#contributing','Add your tool','text-link')}{link(repo_url('overview')+'/blob/main/ROADMAP.md','Read the roadmap','text-link')}</div></div></section>'''


def tool_page(config, args):
    key = config['key']
    repo = repo_url(key)
    image = './assets/' + Path(config['image']).name
    media = f'<a href="{image}" aria-label="Open full-size {esc(config["name"])} image"><img src="{image}" alt="{esc(config["alt"])}" width="{config["width"]}" height="{config["height"]}" fetchpriority="high"></a>'
    media_link = link(image, 'View full size')
    if config.get('video'):
        video = './assets/' + Path(config['video']).name
        media = f'<video data-demo-video controls muted loop playsinline preload="metadata" poster="{image}" width="{config["width"]}" height="{config["height"]}" aria-label="{esc(config["alt"])}"><source src="{video}" type="video/mp4">{link(video,"Watch the demo")}</video>'
        media_link = f'<button class="motion-toggle" data-motion-toggle hidden type="button" aria-pressed="false">Pause motion</button> {link(video,"Watch full size")}'
    steps = ''.join(f'<li><h3>{esc(t)}</h3><p>{esc(p)}</p></li>' for t,p in config['steps'])
    details = ''.join(f'<article><h3>{esc(t)}</h3><p>{esc(p)}</p></article>' for t,p in config['details'])
    return f'''<section class="hero tool-hero"><div class="hero-grid"><div><h1>{esc(config['name'])}</h1><p class="promise">{esc(config['promise'])}</p></div><div><p class="lede">{esc(config['description'])}</p><div class="actions">{link('#get-started','Get started','button primary')}{link(repo,'View on GitHub','button')}</div></div></div></section>
    <figure class="tool-figure"><div class="product-image">{media}</div><figcaption class="image-caption"><span>{esc(config['caption'])}</span><span class="demo-actions">{media_link}</span></figcaption></figure>
    <section class="section two-col"><div><p class="eyebrow">How it works</p><h2>{esc(config['flow_title'])}</h2><p style="margin-top:24px">{esc(config['flow_intro'])}</p></div><ol class="numbered">{steps}</ol></section>
    <section class="section"><div class="section-heading"><div><p class="eyebrow">Made for real work</p><h2>{esc(config['detail_title'])}</h2></div></div><div class="detail-grid">{details}</div></section>
    <section class="section two-col" id="get-started"><div><p class="eyebrow">Get started</p><h2>Bring it to<br>your agent.</h2><p style="margin-top:24px">Start with the outcome you want. Your agent can install the tool and use its help to carry out the work.</p>{code_box(config['prompt'],'A starting prompt','prompt')}</div><div><h3>Help your agent can use.</h3><p>Amplifier Smart Tools provide help in skill format: instructions your agent can read to understand capabilities, inputs, and how to use the tool. Ask your agent to read <code>--help</code> before getting started.</p>{code_box(config['install'],'Terminal','install')}<p class="note">{esc(config['prerequisites'])}</p><p class="note">{esc(config['model_note'])}</p><div class="compact-links">{link(repo+'/blob/main/'+config['guide'],'Setup and usage guide')}{link(repo+'#readme','Full documentation')}</div></div></section>
    <section class="section"><div class="section-heading"><div><p class="eyebrow">Part of the same family</p><h2>Keep making.</h2></div><p>Each tool stands on its own. Explore the others when your work takes you there.</p></div>{related(config['related'],args)}</section>'''


def catalog(config, args, root):
    import yaml
    entries = []
    platforms = set()
    for source in sorted((root/'tools').glob('*/source.json')):
        slug = source.parent.name
        pointer = json.loads(source.read_text())
        repo = safe_url(pointer['repository']).removesuffix('.git')
        manifest = source.parent/'SMART_TOOL.md'
        provenance = source.parent/'provenance.json'
        description = 'No manifest snapshot is available yet. Inspect the source repository for current guidance.'
        meta, prov = {}, {}
        if manifest.exists() and provenance.exists():
            raw = manifest.read_text()
            if not raw.startswith('---\n'):
                raise ValueError(f'{slug}: missing YAML front matter')
            meta = yaml.safe_load(raw.split('---',2)[1])
            if not isinstance(meta, dict) or not isinstance(meta.get('description'), str):
                raise ValueError(f'{slug}: invalid manifest description')
            description = meta['description'].strip()
            prov = json.loads(provenance.read_text())
        tool_platforms = meta.get('platforms', [])
        if not isinstance(tool_platforms, list) or not all(isinstance(p,str) for p in tool_platforms):
            raise ValueError(f'{slug}: invalid platforms')
        platforms.update(tool_platforms)
        name = meta.get('name', slug)
        display_name = slug.replace('-', ' ').title()
        excerpt = description if len(description) <= 250 else description[:247].rsplit(' ', 1)[0] + '...'
        use_cases = meta.get('use_cases', [])
        if not isinstance(use_cases, list) or not all(isinstance(u,str) for u in use_cases):
            raise ValueError(f'{slug}: invalid use cases')
        detail = ''
        manifest_link = ''
        if prov:
            commit = prov['source']['commit']
            if not re.fullmatch(r'[a-f0-9]{40,64}', commit):
                raise ValueError(f'{slug}: invalid source commit')
            source_repo = safe_url(prov['source']['repository']).removesuffix('.git')
            path = quote(prov['original_manifest_path'],safe='/')
            manifest_link = link(f'{source_repo}/blob/{commit}/{path}', 'Read manifest')
            detail = f'<details><summary>Full description and source</summary><p>{esc(description)}</p><p>Manifest name: {esc(name)}</p><ul>{"".join("<li>"+esc(u)+"</li>" for u in use_cases)}</ul><p>Snapshot refreshed: {esc(prov["last_success"])}</p><p>Source commit: <code>{esc(commit)}</code></p><p>Ref: {esc(prov["source"]["ref"])} / Path: {esc(prov["source"]["path"])}</p></details>'
        showcase = next((key for key,p in PAGES.items() if repo == repo_url(key) and key not in ('overview','catalog')),None)
        launch = link(page_url(showcase,args),'Explore tool') if showcase else ''
        search = esc(' '.join([str(name),description,*use_cases,*tool_platforms]).lower())
        tags = ''.join('<span class="tag">'+esc(p)+'</span>' for p in tool_platforms)
        entries.append(f'<article class="catalog-card" data-tool="{esc(slug)}" data-platforms="{esc(" ".join(tool_platforms))}" data-search="{search}"><h2>{esc(display_name)}</h2><p>{esc(excerpt)}</p><div class="tool-meta">{tags}</div>{detail}<div class="card-links">{launch}{link(repo,"Repository")}{manifest_link}</div></article>')
    options = ''.join(f'<option value="{esc(p)}">{esc(p)}</option>' for p in sorted(platforms))
    return f'''<section class="hero catalog-hero"><p class="eyebrow">Amplifier Smart Tools / Catalog</p><h1>Find a tool.<br>Make something happen.</h1><p class="lede">Domain expertise you can put to work. Explore the tools, inspect their requirements, and bring the right one to your agent.</p><div class="actions">{link('#discovery','Get the discovery skill','button primary')}{link(repo_url('catalog')+'#contributing','Add a tool','text-link')}</div></section>
    <section aria-label="Browse smart tools"><div class="filters"><div class="search-field"><label for="tool-search">Search tools and use cases</label><input id="tool-search" type="search" placeholder="Try video, research, or presentations" autocomplete="off"></div><div><label for="platform">Declared platform</label><select id="platform"><option value="">All platforms</option>{options}</select></div></div><p class="catalog-count" id="result-count" role="status">{len(entries)} tools</p><noscript><p>Search requires JavaScript. All tools are listed below.</p></noscript><div class="catalog-grid">{''.join(entries)}</div><div id="empty-results" class="empty" hidden><h3>No matching tools.</h3><p>Try a broader term or another platform.</p><button id="clear-filters" class="button">Clear filters</button></div><p class="catalog-note">Descriptions and declared platforms come from the tools' own manifest snapshots. A listing does not establish installation or usability in your environment. Expand an entry to inspect its source revision and refresh time.</p></section>
    <section class="section two-col" id="discovery"><div><p class="eyebrow">Let your agent help</p><h2>One skill.<br>The whole catalog.</h2><p style="margin-top:24px">Ask your coding agent to find a Smart Tool for your task. It can inspect the manifest, check the local environment, and follow the selected tool's own guidance.</p></div><div class="callout"><h3>Install the discovery skill.</h3>{code_box(config['install'],'Terminal','install')}<p class="note">Keep only the agents you use. This installs discovery guidance, not the tools or their credentials.</p>{link(repo_url('catalog')+'#install-the-skill','All installation options','text-link')}</div></section>'''


def build_reader(root, out, args, config):
    """Render the checked-out specification; do not maintain a second copy."""
    from markdown_it import MarkdownIt
    md = MarkdownIt('commonmark', {'html': False}).enable('table')
    chapters = [('README', 'Introduction'), ('structure', 'Structure'),
                ('manifest', 'Manifest'), ('invocation', 'Invocation'),
                ('packaging', 'Packaging'), ('examples', 'Examples')]
    chapter_files = {name+'.md': 'index.html' if name == 'README' else name+'.html' for name, _ in chapters}
    target = out/'spec'
    target.mkdir(exist_ok=True)
    for index, (name, label) in enumerate(chapters):
        source = root/'spec'/f'{name}.md'
        tokens = md.parse(plain(source.read_text()))
        headings = []
        used = {}
        for i, token in enumerate(tokens):
            if token.type == 'heading_open':
                text = tokens[i+1].content
                anchor = re.sub(r'[^a-z0-9 -]', '', text.lower()).replace(' ', '-')
                n = used.get(anchor, 0)
                used[anchor] = n + 1
                if n:
                    anchor += '-'+str(n)
                token.attrSet('id', anchor)
                if token.tag == 'h1':
                    tokens[i+1].content = 'Amplifier Smart Tools' if name == 'README' else text
                    tokens[i+1].children = md.parseInline(tokens[i+1].content)[0].children
                if token.tag == 'h2':
                    headings.append((anchor,text))
            for child in token.children or []:
                if child.type != 'link_open':
                    continue
                href = child.attrGet('href')
                url = urlsplit(href)
                if url.scheme or url.netloc or not url.path:
                    continue
                filename = url.path.removeprefix('./')
                if filename in chapter_files:
                    child.attrSet('href', urlunsplit(('', '', './'+chapter_files[filename], url.query, url.fragment)))
                else:
                    from posixpath import normpath
                    source_path = normpath('spec/'+filename)
                    child.attrSet('href', repo_url('overview')+'/blob/main/'+source_path+('#'+url.fragment if url.fragment else ''))
        rendered = md.renderer.render(tokens, md.options, {})
        chapter_nav = ''.join('<a href="./'+chapter_files[n+'.md']+'"'+(' aria-current="page"' if n == name else '')+'>'+esc(l)+'</a>' for n,l in chapters)
        toc = ''.join(link('#'+anchor,text) for anchor,text in headings)
        page_nav = ''
        if index:
            prev_name, prev_label = chapters[index-1]
            page_nav += link('./'+chapter_files[prev_name+'.md'], 'Previous: '+prev_label)
        if index+1 < len(chapters):
            next_name, next_label = chapters[index+1]
            page_nav += link('./'+chapter_files[next_name+'.md'], 'Next: '+next_label)
        body = f'''<div class="reader-layout"><aside class="reader-sidebar"><p class="eyebrow">Specification</p><nav aria-label="Specification chapters">{chapter_nav}</nav><details class="reader-toc"><summary>On this page</summary><nav aria-label="On this page">{toc}</nav></details>{link(repo_url('overview')+'/blob/main/spec/'+name+'.md','View source on GitHub','reader-source')}</aside><article class="reader-content"><p class="eyebrow">Amplifier Smart Tools / Specification</p>{rendered}<nav class="reader-pagination" aria-label="Chapter navigation">{page_nav}</nav></article></div>'''
        page_config = dict(config, kind='reader', title=label+' | Amplifier Smart Tools specification',description='Read the '+label.lower()+' chapter of the Amplifier Smart Tools specification.')
        (target/chapter_files[name+'.md']).write_text(document(page_config,body,args,'../assets/'))


def document(config, body, args, asset_prefix='./assets/'):
    key = config['key']
    destinations = [
        (page_url('catalog', args), 'Find', key == 'catalog'),
        (page_url('overview', args) + '#build', 'Build', False),
        (SPEC, 'Learn', config['kind'] == 'reader'),
    ]
    nav = ''.join(f'<a href="{url}"' + (' aria-current="page"' if current else '') + f'>{label}</a>' for url, label, current in destinations)
    team_identity = '<div class="team"><strong>MADE</strong><span>Math &middot; AI &middot; Design &middot; Engineering</span></div>'
    organization = '<span class="organization">Microsoft Office of the CTO</span>'
    title = config['title']
    description = config['description']
    accent = config.get('accent','#486b61')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',accent):
        raise ValueError('Accent must be a hex color')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="theme-color" content="#f6f4ee"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="website"><link rel="icon" href="{asset_prefix}favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{asset_prefix}style.css"><script src="{asset_prefix}site.js" defer></script></head>
<body style="--accent:{accent}"><a class="skip" href="#main">Skip to content</a><div class="attribution"><div class="wrap">{team_identity}{organization}</div></div><header class="masthead"><div class="wrap"><a class="brand" href="{page_url('overview',args)}"><img class="brand-motion" src="{asset_prefix}mark-loop.png" data-motion-src="{asset_prefix}mark-loop.gif" data-still-src="{asset_prefix}mark-loop.png" alt="" width="42" height="42"><span class="brand-name">Amplifier Smart Tools</span></a><nav class="nav" aria-label="Main navigation">{nav}{link(repo_url(key),'GitHub')}</nav></div></header><main class="wrap" id="main">{body}</main><footer class="site-footer"><div class="wrap footer-grid"><div><strong class="footer-brand">Amplifier Smart Tools</strong><p>Expertise, built into the tool.</p><div class="footer-attribution">{team_identity}{organization}</div></div><nav class="footer-links" aria-label="Footer">{nav}{link(repo_url(key),'GitHub')}</nav></div></footer></body></html>'''


def main():
    global SPEC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='_site')
    parser.add_argument('--local', action='store_true', help='Link sibling pages on the same local preview server')
    parser.add_argument('--family-owner', help='Owner of the overview and catalog Pages previews, e.g. robotdad')
    args = parser.parse_args()
    SPEC = page_url('overview', args) + 'spec/'
    root = THEME.parent.parent
    config = json.loads((root/'site/site.json').read_text())
    out = Path(args.output).resolve()
    if out == root or root.is_relative_to(out) or out in (root/'site', THEME):
        raise ValueError('Output must be a separate generated-site directory')
    out.mkdir(parents=True, exist_ok=True)
    (out/'assets').mkdir(exist_ok=True)
    for filename in ('style.css','site.js'):
        shutil.copy2(THEME/filename, out/'assets'/filename)
    for asset_dir in (THEME/'assets', root/'site/assets'):
        if asset_dir.is_dir():
            shutil.copytree(asset_dir, out/'assets', dirs_exist_ok=True)
    for media_key in ('image', 'video'):
        if not config.get(media_key):
            continue
        source = (root/config[media_key]).resolve()
        if not source.is_relative_to(root):
            raise ValueError('Media must belong to the repository')
        shutil.copy2(source,out/'assets'/source.name)
    kind = config['kind']
    body = overview(config,args) if kind == 'overview' else catalog(config,args,root) if kind == 'catalog' else tool_page(config,args)
    doc = document(config, body, args)
    if kind == 'overview':
        build_reader(root, out, args, config)
    (out/'index.html').write_text(doc,encoding='utf-8')
    (out/'.nojekyll').touch()
    (out/'assets/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" fill="#f6f4ee"/><g fill="none" stroke="#92743a"><rect x="7" y="7" width="26" height="26"/><rect x="11" y="11" width="18" height="18" transform="rotate(20 20 20)"/><rect x="15" y="15" width="10" height="10" transform="rotate(40 20 20)"/></g></svg>')
    print(f'Built {config["key"]}: {out}')


if __name__ == '__main__':
    main()
