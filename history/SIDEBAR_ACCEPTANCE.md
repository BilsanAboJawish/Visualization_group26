# Sidebar release gate — objective acceptance criteria

- [ ] On a 1366–1536 px laptop viewport, filter labels are readable and all dropdowns are clickable.
- [ ] The left rail is independently scrollable; the map and PCP remain unaffected.
- [ ] No results or “current scope” card consumes space above the filter groups.
- [ ] Geography and Fuel & capacity are initially open; other groups open on click and can be navigated using keyboard.
- [ ] Reference year is selectable in Generation and changing it updates the maps/PCP.
- [ ] With Fossil selected, primary fuels not in the fossil category are disabled.
- [ ] With year 2019, model-estimated generation provenance options are disabled.
- [ ] Age / capacity-factor / CO₂ / generation ranges cannot affect data until explicitly enabled.
- [ ] Reset all restores default fuel group, year, ranges, and search text.
- [ ] Map clicking, PCP brushing, pinning a facility, and exporting its CSV still work.

**Release decision:** keep this version only if all criteria pass; otherwise use the previously tested `PlantScope_Submission_Polished` without further broad redesign.
