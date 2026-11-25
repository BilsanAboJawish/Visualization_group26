# PlantScope PCP — targeted visual and interaction corrections

## Scope and rollback

This release was derived from `PlantScope_PCP_Improved.zip`. Changes are limited to PCP labels, plot margins, line palette, interaction tests, a short build identifier, and in-panel scale guidance. The existing map, sidebar, filtering, inspector, one-screen layout, shortlist, and export logic are unchanged.

## Issue 1 — Rightmost PCP axis clipped

- Replaced long axis captions, including `Modeled CO₂ · Mt · log scale`, with compact labels such as **CO₂ scenario (Mt)**. Logarithmic display is explained beside the controls; tick marks remain in original units.
- Reserved more space around edge axes by changing the Plotly Parcoords x-domain from `[0.055, 0.97]` to `[0.105, 0.845]`; the plot remains responsive within its container.
- Tests assert the labels, axis domain, original-unit ticks, and retained full-cohort ranges.

## Issue 2 — Overlapping lines

- Adjusted the all-fuels colors from about 30% opacity to **19%**; selected fuel emphasis remains stronger at 62%, while other fuels are subdued.
- Unselected lines during brushing are further de-emphasized (3.5% opacity).
- Retained both sampling modes (100 overview / 180 detailed), fuel emphasis, deterministic stratified sampling and the log(1+x) scaling of highly skewed axes. This change reduces clutter without discarding eligible plants from the brush calculation.

## Issue 3 — PCP interaction quality

The automated test now exercises the *callback contract*, not only the individual numeric filter: it simulates the actual Plotly `restyleData` payload for a two-axis brush, runs the Dash brush callback, checks the brush count, checks the map overlay and inspection cohort, then checks clearing both a single axis and all brushes.

For the default **2017** fossil cohort, the reproducible test reports:

| Measure | Count |
|---|---:|
| Sidebar-filtered plants | 8,660 |
| Eligible on all three default PCP axes | 6,100 |
| Missing at least one axis value | 2,560 |
| Example 2-axis selection | 288 |

The sample brush is capacity 7.3–22.5 MW and modeled CO₂ about 0.010–0.670 Mt; these are *test intervals*, not suggested decommissioning thresholds. The selected 288 come from the **6,100 eligible records**, not the 100 visual lines.

## What was and wasn't verified

**Verified in Python:** source-code compilation, complete offline callback/data smoke suite, axis and layout invariants, two-axis brush transform, brush count, map linkage, inspection-scope linkage, clear-brush update and shortlist regression checks.

**Not verified in a real Dash browser here:** live mouse dragging/Plotly `restyleData` emission and visual clipping. Dash is unavailable in the container, and the headless Chromium environment cannot initialize the WebGL-based Parcoords rendering. Therefore, a user-side browser check remains necessary.

## Two-minute live acceptance test

1. Launch the app and open **Compare & shortlist**. Confirm the build subtitle **PCP FIXED · V2**, and that the rightmost **CO₂ scenario (Mt)** label is entirely visible.
2. Drag vertically on the capacity axis to brush a nontrivial range. The **PCP brush summary must change from “No brush active” to a number of matches**. The map must highlight the matching cohort; lookup choices should be scoped to the brush.
3. Click **Clear brush**. The brush handles must disappear, the summary must read “No brush active”, and the map must remove its PCP highlight overlay.
4. Switch **Emphasize fuel** and **Overview/Detailed**. Verify the eligible-record count stays constant, even if the visual sample changes.

If any of the four checks fail, use the previous `PlantScope_PCP_Improved.zip` unchanged as the rollback version and report the failing step.
