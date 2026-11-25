"""Verify all new analytical paths on the bundled actual data and edge cases."""
from pathlib import Path
import runpy
import pandas as pd
import numpy as np
parts=runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
app,core,dash=parts['app'],parts['core'],parts['fake_dash']
import analysis_tools as a
v=parts['values']; frame=app.apply_filters(2017,*v)
assert len(frame)==8660
for level in ('continent','region','country_long'):
    for metric in ('count','capacity','co2','share'):
        fig,note=a.regional_figure(frame,level,metric)
        totals=sum(sum(t.y) for t in fig.data)
        expected={'count':len(frame),'capacity':frame.capacity_mw.sum()/1000,'co2':frame.year_co2_mt.sum(),'share':100*frame[level].nunique()}[metric]
        assert np.isclose(totals,expected), (level,metric,totals,expected)
print('[PASS] Regional totals and fuel composition reconcile with raw data across three geographic levels')
fig,_=a.regional_figure(frame,'continent','count'); seg=next(t for t in fig.data if any(y>0 for y in t.y)); i=next(i for i,y in enumerate(seg.y) if y>0)
custom=list(seg.customdata[i]); dash.ctx.triggered_id='regional-chart'
selected=app.save_map_selection(None,0,v[5],{'points':[{'customdata':custom}]},0,0,None,'count',None,2017,*v[:5],*v[6:],[])
assert len(selected)==seg.y[i] and set(selected)==set(frame.loc[frame.continent.eq(custom[1]) & frame.primary_fuel.eq(custom[2]),'gppd_idnr'])
print('[PASS] Regional segment selects exact underlying facility IDs')
axes=list(core.PCP_FIELDS)
for x in axes:
    for y in axes:
        fig,note=a.scatter_figure(frame,x,y,log=True)
        assert sum(len(t.x) for t in fig.data)==int(frame[[x,y]].notna().all(axis=1).sum())
        assert all(np.isfinite(np.asarray(t.x,dtype=float)).all() for t in fig.data)
print('[PASS] All 36 axis combinations render with exact pairwise coverage, including zero values')
fig,_=a.scatter_figure(frame,'year_capacity_factor_pct','year_co2_mt')
points=[{'customdata':list(t.customdata[0])} for t in fig.data if len(t.x)]
dash.ctx.triggered_id='apply-scatter'
selected=app.save_map_selection(None,0,v[5],None,1,0,{'points':points},'count',None,2017,*v[:5],*v[6:],[])
assert set(selected)=={p['customdata'][0] for p in points}
cohort=app.analysis_cohort(2017,v,selected,app.DEFAULT['dimensions'],{})
assert set(cohort.gppd_idnr)==set(selected)
fig=app.update_map(2017,*v,'fuel','capacity',[],{},selected,app.DEFAULT['dimensions'],None,0,1.22)[0]
assert len(next(t for t in fig.data if t.name=='Selected on map').lat)==len(selected)
print('[PASS] Scatter point IDs propagate to the comparison cohort and full map highlight')
for config in (a.DEFAULT_A,a.DEFAULT_B,dict(a.DEFAULT_A,strict=True),dict(a.DEFAULT_B,strict=True),dict(co2=None,age=None,cf=None,capacity=None,change=None,strict=False)):
    qualifies,unknown,fail=a.screen(frame,config)
    assert len(qualifies)+len(unknown)+len(fail)==len(frame)
    sets=[set(f.gppd_idnr) for f in (qualifies,unknown,fail)]
    assert not (sets[0]&sets[1] or sets[1]&sets[2] or sets[0]&sets[2])
    for k,(col,direction) in a.SCREEN.items():
        if config.get(k) is not None:
            assert (qualifies[col].ge(config[k]) if direction=='min' else qualifies[col].le(config[k])).all()
    if config.get('strict'): assert qualifies.year_provenance.eq('reported').all() and not qualifies.quality_flagged.any() and qualifies[a.EVIDENCE_FIELDS].notna().all().all()
aa,bb,au,bu,groups=a.compare(frame,a.DEFAULT_A,a.DEFAULT_B)
assert (len(aa),len(bb),len(groups['Both']))==(1587,76,26)
assert sum(map(len,groups.values()))==len(set(aa.gppd_idnr)|set(bb.gppd_idnr))
stages=a.evidence_steps(aa); assert all(len(x)>=len(y) for x,y in zip(stages,stages[1:])); assert len(stages[-1])==337
assert set(stages[-1].gppd_idnr)==set(a.screen(frame,dict(a.DEFAULT_A,strict=True))[0].gppd_idnr)
print('[PASS] Scenario sets partition the cohort; exact overlap and strict evidence retention reconcile')
A=[2,None,None,None,None,[]]; B=[.5,35,40,None,None,[]]
result=app.update_scenarios(2017,*v,[],*A,*B,'A','region','Both',None)
assert len(result[6])==26 and result[7] is None
assert set(o['value'] for o in result[6])==groups['Both']
assert app.choose_scenario_group({'points':[{'customdata':'Both'}]})=='Both'
chosen=result[6][0]['value']; dash.ctx.triggered_id='scenario-pin'
assert app.update_shortlist(0,[],0,1,None,[],chosen)==[chosen]
export=app.export_scenarios(1,2017,*v,[],*A,*B)
# Stubs retain the actual bound to_csv method: inspect its backing dataframe.
out=export[1][0].__self__; assert len(out)==8660
assert (out.scenario_A_status=='qualifies').sum()==1587
assert (out.scenario_B_status=='qualifies').sum()==76
assert 'reported_gen_change_pct' in out
print('[PASS] Scenario candidate lookup, pinning and actual CSV membership/status export')
empty=frame.iloc[:0]
assert not a.regional_figure(empty,'region','co2')[0].data
assert not a.scatter_figure(empty,'year_co2_mt','year_capacity_factor_pct')[0].data
assert all(len(g)==0 for g in a.compare(empty,a.DEFAULT_A,a.DEFAULT_B)[-1].values())
for y in core.YEARS:
    f=app.apply_filters(y,*v)
    aa,bb,au,bu,g=a.compare(f,a.DEFAULT_A,a.DEFAULT_B)
    assert len(set(aa.gppd_idnr)&set(bb.gppd_idnr))==len(g['Both'])
print('[PASS] Empty cohorts and all seven years work without inventing records')
