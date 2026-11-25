# V5 validation and design decisions

## Changes
- Replaced workspace tabs with a single fixed screen, a map above the PCP, and the original collapsible filter rail.
- Moved scenario criteria, optional group highlight and PCP configuration into sidebar disclosures.
- Removed permanently displayed auxiliary visualizations and redundant inspectors; regional comparison, scatter plot, scenario outcomes and shortlist/inspection are contextual drawers. Only one may be open at once. The two main plots stay mounted.
- Compact chart legends, coverage counts and selection feedback; preserved fuel colors. Removed the fixed 560-pixel map figure height and use bounded responsive graph slots.
- Reduced crowded log-axis ticks by requiring separation in transformed coordinates; retain edge label safety.
- Scenario highlight is an overlay with a distinct amber legend, avoiding a feedback loop that would otherwise shrink the baseline. It does not modify linked selection or PCP brushing.

## Checks executed
- Offline smoke suite: component and callback IDs, all existing filters, data schema, exact plant selection, map–PCP brush semantics, shortlist and CSV export, and edge-safe PCP labels passed.
- V4 analytics regression: regional totals, all 36 scatter axis combinations, linked selection, scenario sets, evidence retention, all seven years and CSV exports passed.
- V5-specific suite: no tabs, map above PCP, both charts mounted, scenario criteria in rail, mutually exclusive drawer states, 26 exact default overlapping candidates highlighted without narrowing baseline, reset of display overlays passed.
- Search/empty-state, sidebar audit and fixed-viewport checks passed.
- Static HTML layout generated from the component tree with mocked Dash controls and checked in Chromium: viewport dimensions 1536×830, 1366×700 and 1920×950. Document dimensions matched each viewport; plot slots were non-overlapping and visible within the viewport (at least 150 px each); sidebar retained internal scrolling.

## Limits of verification
Dash could not be installed in the execution environment. Chromium also rejected WebGL context creation, so the static layout check verifies DOM geometry only, not actual visual rendering of map markers or PCP lines. Map tiles were disabled in the static offline check. The real Dash component instantiation, mouse interactions and full rendering must be checked locally. `tests/browser_check_v5.py` is supplied for real-browser smoke checks; it has not been executed here. Smaller desktop windows necessarily reduce chart heights; use full-screen mode or a higher-resolution display for the most readable multivariate view.

The two comparison strategies remain illustrative user-editable configurations. Missing evidence is not a declaration of unsuitability; agreement across two scenarios is not proof of retirement feasibility. No change to the dataset or screening formulas.
