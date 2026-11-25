# PlantScope — Single Workspace (V6 submission candidate)

A fixed-screen visual decision-support dashboard for preliminary fossil-fuel power plant screening. Built from V4 using the same WRI-derived historical dataset and analytical functions.

## Run on Ubuntu

Extract the ZIP into a new folder. Stop any previous PlantScope server with Ctrl+C. In the extracted folder, activate your existing virtual environment (or create one and install requirements), then run:

```bash
cd PlantScope_Submission_V6
# If needed, create and activate a new environment:
# python3 -m venv .venv
# source .venv/bin/activate
# pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8050/ and hard refresh (Ctrl+Shift+R). Internet access is needed for the basemap tiles; Chromium/Firefox must support WebGL for the map and PCP. The data files are bundled.

## One-screen workflow

- The map is always above the PCP. No workspace tabs, page switching, page-level scrolling, or navigation slider. The filter rail scrolls independently; contextual drawers scroll internally when necessary.
- Use the original sidebar filters and plant-name/ID autocomplete. Click a map marker to inspect its record; lasso or box-select plants to define the PCP cohort. Clear selection returns to the filtered cohort.
- Brush PCP axes to highlight all matching complete records on the map, not only the plotted sample. PCP settings (dimensions, order, line density and fuel emphasis) are in the sidebar. Clear brush resets the brush. The coverage strip distinguishes all cohort records, complete records, missing-axis records, and displayed lines.
- Expand **Scenario screening** in the sidebar. Edit A/B criteria (blank means unconstrained), view the qualifying counts, and optionally highlight A-only, both, or B-only facilities on the map. The scenario highlight is an overlay, not a selection/filter; it does not change the comparison denominator. Scenarios use current filters and linked selection, excluding PCP brushes, for a common fossil-plant cohort.
- Click **Compare outcomes** for a contextual drawer containing candidate overlap, inspection, trade-off table, evidence sensitivity and scenario CSV export. Only one drawer is open at a time. Close it to restore the unobstructed view; both primary charts remain mounted and no page navigation occurs.
- Use **Regional comparison** on the map or **Relationships** on the PCP to open optional charts. Click a regional bar segment or apply a scatter selection to define the same linked cohort. A new linked selection clears incompatible PCP constraints. Use the drawer close button to return focus to the two primary charts.
- Inspect plants and pin them to a browser-local shortlist; open Shortlist in the header to review or remove saved facilities and Export to download CSV. Scenario thresholds persist for the browser session. Reset filters restores the normal filters, PCP display settings, linked selection, and scenario highlight, but does not delete the saved shortlist or overwrite the independently editable scenario thresholds.

## Scientific limitations

Historical data, modeled CO₂ (not actual emissions), incomplete plant characteristics and generation history. Missing information is not zero. Screening thresholds are analyst-selected illustrative criteria, not recommendations to retire facilities. Robustness here means agreement between two tested configurations, not universal robustness. Evidence quality indicators do not independently verify the data.

## Verification

```bash
python tests/single_workspace_v5.py
python tests/analytics_v4.py
python tests/search_empty_states.py
python tests/sidebar_audit.py
python tests/viewport_contract.py
python tests/dash_runtime_check.py
```

The offline tests use stub Dash components but real pandas/Plotly calculations. The last command requires actual Dash. Run the optional browser QA script on an installed local app to check the real DOM and drawers (requires Playwright and a Chromium installation):

```bash
# In another terminal while app.py is running:
# pip install playwright
# playwright install chromium
python tests/browser_check_v5.py
```

See V5_VALIDATION.md for the tested results and limitations. Full live Dash/WebGL rendering was not possible in the build environment.

### V5.1 — Live scenario feedback

Open Scenario screening in the sidebar. The live result summary is above the threshold editors and reports A matches, B matches, their intersection and insufficient-evidence counts. Threshold edits commit after a 0.35-second typing pause (server processing adds latency). There is no Apply button. Editing A or B automatically selects the corresponding full match set on the map unless an explicit exclusive/overlap group is selected. Orange markers and the map legend show the selected scenario group; the original filtered population remains as context. A zero result has no orange markers. Compare outcomes opens the existing detailed analysis drawer. Reset filters clears the map overlay; scenario thresholds remain session-persistent as in V5.

Offline validation: `python tests/live_scenarios.py`, `python tests/single_workspace_v5.py`, `python tests/analytics_v4.py`. The optional browser test (`tests/browser_check_v5.py`) now checks the no-Enter update and map legend; it requires a running Dash installation and Chromium. It has not been executed in the build environment. The V6 section below describes the subsequent visual refinements.

## V6 — Submission candidate

This version retains the V5.1 single-page workflow and live scenarios, with no extra permanent charts or navigation. All sidebar sections start collapsed and follow the workflow from geography and fuel to evidence, scenarios and visual settings. The Reset filters button resets the main filters, brush, linked selection and map overlay, not independently saved scenario thresholds or the shortlist.

- The map's MapLibre world-copy setting is disabled by a browser asset, and Reset view fits one world rather than wrapping longitude. There may be neutral margins around the global map on wide screens; zoom and pan to inspect local regions. Smaller overview markers, zoom-aware opacity and dimmed context reduce congestion. All matching IDs remain in the overlays. The CARTO basemap still requires internet access.
- PCP uses pre-blended RGB lines rather than relying only on alpha, and stronger colors for emphasized or brushed records. At most five spaced tick labels per axis; log1p transforms preserve zero (CO₂ pivot 0.01 Mt); generation change uses a signed log1p transform with a 100 percentage-point pivot. Real-unit ticks and inverse brush transforms preserve the actual numerical criteria. The historical age label explicitly references 2021. Extreme source observations are retained; they are not verified commissioning dates or necessarily comparable across reporting conventions.
- The displayed sample remains limited to 100 overview / 180 detailed lines. A brush reserves up to 80% of the budget for matching plants, using the remainder for context; all complete cohort records determine membership and map highlights. Axis reordering is synchronized with the server; reorder clears any previous brush.
- Live scenarios preserve V5.1's automatic map feedback and exact counts; orange highlights represent the chosen scenario group, not a ranking or retirement recommendation.

### Final validation

Run the existing offline suites and the new tests:

```bash
python tests/submission_v6.py
python tests/live_scenarios.py
python tests/single_workspace_v5.py
python tests/analytics_v4.py
python tests/search_empty_states.py
python tests/sidebar_audit.py
python tests/viewport_contract.py
node tests/map_camera_v6.js  # optional Node.js test of the map adapter
```

All these offline checks passed in the build environment. Static HTML/CSS geometry passed in Chromium at 1366×700, 1536×830, and 1920×950 using mocked Dash controls without rendering WebGL charts. See `SUBMISSION_VALIDATION.md` for the remaining real-browser release gate. The installed Plotly version used to validate figures was 6.5.2. For reproducible map internals, use the pinned tested Plotly version in requirements.txt.

### V6.1 contrast refinement
Default PCP colors use 76% original fuel-color strength rather than 38%; brushing and fuel emphasis retain full-strength focus colors with muted context. Global map marker opacity increases to 68%, retaining adaptive sizes and selection dimming. The map camera is unchanged; the live V6 screenshot showed clipped southern regions, which still requires browser-level validation. Offline contrast and V6 regression tests pass.

### V6.2 map visibility refinement
The map restores V5.1's larger capacity-scaled and uniform marker diameters. Default marker opacity is 82% at overview, 90% at medium zoom and 96% at local zoom. Selection overlays are larger; background markers still dim to 40% of their normal opacity during active matches. The fuel palette, PCP, map camera and one-page layout are unchanged. Test with `python tests/map_visibility_v6_2.py`; real browser appearance remains a manual validation item.
