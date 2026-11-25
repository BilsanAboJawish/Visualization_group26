# PlantScope V6 — validation and release gate

## Verified in this build

| Check | Result |
|---|---|
| Original filter, search, empty-state, shortlist and export callbacks | Passed offline |
| All 36 relationship-axis combinations, regional grouping, seven generation years | Passed offline |
| Scenario A threshold 2/5/10/38 Mt: 1587/687/199/0 candidates | Passed offline; exact overlay IDs |
| Default A/B overlap: 26 candidates | Passed offline |
| All six PCP field transforms, inverse values, tick spacing and extrema for every year | Passed offline |
| Native PCP reordering event and subsequent brush mapping | Passed simulated callback test |
| Prioritized display sampling and full-cohort membership | Passed offline |
| Zoom marker sizes/opacity, dimmed context and all selection IDs | Passed offline |
| Map world-copy suppression, camera fitting on initial/reset, preservation on data updates | Passed mock MapLibre adapter test; not a live map |
| Fixed-screen geometry, all eight collapsed groups visible, nonoverlapping map/PCP slots at 1366×700, 1536×830, 1920×950 | Passed static Chromium HTML/CSS check with mock controls |

No values or source records were changed. Historical commissioning dates of 1900 create three 121-year ages; very large generation-change percentages are retained and displayed on a signed compressed scale, not removed or capped. The source observations have not been independently validated.

## Required release gate on the actual running app

The build environment lacks Dash; Chromium also could not initialize WebGL. Therefore the complete running dashboard, tile rendering, actual pointer gestures, native Dash callbacks and live visual quality were not verified. The package is a submission candidate, not an unconditional certification of readiness.

Run `python tests/dash_runtime_check.py`, then start `python app.py`. Open the dashboard in a WebGL-enabled browser, hard refresh, and check:

1. At your normal browser zoom, map and PCP fit vertically without document scrolling; all collapsed sidebar groups are visible. Expand filters and verify only the sidebar scrolls.
2. Reset view: a single world appears without repeating continents. Zoom/pan; markers grow; check that a filter change does not cause unintended camera reset. Neutral margins are expected on wide/short map panels. Antarctic outliers can be reached by zooming/panning.
3. Drag a PCP axis and brush it; the correct criterion and exact matching map count appear. Clear brush restores the full eligible cohort. Check the dense CO₂ axis labels, 2 and 6 axes, overview/detailed and fuel emphasis.
4. Select a geographic region, compare the linked PCP cohort, clear the selection, inspect a plant, pin/unpin, and export the shortlist. Try an incompatible filter: retain empty basemap/axis skeleton with zero counts.
5. Open Scenario screening, edit A's CO₂ threshold 2 → 5 → 10 → 38 with the default fossil cohort and year 2017; see 1587 → 687 → 199 → 0 without pressing Enter, and verify the orange map overlay. Open Compare outcomes, inspect overlap, evidence and export.
6. Open Regional comparison and Relationships, use their selection actions and close each drawer. Verify no navigation or scrolling of the page itself.
7. Record evidence and actual findings for the six analytical questions in the report. Confirm course-specific submission requirements separately.

The optional `tests/browser_check_v5.py` checks the real map/PCP layout, MapLibre no-wrap flag, scenario editing, and drawers when Dash and Playwright/Chromium are installed.
