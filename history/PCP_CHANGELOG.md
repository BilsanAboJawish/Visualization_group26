# PCP-focused upgrade — 25 November 2026

This package is based on the last working **PlantScope_ViewportLocked** release.

**Unchanged:** world map, filter fields and their semantics, sidebar, navigation, viewport lock, inspection/search, shortlist, CSV export, data model, and CO₂ scenario calculations.

## Only the comparison plot and its controls have changed

1. Logarithmic presentation of nonnegative, highly skewed columns: capacity (MW), selected-year generation (GWh), and illustrative modeled CO₂ (Mt). The axes explicitly say *log scale* and show tick labels in real units. Age, reported capacity factor, and reported generation change remain linear. No underlying values are converted in the filtered dataset or exports.
2. Brushing on a transformed axis converts selected Plotly display-space intervals **back into the original units** before testing the full complete-case cohort. The displayed lines are a visualization sample, not the selection population.
3. Deterministic visual sampling stratified by fuel and capacity bands. Default **Overview** has 100 lines; **Detailed** has 180. Switching modes never changes the cohort or analytical filters.
4. **Emphasize fuel** controls the visual priority of the fuel lines; it does not filter plants. Real filter options remain in the left sidebar.
5. **Clear brush** clears both the brush state and actual plot selection. Match counts report the whole eligible population.
6. More explicit coverage note distinguishes total cohort, complete cases, missing-axis cases, and drawn lines.

## Dataset caveats

The WRI plant dataset is historical (June 2021 release). 2017 modeled CO₂ is a scenario based on energy and fuel assumptions, **not actual measured emissions**. Missing data stays missing. A user can choose other axes to include plants excluded by complete-case requirements. Data points in the visual sample may be enriched by capacity strata to show the distribution, so they must not be used to infer frequency from line counts.

## Verification status

- `python tests/offline_smoke.py` checks data/plot construction, original-unit brushing, color emphasis, clearing, existing callbacks, and shortlisting.
- `python tests/viewport_contract.py` checks the previously frozen viewport contract.
- `python tests/dash_runtime_check.py` requires the locally installed Dash runtime (the sandbox could not install Dash).
- **Still required:** actual browser interaction test with the user's installed Dash and WebGL-capable browser.

## Manual acceptance check

1. In **Compare & shortlist**, confirm the plot has 3 readable axes by default. Capacity and CO₂ have logarithmic real-unit ticks; age is linear.
2. Change **Overview** to **Detailed**; only the rendered-line counter should change, not the complete-record counter.
3. Select **Coal** in Emphasize fuel; coal lines become visually stronger but the comparison cohort count stays the same.
4. Drag a capacity-axis brush; the match count must update, and a matching plant must be searchable in the inspector. Note selected values in real MW.
5. Click **Clear brush**; both highlight and match count reset.
6. Switch to **Explore**, adjust a country filter, then return to Compare and check cohort update.
7. Ensure no document scrollbar appears and the map/sidebars still work.

If the new plot fails to render, stop the process and run the previous `PlantScope_ViewportLocked` package as a safe fallback.
