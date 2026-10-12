# Website

This repository's promotional page uses the Amplifier Smart Tools family theme.
Product page content lives in `site.json`. The canonical theme is maintained in
`microsoft/amplifier-smart-tools/site/theme`; this repository carries a versioned
copy so a build does not depend on a moving remote theme or an online service.
Theme version: 0.1.0. Theme code is MIT licensed.

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
and individual tool listings belong in the catalog.

Use plain punctuation, with middle dots permitted between Math, AI, Design, and
Engineering in the team name. Keep MADE and Microsoft Office of the CTO as text
attribution. Do not link to the internal team site. Preserve the shared navigation,
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
Entries without a listing automatically appear under Other and remain searchable by Name and Category. Other is a built-in fallback grouping, not a registry category. Without a registry, the renderer keeps legacy output and does not add category or recommendation controls.

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
not renew the designation. Recommended is a plain, noninteractive badge. Source revision
and refresh details remain in the existing optional “Full description and source”
disclosure; the badge does not expand or link to recommendation-specific copy.

The catalog places Recommended above All tools. Each effective recommendation appears
once in Recommended as a shortcut and once in All tools as part of the complete catalog;
the two regions contain 24 card instances for 22 unique source listings. The All tools
count and global result count are based on those 22 unique listings, not the rendered
card total. The Recommended region is hidden whenever no matching effective
recommendations exist, including on the initial server-rendered page, and has no
empty-state placeholder. All tools are grouped by category by default or can be shown
in one global alphabetical Name list.

One control bar sits above all results: Search, Category, Platform, Sort by (Category or
Name), and one Clear filters action. Search, category, and platform filter both copies;
sorting changes only All tools, and clearing filters preserves the selected sort. Category
scopes remain registry metadata and are not inserted into the control bar or displayed
when a category is selected. The Other option and group appear only when at least one current
entry lacks classification. Native select controls keep their dimensions as values change. At
phone widths, Search spans the bar, Category and Platform share a two-column row, and Sort
by and Clear filters share the next row. Category labels remain visible on every card and
searchable with displayed tool names.

The all-results count is a live status for unique All tools listings; Recommended and All
tools have separate counts. When no listing matches, one global empty message replaces
section-specific empty messages. Without JavaScript, the filter bar and Name list stay
hidden, all 22 unique listings remain visible in All tools along with the two featured
shortcuts, and a zero-card Recommended region is hidden. Ordinary category group headings
are noninteractive, with no second category-navigation area.

With a category registry, every card names its category. Recommended shortcuts use the
section heading instead of a redundant “Recommended” badge; their All tools copies show
that badge. Stale designations retain “Recommendation needs review”; ordinary cards have
no recommendation-status badge. Cards without a listing show “Category: Other.” Even without snapshots or JavaScript, these entries remain readable. A legacy catalog without a registry keeps its existing card markup.

Tool creators do not nominate or select entries; catalog maintainers make those
decisions. Submissions are source-only and category-agnostic: submitters do not add, choose, or create categories or recommendations and need not know category definitions. Maintainers assign classification from the approved registry in separate metadata, never upstream manifests or source pointers. Category additions, label changes, and scope changes require their separate review and approval.

### Maintainer recommendation review

The normative maintainer roles and designation, renewal, replacement, and withdrawal
procedures live in the catalog's
[maintainer curation guide](https://github.com/microsoft/amplifier-smart-tools-catalog/blob/main/docs/maintainers.md).

`site/sync_theme.py` copies the helper with the renderer, CSS, JavaScript, family registry, license, and shared motion assets. Review the synchronized diff and run a build in the target catalog before adoption; do not update only a vendored theme copy.

## Site tests

Run deterministic Python renderer/metadata tests and the JavaScript filter harness from the repository root:

```sh
uv run --with pytest --with-requirements site/requirements.txt pytest site/tests/ -q
node --test site/tests/test_filters.cjs
```

The Python suite also checks legacy rendering, emitted assets, and theme sync. The Node harness executes the production script against a minimal DOM; it is not a browser layout or supported-host trial. Run browser and read-only host discovery scenarios separately before making those claims. CI runs these checks alongside the existing conformance kit tests.

## Motion assets

The shared title mark uses an eight-second looping GIF with a static PNG fallback.
The overview illustration has a pause control that also pauses its title mark. Reduced-motion
preferences select the still image by default. Shared media lives in
`site/theme/assets/` and is included by the theme sync script. The original briefs
and generation provenance live in `amplifier-smart-tools/site/artwork/`.

## Specification reader

The build renders the six Markdown chapters in `spec/` into a local reader at
`spec/index.html`, with chapter navigation, heading links, and source links.
The repository specification remains the source of truth. Changes under `spec/`
trigger the Website build; publishing the updated site remains explicit.

The square overview illustration lives in `site/assets/`. Unfold authors and renders the animation from the approved artwork. Outtake
converts the square export to an inline GIF.
See `site/artwork/README.md` for provenance and the retained MP4 masters.

## Tool demo videos

Tool pages may set `video` to a repository-relative MP4 path. With video present,
`image` is the poster, and the existing dimensions, alt text and caption describe
the demo. The player supports native controls and muted looping playback.
The shared motion toggle controls both GIF branding and demo playback; reduced
motion disables initial playback. Without JavaScript, native video controls remain
available. Sync the theme to an explicit tool checkout to adopt this capability.
