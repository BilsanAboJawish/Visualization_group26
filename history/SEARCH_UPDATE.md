# PlantScope V3 — search and empty views

Based on PlantScope_PCP_Fixed_V2. All prior filters, map/PCP modes and shortlist functionality are retained.

- Sidebar search is a searchable, clearable autocomplete. Enter at least two characters of a name or plant ID. Suggestions respect all other sidebar filters, are case-insensitive and show facility name, country, fuel, and unique ID. Choose a suggestion to filter to that exact facility and inspect it. Changing/clearing the facility search clears the prior geographic selection to avoid contradictory cohorts. Typing without choosing does not change the map or PCP. Clear the choice to restore results from the remaining filters. A selected facility that conflicts with another filter remains clearable but does not appear on the map or PCP.
- Comparison search uses the same ranked options, within the filtered and brushed cohort (including country searches).
- When no plants match, the basemap remains visible with no markers. When the PCP has no complete records, its labeled axis skeleton remains visible with no data lines or fabricated tick ranges. Counts and explanatory text remain outside the visualization. Facility generation history retains its time axis when observations are missing.

## Verification
`python tests/search_empty_states.py`, `python tests/sidebar_audit.py`, `python tests/viewport_contract.py`, and Python syntax compilation passed in the build environment. The first two include the full offline smoke suite. Real Dash/browser rendering was not tested because Dash is not installed in the build environment. To verify locally, run `python tests/dash_runtime_check.py` and `python app.py`, then type part of a plant name in the sidebar, select a suggestion, clear the search, and apply incompatible filters. Verify dropdown menus are not clipped and both empty canvases remain visible.
