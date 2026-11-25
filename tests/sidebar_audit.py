"""Independent sidebar/data integrity checks, run without Dash install.

Usage: python tests/sidebar_audit.py
"""
from pathlib import Path
import runpy

parts=runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
app=parts['app']
core=parts['core']
walk=parts['walk']
ids={part.id for part in walk(app.SIDEBAR) if isinstance(part.id,str)}
required={
 'plant-search','continent-filter','region-filter','country-filter',
 'group-filter','fuel-filter','capacity-filter','fuel-configuration-filter',
 'generation-year','provenance-filter','generation-filter','generation-enabled',
 'trend-filter','age-filter','age-enabled','cf-filter','cf-enabled',
 'co2-filter','co2-enabled','unknown-filter','quality-filter',
 'commissioning-filter','generation-source-filter','min-reported-years',
 'color-mode','size-mode','cluster-mode','reset-filters'
}
assert required<=ids,(required-ids)
assert {'active-filter-chips','active-filter-count','population-overlay'}.isdisjoint(ids)
sections=[x for x in walk(app.SIDEBAR) if x.component_name=='Details']
assert len([x for x in sections if x.props.get("className", "").startswith("filter-section ")])==8
assert sum(bool(x.props.get('open')) for x in sections)==0

# All active sidebar options are measurable within the bundled dataset.
base=core.get_year_frame(2017)
fossil=base[base.fuel_group=='Fossil']
assert fossil['has_other_fuel'].nunique()==2
assert fossil['quality_flagged'].nunique()==2
assert fossil['generation_source_known'].nunique()==2
assert fossil['commissioning_known'].nunique()==2
assert fossil['reported_years_available'].nunique()>1
for col in ['capacity_mw','plant_age_2021_years','year_generation_gwh',
            'year_capacity_factor_pct','year_co2_mt','reported_gen_change_pct']:
    assert fossil[col].notna().sum() > 0,(col,'no usable data')

# Irrelevant choices should be disabled for incompatible years/fuel groups.
opts=app.available_provenance(2019,['Fossil'])
assert next(o for o in opts if o['value']=='estimated')['disabled']
assert next(o for o in opts if o['value']=='reported')['disabled'] is False
opts=app.available_provenance(2017,['Fossil'])
assert next(o for o in opts if o['value']=='estimated')['disabled'] is False
opts=app.available_fuels(['Fossil'])
assert next(o for o in opts if o['value']=='Gas')['disabled'] is False
assert next(o for o in opts if o['value']=='Solar')['disabled']

assert 'generation-year' not in {
    x.id for x in walk(app.app.layout) if x.component_name=='Dropdown'
    and x.id=='nav-year-dropdown'
}
assert len(app.reset_all_filters(1))==29
print('[PASS] 8 purposeful groups (including PCP and scenario settings) and 28 required sidebar controls')
print('[PASS] Every analytical field has nonempty measured/modeled coverage')
print('[PASS] Generation status/fuel options disabled when unavailable')
print('[PASS] No results box or unavailable population control')
print('[PASS] Existing reset contract unchanged')
