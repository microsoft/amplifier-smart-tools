# Website

This repository's promotional page uses the Amplifier Smart Tools family theme.
Product page content lives in `site.json`. The canonical theme is maintained in
`microsoft/amplifier-smart-tools/site/theme`; this repository carries a versioned
copy so a build does not depend on a moving remote theme or an online service.
Theme version: 0.2.0. Theme code is MIT licensed.

## Build and preview

From the repository root, using Python 3.12 or later:

```sh
python3 -m venv .work/site-venv
.work/site-venv/bin/python -m pip install -r site/requirements.txt
.work/site-venv/bin/python site/theme/build.py --family-owner robotdad
python3 -m http.server 8000 --directory _site --bind 127.0.0.1
```

Open http://127.0.0.1:8000. Generated output belongs in `_site/` and is ignored.
The site is a static build; visitors need no Python runtime or account.

The `--family-owner robotdad` option points overview and catalog links at the
fork previews. Omit it for their Microsoft organization URLs. Individual tool
links retain their authors' owners. Keep the same setting across the family.
For a combined local preview, build each page with `--local --output` into a
shared preview directory named after its repository, then serve that directory.

## GitHub Pages

The Website workflow builds an artifact for relevant pull requests and main
updates. Publication is explicit: enable Pages with GitHub Actions as the source,
then run Website on the intended branch with `publish` checked and the correct
family owner. Branch previews need that branch allowed in the github-pages
environment's deployment rules. All linked family sites must be published before
cross-site navigation is live. No repository visibility changes are required by
this workflow; verify Pages availability for the repository's current plan.

A normal push only builds the artifact. It does not publish an unreviewed page.
Use the downloaded artifact or the local server to review before publication.

The `github-pages` artifact is retained for seven days; it is a downloadable
preview, not a live preview URL. Pull requests build GitHub's merge ref
(`refs/pull/<number>/merge`), not just the branch head, and never deploy.
To preview the exact source on a review branch once it is available in the
repository hosting the workflow, set the branch and the actual owner of the
family preview sites, then dispatch the build with publication disabled:

```sh
REVIEW_BRANCH='<review-branch>'
PREVIEW_OWNER='<owner-of-family-preview-sites>'
gh workflow run website.yml --ref "$REVIEW_BRANCH" -f publish=false -f family_owner="$PREVIEW_OWNER"
```

Verify the run's branch and commit, download its artifact, extract the contained
site archive, and serve it locally. A branch build does not update the live
GitHub Pages URL. Publication and repository/environment settings require
separate authorization.

## Shared identity

Use the full family name, Amplifier Smart Tools, as one masthead and footer
identity. The overview explains the format and how to build a tool; discovery
and individual tool listings belong in the catalog. The overview may name a few
tools in `featured` in `site.json`; each entry links to that tool's catalog page.

The overview's "What's new" list shows the five newest items from `news` in
`site.json` and from the blog. A `news` entry has a `date` (YYYY-MM-DD), a `label`,
a `title`, and an optional `tool` slug that links the title to that tool's catalog
page. Blog posts appear without an entry.

Use plain punctuation. The footer credit, "Developed by made at Microsoft", is the
only attribution. Do not link to the internal team site. Preserve the shared navigation,
layout, typography, paper background, and gold details; a tool may set its own
accent, content, and image in `site.json`.

Images are copied from the repository's existing `docs/images/` at build time.
Their existing provenance remains there. Screenshots are labeled as screenshots;
concept artwork is labeled as illustration. Add demo video only when reviewed
footage is available. Do not use a fake player over a still image.

To update a vendored theme, run the canonical `site/sync_theme.py` with an explicit
target checkout, review the diff, and build again. It updates only `site/theme/`.
Page content stays in the owning repository. The family link registry holds only
navigation identity; the catalog's tool inventory remains `tools/*/source.json`.

## Catalog categories and recommendations

The canonical renderer supports optional catalog-owned `categories.json` and
`tools/<slug>/listing.json`, without changing the Smart Tool manifest or source-pointer
format. The registry is `{"categories":[{"id":"stable-id","label":"Display name","scope":"Kind of work covered."}]}`.
A maintainer-owned listing requires a known primary `category`; the ordinary form is `{"category": "approved-id"}`. Optional `recommended` defaults to false in a normalized copy in memory, never by mutating input or rewriting files. A provided flag must be a strict boolean. False or omission prohibits `reviewed_source`; a true designation records the selected `repository`, distribution `path`, and full source `commit`.
Entries without a listing automatically appear under Other and remain searchable by Name and Category. Other is a built-in fallback grouping, not a registry category. Without a registry, the renderer adds no category or recommendation controls.

`site/theme/catalog_metadata.py` provides the shared validators for the renderer and
catalog CI: `load_catalog_metadata(root)` returns optional categories and validated
listings, `validate_pointer` applies ref/path defaults, `read_snapshot` inspects front
matter and provenance without executing upstream code, and `recommendation_state`
compares recorded identities. Import this helper from the synced theme in catalog CI
rather than copying its rules. Invalid metadata, unsafe paths, symlinks, credential
URLs, and multiple designations in one category fail the build. A designation needing
review still occupies its category.

An effective Recommended designation requires pointer repository/ref/path to match
snapshot provenance and reviewed repository/path/commit to match that provenance.
Missing snapshots or mismatched identities show “Recommendation needs review” and
remove recommendation preference without removing the entry or its category. Recommended
means catalog maintainers selected this tool as a preferred starting point for its
category at the recorded source revision. Selection is not certification or a claim that
specification conformance or task outcomes were checked. Any review results and scope
limitations are stated only when recorded. A snapshot is point-in-time; refreshing it does
not renew the designation.

