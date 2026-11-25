"""Regression tests for autocomplete and empty visualizations (offline)."""
from pathlib import Path
import runpy
parts = runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
app, core, dash = (parts[k] for k in ('app','core','fake_dash'))
values = [
    ['Fossil'], [], [], [], [], None, [0, app.CAP_MAX], [],
    [], [0, app.AGE_MAX], [], [0,100], [], [0, app.CO2_MAX],
    'all', [], 'all', 'all', 'all', 0,
    [], [0, app.GEN_MAX], 'all'
]
frame = app.apply_filters(2017,*values)
row = frame.iloc[0]
pid = str(row.gppd_idnr)
opts = app.suggest_plants(pid.lower(),2017,*values[:5],*values[6:],None)
assert opts and opts[0]['value']==pid
assert str(row['name']) in opts[0]['label'] and str(row.country_long) in opts[0]['label']
assert app.suggest_plants('zzzz_no_matching_plant_zzzz',2017,*values[:5],*values[6:],None)==[]
assert app.suggest_plants('a',2017,*values[:5],*values[6:],None)==[]
values[5]=pid
assert app.apply_filters(2017,*values).gppd_idnr.tolist()==[pid]
dash.ctx.triggered_id='plant-search'
assert app.focus_plant(None,None,pid,[])==pid
assert app.focus_plant(None,None,None,[]) is None
assert app.save_map_selection(None,0,pid,None,0,0,None,"capacity",None,2017,*values[:5],*values[6:],[pid])==[]
print('[PASS] Case-insensitive suggestions, exact plant ID, clear, and geographic selection reset')
# Selected plant becomes incompatible with other active filters.
values[4]=['NOT A COUNTRY']
assert app.apply_filters(2017,*values).empty
opts=app.suggest_plants(pid,2017,*values[:5],*values[6:],None)
assert opts==[]
axes=app.DEFAULT['dimensions']
map_result=app.update_map(2017,*values,'fuel','capacity',[],{},[],axes,None,0,1.22)
assert map_result[1:6]==('0','0','0.0','0',[])
fig=map_result[0]
assert fig.layout.map.style=='carto-positron'
assert len(fig.data)==1 and fig.data[0].type=='scattermap'
assert all(v is None for v in fig.data[0].lat) and not fig.layout.annotations
for mode in ('fuel','provenance','co2'):
    empty_map=core.make_map(frame.iloc[:0],2017,mode)
    assert empty_map.data[0].type=='scattermap' and not empty_map.layout.annotations
pcp,_=app.update_pcp(2017,*values,[],axes,'All','overview',0,{})
assert len(pcp.layout.shapes)==len(axes)
assert [a.text for a in pcp.layout.annotations]==[core.PCP_AXIS_LABELS[k] for k in axes]
assert len(pcp.data[0].x)==0
assert app.search_for_inspection(pid,2017,[],{},axes,*values,None)==[]
print('[PASS] Empty map keeps basemap; empty PCP keeps axes; no fabricated marks or stale matching results')
# Non-empty cohort but missing every selected dimension: same axis skeleton.
missing=frame.iloc[:1].copy()
missing[axes[-1]]=float('nan')
eligible,meta=core.pcp_cohort(missing,[],axes)
assert meta=={'cohort':1,'eligible':0,'missing':1}
fig=core.make_pcp(eligible,axes,2017,eligible=eligible)
assert len(fig.layout.shapes)==len(axes) and len(fig.data[0].x)==0
print('[PASS] Missing-data-only cohort remains an empty PCP with correct coverage')
