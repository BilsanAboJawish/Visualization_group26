# V4 analytical acceptance notes

## Research tasks and implemented support

| Task | Interaction and evidence |
|---|---|
| Q1 Regional patterns | Stacked bars by continent, subregion or country; count, installed capacity, plant fuel composition or modeled CO₂; linked selection with map. |
| Q2 Relationships | Configurable pairwise scatter plot; full available pairs, Spearman rank association overall and by fuel; PCP for simultaneous multivariate inspection. |
| Q3 Environmental screening | Sidebar thresholds and full-cohort PCP brushing; map overlays show all selected/matching records, not a sample; facility inspection. |
| Q4 Trade-offs | Two editable screening configurations; overlap, counts, capacity, modeled CO₂ coverage/totals, medians, countries and evidence coverage. |
| Q5 Evidence sensitivity | Sequential retention chart and geographical comparison before/after strict evidence requirements; initial/strict summary columns. |
| Q6 Robust shortlisting | A-only, B-only and common qualifying groups; per-plant inspection, pinning, shortlist export, full scenario-status CSV. Robustness refers only to the two tested configurations, not arbitrary thresholds. |

## Reproducible default example (2017, all fossil facilities, no other filters)

- Base: 8,660 facilities.
- Scenario A: modeled annual CO₂ >= 2 Mt; other thresholds blank. 1,587 qualify.
- Scenario B: modeled CO₂ >= 0.5 Mt, age in 2021 >= 35 years, reported capacity factor <= 40%; other thresholds blank. 76 qualify.
- A only: 1,561; both: 26; B only: 50. Intersection / union: 26 / 1,637 = 1.59%.
- Strict evidence (valid reported generation in selected year, all five screening attributes present, no flagged anomaly) retains 337 of 1,587 initial A candidates (21.2%). These counts are derived from the bundled dataset, not policy recommendations.
- 3,255 of 8,660 plants have both modeled CO₂ and reported CF in 2017. Their Spearman association is approximately 0.87; these indicators share generation inputs, so the relationship does not establish causality.

## Analytical conventions

The scenario cohort includes all active sidebar filters and the linked selection. The PCP brush is deliberately excluded from scenario comparisons so its axis-specific complete-case restriction does not silently change scenario results. Both strategies evaluate exactly the same population and year. Missing values for enabled criteria produce insufficient evidence unless another known criterion fails. Strict evidence is an additional eligibility condition, not proof of technical unsuitability. No missing data are replaced with zero. CO₂ totals sum available values only; coverage is provided separately. Median statistics use available observations. Age refers to 2021. Historical generation change compares earliest/latest usable observations; it does not imply continuous decline. CO₂ is modeled, not measured. Historical plant data cannot establish present-day operation or actual retirement feasibility.

## Live acceptance checklist (not executed in the build environment)

1. Run `python tests/dash_runtime_check.py` with your installed environment. Start the app and confirm the three tabs load without errors.
2. At your laptop resolution, check the map, map+regions, regions-only and PCP/relationship toggles; all controls should be usable without document-level scrolling. The scenario workspace intentionally scrolls internally.
3. Click a region/fuel bar; verify the selected IDs/count, map highlight and PCP cohort. Clear linked selection. Draw a scatter lasso, apply and verify the same IDs on the map and PCP. Check an empty filter and a missing-data-only cohort.
4. Change scenario thresholds and the strict evidence checkbox. Compare default values above, click each overlap bar, choose a plant and pin it. Export CSV and inspect membership/status fields. Change year and verify that the two scenarios continue to share the same cohort/year.
5. Recheck basemap tile availability, chart resizing and small-screen readability. Review task wording and actual findings with the target users / course rubric before final submission.

## Validation scope

The offline suites verify component IDs/callback references and real data/figure computations, including all 36 scatter axis combinations, regional aggregation, linked selection IDs, scenario partitions and overlap, evidence steps, export, search and empty views. They do not execute Dash's client renderer, real callback scheduling, browser layout, or mouse-event dispatch. Dash could not be installed in the build environment. The current configuration supports two editable scenario slots and session persistence, not a general saved multi-scenario library. The analysis guide provides instructions, not automatic filter presets. Regional comparison does not calculate a separate screening-rate metric; the evidence view covers geographic retention, and the map shows filtered/selected candidates.
