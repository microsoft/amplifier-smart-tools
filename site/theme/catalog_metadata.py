"""Catalog-owned editorial metadata and recorded source identity. No tool execution.

Shared by the renderer and catalog CI. Missing editorial files are legacy data;
invalid files raise ValueError, never an endorsement.
"""
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
COMMIT = re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})')


def text(value, field, multiline=False):
    if (not isinstance(value, str) or not value.strip() or
            any(unicodedata.category(c).startswith('C') and
                not (multiline and c in '\n\r\t') for c in value)):
        raise ValueError(f'{field}: expected a nonempty string without control characters')
    return value


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('Expected a lowercase hyphenated identifier')
    return value


def relative_path(value):
    text(value, 'path')
    if value == '.':
        return value
    if (value.startswith('/') or any(c in value for c in '\\%:?#') or
            any(p in ('', '.', '..') for p in value.split('/'))):
        raise ValueError('Expected a safe repository-relative path')
    return value


def repository(value):
    text(value, 'repository')
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or
            parsed.username is not None or parsed.password is not None or
            parsed.query or parsed.fragment or
            any(c.isspace() for c in value) or
            not re.fullmatch(r'[A-Za-z0-9.-]+(?::[0-9]+)?', parsed.netloc)):
        raise ValueError('Expected a credential-free HTTPS repository URL')
    if (any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?', label)
            for label in parsed.hostname.split('.')) or
            (parsed.port is not None and not 1 <= parsed.port <= 65535) or
            relative_path(parsed.path.removeprefix('/')) == '.'):
        raise ValueError('Invalid repository host, port, or path')
    return value


def commit(value):
    if not isinstance(value, str) or not COMMIT.fullmatch(value):
        raise ValueError('Expected a full lowercase source commit')
    return value


def ref(value):
    text(value, 'ref')
    if (any(c.isspace() or c in '~^:?*[\\' for c in value) or
            any(s in value for s in ('..', '@{', '//')) or
            value == '@' or value.startswith(('/', '-')) or value.endswith(('/', '.')) or
            any(p.startswith('.') or p.endswith('.lock') for p in value.split('/'))):
        raise ValueError('Expected a safe source ref')
    return value


def closed(data, required, optional=()):
    if (not isinstance(data, dict) or not set(required) <= data.keys() or
            data.keys() - set(required) - set(optional)):
        raise ValueError('Missing required fields or unknown metadata keys')
    return data


def checked_path(path, root):
    """Reject file and directory symlinks, including dangling links, before reads."""
    path, root = Path(path).absolute(), Path(root).absolute()
    if not path.is_relative_to(root):
        raise ValueError('File must belong to the catalog')
    if '..' in path.relative_to(root).parts:
        raise ValueError('File must not escape the catalog')
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('Catalog files and directories must not be symlinks')
        if part == root:
            break
    return path


def read_json(path, root):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def invalid_constant(_):
        raise ValueError('Invalid JSON constant')

    path = checked_path(path, root)
    if not path.is_file():
        raise ValueError('Expected a regular JSON file')
    return json.loads(path.read_text(encoding='utf-8'),
                      object_pairs_hook=unique, parse_constant=invalid_constant)


def validate_pointer(data):
    closed(data, ('repository',), ('ref', 'path'))
    return {'repository': repository(data['repository']),
            'ref': ref(data.get('ref', 'main')),
            'path': relative_path(data.get('path', '.'))}


