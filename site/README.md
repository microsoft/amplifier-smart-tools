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
