# Motion asset provenance

Original reference geometry comes from the approved Amplifier Smart Tools website design.
Unfold authored and rendered the original motion using Gemini gemini-3.7-flash, HyperFrames 0.8.33, and GSAP 3.14.2.
FFmpeg cropped the caller-owned 1280x720 exports to the central 720x720 square without changing timing.
Outtake produced the looping GIFs through its public plan/render operations.
PNG stills were decoded from the corresponding square MP4s.

Both loops are silent and return to their initial geometry. The title mark is 8 seconds; the illustration is 16 seconds.
The page respects reduced-motion preferences and offers a shared pause control.
Frame sampling, decoded-frame checks, and browser review do not imply user approval of the design.

## Illustration

Unfold authored and rendered this 16-second composition using circular-track
vertex animation. Three nested irregular shapes spin in alternating directions,
then decelerate and lock into squares. Circular tracks fade before the complete
eight-second gold-logo cycle. The title logo asset is unchanged.

Polygon radii are 314, 205, and 98 pixels. Maximum corner gaps are 94, 105,
and 120 degrees. Shared angle easing bounds all interpolated gaps, keeping
outer edges clear of the full inner tracks and their markers. Matching green
and gold trajectories also prevent crossing during color transitions.

The initial brief is in `plate-brief.json`; the latest refinement is in
`plate-refinement.txt`. Animation is authored by Unfold and converted by Outtake.

Unfold revision: `824af5ed63f34012bb0de273e6fd0eb7`.
Unfold artifact: `b7a32d22df284042b09baf3bd666be72`.
Outtake artifact: `export_74c3415253c846a3be18c007aac33374`.
GIF SHA-256: `5fb81e091bd0feca07e21df41355146c32fc6ba30be1b9f8627689281e9c5046`.
Dimensions: 600 x 600. Frame rate: 20 fps. Duration: 16 seconds.

## Title mark

Unfold revision: `8b5717f9e09e4cf4a4facbc7a8f07a0c`.
Unfold artifact: `6787230965e946c1899f12c0e599b571`.
Outtake artifact: `export_3734555551a6475dac9d4adf88ce6b5d`.
GIF SHA-256: `5d56ab191e9da10c3e1505e5809cc171d5e255747797101a5f71b6ee9121206e`.
Dimensions: 160 x 160. Frame rate: 20 fps.
