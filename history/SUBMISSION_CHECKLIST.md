# PlantScope — 10-minute submission check

## Launch
1. Stop every previous server (Ctrl+C). In Ubuntu run `python app.py` from this folder using the configured venv.
2. Hard refresh the browser: Ctrl+Shift+R.
3. Confirm the map is **full height** (not a narrow strip). If not, stop and send the browser screenshot to troubleshoot.

## Must-pass interactions
1. Change Country (e.g. Netherlands), observe KPI and map change. Reset filters.
2. Choose a plant on the map. Plant inspector must show its ID, fuel and generation data provenance.
3. Switch Compare & shortlist; ensure PCP is full height, not blank. Brush an axis; matching count must change.
4. Look up a matching plant in the Compare inspector; pin it; ensure count increments.
5. Export shortlist and open CSV; ensure the chosen plant exists.
6. Reload page; pinned shortlist should persist in the same browser.

## Protect against deadline risk
- Keep the previous `PlantScope_Map_Repaired.zip` as fallback.
- Do not make new functional edits after completing this checklist.
- Modeled CO2 is not measured emissions; do not claim the plot proves suitability for shutdown.

## Notes
The package preserves the existing filters, callback IDs, data source and 560px map / 620px PCP dimensions. Dash cannot be launched in this build environment; browser testing is required on the target laptop.
