"""Scenario feedback checks against the actual dataset (offline callback tests)."""
from pathlib import Path
import runpy
parts=runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
app,dash,walk=parts['app'],parts['fake_dash'],parts['walk']
v=parts['values']; f=app.apply_filters(2017,*v)
A=[2,None,None,None,None,[]]; B=[.5,35,40,None,None,[]]
byid={c.id:c for c in walk(app.app.layout) if isinstance(c.id,str)}
assert all(byid[i.component_id].props['debounce']==.35 for i in app.SCENARIO_INPUTS if not i.component_id.endswith('strict'))
for threshold in (2,5,10,app.CO2_MAX):
    edited=[threshold,*A[1:]]
    content,h=app.scenario_sidebar(2017,*v,[],*edited,*B,'A matches')
    matches=f.loc[f.year_co2_mt.ge(threshold)]
    assert set(h['ids'])==set(matches.gppd_idnr)
    counts=content.children[0][1].children[0]
    assert counts[0].children[0][1].children==(f'{len(matches):,}',)
    figure=app.update_map(2017,*v,'fuel','capacity',[],{},[],app.DEFAULT['dimensions'],None,0,1.22,h)[0]
    overlay=[t for t in figure.data if t.name=='Scenario A matches']
    assert len(overlay)==bool(len(matches))
    if len(matches): assert set(x[0] for x in overlay[0].customdata)==set(h['ids'])
    print(f'[PASS] CO2 >= {threshold} Mt: {len(matches):,} matches; exact displayed count and map IDs')
content,h=app.scenario_sidebar(2017,*v,[],*A,*B,'B matches')
assert len(h['ids'])==76
content,h=app.scenario_sidebar(2017,*v,[],*A,*B,'Both')
assert len(h['ids'])==26
for trigger,current,expected in [('scenario-a-co2','off','A matches'),('scenario-b-cf','A matches','B matches'),('scenario-a-co2','Both',dash.no_update),('scenario-b-strict','B matches',dash.no_update),('reset-filters','Both','off')]:
    dash.ctx.triggered_id=trigger
    group,cluster=app.reset_display_overlays(1,*A,*B,current)
    assert group==expected
    assert cluster==([] if trigger=='reset-filters' else dash.no_update)
print('[PASS] Automatic map highlight follows edited strategy; explicit overlap stays selected; reset removes highlighting')
empty=list(v); empty[5]='unknown-plant-id'
_,h=app.scenario_sidebar(2017,*empty,[],*A,*B,'A matches')
assert h['ids']==[]
print('[PASS] Empty filter cohort yields no scenario markers')