Recommended sits above All tools as a row of
cards, one per effective recommendation, and is absent when there is none. All tools
is one list of every unique listing in name order: icon, name, the first sentence of
the manifest description, and Get. A recommended tool carries a "Recommended" label in the list.
A stale designation shows "Recommendation needs review" and has no card. A live status
for screen readers reports the number of matching unique listings.

Search and category chips sit above the results. Chips exist only for categories
that hold a tool, in label order, with Other only when an entry lacks classification.
Search matches names, descriptions, use cases, platforms, and category labels. While
a search or category is active, Recommended is hidden. When nothing matches, one
empty message offers to clear the search. At phone widths the chips scroll sideways
in one row. Category scopes remain registry metadata and are not displayed. Without
JavaScript, the search and chips stay hidden and every listing remains visible.

Get, the name, and the card all open the tool's catalog page at `tools/<slug>/`.
The page shows the icon, the name, one line of facts (category, platforms, publisher,
version), the first sentence, a prompt that asks an agent to install the tool from its
source, up to six use cases, and other tools in the same category. An entry without a listing shows the
category Other. An entry without a snapshot remains readable. A catalog without a
registry has no chips, no Recommended, and no Category fact.

Tool creators do not nominate or select entries; catalog maintainers make those
decisions. Submissions are source-only and category-agnostic: submitters do not add, choose, or create categories or recommendations and need not know category definitions. Maintainers assign classification from the approved registry in separate metadata, never upstream manifests or source pointers. Category additions, label changes, and scope changes require their separate review and approval.

### Maintainer recommendation review

The normative maintainer roles and designation, renewal, replacement, and withdrawal
procedures live in the catalog's
[maintainer curation guide](https://github.com/microsoft/amplifier-smart-tools-catalog/blob/main/docs/maintainers.md).

`site/sync_theme.py` copies the helper with the renderer, graphics module, CSS, JavaScript, family registry, license, and shared assets. Review the synchronized diff and run a build in the target catalog before adoption; do not update only a vendored theme copy.

## Site tests

Run deterministic Python renderer/metadata tests and the JavaScript filter harness from the repository root:

```sh
uv run --with pytest --with-requirements site/requirements.txt pytest site/tests/ -q
node --test site/tests/test_filters.cjs
```

The Python suite also checks rendering without a category registry, emitted assets, and theme sync. The Node harness executes the production script against a minimal DOM; it is not a browser layout or supported-host trial. Run browser and read-only host discovery scenarios separately before making those claims. CI runs these checks alongside the existing conformance kit tests.

## Site text

`site/theme/text.yaml` holds the wording of the overview site and the catalog site:
headings, button labels, the home page copy, the diagram labels, and the sentences in
`llms.txt`. A comment above each entry says where it shows. Change a value, build again,
and sync the theme so the catalog shows the same text.

Text that belongs to one site stays in that site's `site.json`: the page title and
description, the `featured` tools, and the `news` items. Blog posts are in `site/blog/`,
and the specification chapters are in `spec/`.

## Graphics and fonts

`site/theme/graphics.py` draws the family mark, line icons, the flow diagram, and one
glyph per tool, all as inline SVG. The mark is a wrench with a spark in its jaw; the
favicon follows the browser's light or dark color scheme. A tool's glyph and field
color are keyed by its catalog slug or page key; a tool without a glyph shows its
initial on a neutral field. Reality Check, Smart Tool Creator, and Digital Twin Universe
have their own artwork: a line drawing with one pastel part on an ink tile.

Instrument Sans, Geist Mono, and Pirata One ship in `site/theme/assets/fonts/` with
their Open Font License texts and are included by the theme sync script.

## Blog

Each post is a directory at `site/blog/<slug>/` with a `post.md` and its images beside it.
`post.md` starts with front matter, then the body in Markdown:

```
---
title: Post title
date: 2026-11-16
author: Author name
affiliation: Team or organization
summary: One or two sentences for the post list.
---
```

`affiliation` is optional. The build writes the post list to `blog/index.html`, newest
first, and each post to `blog/<slug>/index.html`. An image alone in a paragraph becomes a
figure, and an italic line directly after it becomes the caption. Images must be files in
the post directory. A post's header has a "Copy as Markdown" link; without JavaScript it
opens the post's Markdown copy.

## Markdown copies and llms.txt

The build follows the [llms.txt](https://llmstxt.org/) proposal so an agent can read the
site without parsing HTML. `llms.txt` at the site root gives a short description and links
to Markdown copies. Each specification chapter has a copy at `spec/<chapter>.md` (the
introduction at `spec/index.md`), and each post has one at `blog/<slug>/index.md`. Images
in a post's copy carry the post's full address, so they load from a pasted copy. A page
with a copy names it in a `rel="alternate"` link, and every page names `llms.txt` in a
`rel="describedby"` link. The catalog build writes its own `llms.txt` and one
`tools/<slug>/index.md` per tool.

## Specification reader

The build renders the six Markdown chapters in `spec/` into a local reader at
`spec/index.html`, with chapter navigation, heading links, and source links.
The repository specification remains the source of truth. Changes under `spec/`
trigger the Website build; publishing the updated site remains explicit.


## Tool demo videos

Tool pages may set `video` to a repository-relative MP4 path. With video present,
`image` is the poster, and the existing dimensions, alt text and caption describe
the demo. The player supports native controls and muted looping playback.
The motion toggle controls demo playback; reduced
motion disables initial playback. Without JavaScript, native video controls remain
available. Sync the theme to an explicit tool checkout to adopt this capability.