def validate_provenance(data):
    if not isinstance(data, dict) or not isinstance(data.get('source'), dict):
        raise ValueError('Missing provenance source')
    source = closed(data['source'], ('repository', 'ref', 'path', 'commit'))
    repository(source['repository'])
    ref(source['ref'])
    relative_path(source['path'])
    commit(source['commit'])
    original = relative_path(data.get('original_manifest_path'))
    if original.split('/')[-1] != 'SMART_TOOL.md':
        raise ValueError('Provenance must name SMART_TOOL.md')
    timestamp = text(data.get('last_success'), 'last_success')
    if datetime.fromisoformat(timestamp.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Snapshot refresh time must include a timezone')
    return data


def validate_domains(data):
    closed(data, ('domains',))
    if not isinstance(data['domains'], list):
        raise ValueError('domains must be a list')
    domains = {}
    for domain in data['domains']:
        closed(domain, ('id', 'label', 'scope'))
        identity = identifier(domain['id'])
        if identity in domains:
            raise ValueError('Duplicate domain identifier')
        text(domain['label'], 'label')
        text(domain['scope'], 'scope')
        domains[identity] = domain
    return domains


def validate_listing(data, domains):
    closed(data, ('domain', 'recommended'), ('reviewed_source',))
    try:
        domain = identifier(data['domain'])
    except ValueError as exc:
        raise ValueError(f'domain: {exc}') from exc
    if domain not in domains:
        raise ValueError(f'domain: Unknown domain {domain!r}; approved ids: {sorted(domains)!r}')
    if type(data['recommended']) is not bool:
        raise ValueError('recommended must be an explicit boolean')
    if data['recommended']:
        reviewed = closed(data.get('reviewed_source'), ('repository', 'path', 'commit'))
        repository(reviewed['repository'])
        relative_path(reviewed['path'])
        commit(reviewed['commit'])
    elif 'reviewed_source' in data:
        raise ValueError('An ordinary listing must not carry reviewed_source')
    return data


def catalog_sources(root):
    tools = checked_path(Path(root)/'tools', root)
    sources = []
    if tools.exists():
        for directory in sorted(tools.iterdir()):
            checked_path(directory, root)
            if not directory.is_dir():
                continue
            identifier(directory.name)
            source = checked_path(directory/'source.json', root)
            if source.exists():
                sources.append(source)
    return sources


def load_catalog_metadata(root):
    """Validate all editorial files and designation uniqueness before rendering."""
    root = Path(root)
    try:
        registry = checked_path(root/'domains.json', root)
        domains = validate_domains(read_json(registry, root)) if registry.exists() else None
    except ValueError as exc:
        raise ValueError(f'domains.json: {exc}') from exc
    listings, designated = {}, set()
    # Enumerate directories, not just pointers, so orphan listings cannot hide.
    tools = checked_path(root/'tools', root)
    for directory in sorted(tools.iterdir()) if tools.exists() else ():
        checked_path(directory, root)
        if not directory.is_dir():
            continue
        try:
            listing = checked_path(directory/'listing.json', root)
            if not listing.exists():
                continue
            identifier(directory.name)
            if domains is None:
                raise ValueError('Listings require domains.json')
            source = checked_path(directory/'source.json', root)
            if not source.is_file():
                raise ValueError('Listing requires a source pointer')
            data = validate_listing(read_json(listing, root), domains)
            if data['recommended']:
                if data['domain'] in designated:
                    raise ValueError('At most one recommendation designation per domain')
                designated.add(data['domain'])
        except ValueError as exc:
            raise ValueError(f'{directory.relative_to(root).as_posix()}/listing.json: {exc}') from exc
        listings[directory.name] = data
    return domains, listings


def recommendation_state(pointer, provenance, listing, snapshot_present=True):
    """Compare a listing validated by load_catalog_metadata with recorded identity.

    A stale designation remains occupied, but loses its badge and preference.
    """
    if not listing or not listing['recommended']:
        return 'ordinary'
    if not snapshot_present or not provenance:
        return 'needs-review'
    pointer = validate_pointer(pointer)
    source = validate_provenance(provenance)['source']
    reviewed = listing['reviewed_source']
    if (any(pointer[k] != source[k] for k in ('repository', 'ref', 'path')) or
            any(reviewed[k] != source[k] for k in ('repository', 'path', 'commit')) or
            (COMMIT.fullmatch(pointer['ref']) and pointer['ref'] != source['commit'])):
        return 'needs-review'
    return 'recommended'


def read_snapshot(directory, root):
    """Inspect recorded files only; do not import or launch upstream code."""
    import yaml

    manifest = checked_path(Path(directory)/'SMART_TOOL.md', root)
    provenance = checked_path(Path(directory)/'provenance.json', root)
    prov = validate_provenance(read_json(provenance, root)) if provenance.exists() else {}
    meta = {}
    if manifest.exists():
        if not manifest.is_file():
            raise ValueError('Expected a regular manifest file')
        raw = manifest.read_text(encoding='utf-8')
        match = re.match(r'\A---\n(.*?)\n---(?:\n|$)', raw, re.DOTALL)
        if not match:
            raise ValueError('Missing or unclosed YAML front matter')
        try:
            meta = yaml.safe_load(match[1])
        except yaml.YAMLError as exc:
            raise ValueError('Invalid manifest YAML') from exc
        if not isinstance(meta, dict):
            raise ValueError('Manifest front matter must be a mapping')
        for field in ('name', 'description'):
            text(meta.get(field), field, multiline=field == 'description')
        for field in ('platforms', 'use_cases'):
            if not isinstance(meta.get(field), list):
                raise ValueError(f'Invalid manifest {field}')
            for item in meta[field]:
                text(item, field)
    # Keep legacy rendering when only one half of a snapshot exists.
    return (meta, prov) if manifest.exists() and provenance.exists() else ({}, {})