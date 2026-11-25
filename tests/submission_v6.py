"""Final visual encoding and interaction regression tests; no Dash required."""
from pathlib import Path
import runpy
import numpy as np
parts=runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
app,core,dash,walk=parts['app'],parts['core'],parts['fake_dash'],parts['walk']
v=parts['values']; f=app.apply_filters(2017,*v); axes=app.DEFAULT['dimensions']
eligible,meta=core.pcp_cohort(f,[],axes)
# All scales invert on all measured values, including zero, extremes and negative change.
for year in core.YEARS:
    frame=core.get_year_frame(year); frame=frame.loc[frame.fuel_group.eq('Fossil')]
    for field in core.PCP_FIELDS:
        vals=frame[field].dropna().to_numpy(float)
        if not len(vals): continue
        scaled=core.pcp_to_display(field,vals)
        assert np.allclose(core.pcp_from_display(field,scaled),vals,rtol=1e-10,atol=1e-9),(year,field)
        lo,hi=vals.min(),vals.max()
        if hi>lo:
            ticks,labels=core._pcp_ticks(field,lo,hi)
            assert len(ticks)==len(labels) and 2<=len(ticks)<=5
            assert len(labels)==len(set(labels)) and np.all(np.diff(ticks)>0)
            assert np.min(np.diff(ticks))>=(ticks[-1]-ticks[0])*.18-1e-8
            assert np.allclose([ticks[0],ticks[-1]],core.pcp_to_display(field,[lo,hi]))
print('[PASS] Real-unit inverse transforms and readable tick spacing for all six fields and seven years')
assert len(f.loc[f.plant_age_2021_years.eq(121)])==3
assert set(f.loc[f.plant_age_2021_years.eq(121),'commissioning_year'])=={1900}
assert f.reported_gen_change_pct.max()>1e6
print('[PASS] Extreme historical ages and generation changes retained, not silently removed')
# Tiny and larger brush cohorts must appear in the sample, but membership is full-cohort.
for low,high in [(0.,10.),(100.,300.),(8000.,10000.),(1e5,1e6)]:
    brush={'capacity_mw':[[low,high]]}; ids=set(core.brushed_ids(eligible,brush))
    s=core.prioritize_pcp_sample(eligible,100,'All',brush)
    assert len(s)==min(100,len(eligible)) and s.gppd_idnr.is_unique
    assert len(set(s.gppd_idnr)&ids)>=min(80,len(ids))
    assert ids==set(eligible.loc[eligible.capacity_mw.between(low,high),'gppd_idnr'])
print('[PASS] Brush-prioritized display without changing full-cohort membership')
brush={'capacity_mw':[[100.,300.]]}; dash.ctx.triggered_id='pcp-brush'
fig,note=app.update_pcp(2017,*v,[],axes,'All','overview',0,brush)
assert fig.data[0].dimensions[0].constraintrange is not None
assert np.allclose(fig.data[0].dimensions[0].constraintrange,core.pcp_to_display('capacity_mw',[100.,300.]))
assert core.FUEL_COLORS['Gas'] in str(fig.data[0].line.colorscale)
assert fig.data[0].labelfont.size>=14 and fig.data[0].tickfont.size>=12
# Native Plotly drag-order event uses actual field names rather than guessing indices.
dash.ctx.triggered_id='pcp-chart'
order=[axes[2],axes[0],axes[1]]; restyle=[{'dimensions':[[{'name':x} for x in order]]},[0]]
assert app.reorder_axes(axes,0,0,restyle,axes[0],axes)==order
assert app.update_brush(restyle,0,2017,*v,[],axes,{}) is dash.no_update
raw=[.05,1.0]; transformed=core.pcp_to_display(order[0],raw).tolist()
result=app.update_brush([{'dimensions[0].constraintrange':[transformed]},[0]],0,2017,*v,[],order,{})
assert list(result)==[order[0]] and np.allclose(result[order[0]][0],raw)
print('[PASS] Native axis reordering, correctly mapped subsequent brush, active constraints preserved on redraw')
# Every visible base point is present; marker growth and selection emphasis are explicit.
lo=core.make_map(f,2017,zoom_for_markers=1.22); hi=core.make_map(f,2017,zoom_for_markers=5.)
assert sum(len(t.lat) for t in lo.data)==len(f)
for l,h in zip(lo.data,hi.data):
    assert np.all(np.asarray(h.marker.size)>np.asarray(l.marker.size))
    assert h.marker.opacity>l.marker.opacity
chosen=f.gppd_idnr.iloc[:20].tolist(); sel=core.make_map(f,2017,highlight_ids=chosen)
assert sel.data[0].marker.opacity<lo.data[0].marker.opacity
assert set(x[0] for x in sel.data[-1].customdata)==set(chosen)
print('[PASS] Adaptive markers, de-emphasized context and exact full selection overlays')
sections=app.SIDEBAR.children[-1].children
for section,expected in zip(sections,['Geography','Fuel & capacity','Generation','Plant screening','Evidence quality','Scenario screening','PCP settings','Map appearance']):
    words=[c.children[0] for c in walk(section) if c.component_name=='Strong' and c.props.get('className')=='section-title']
    assert words==[expected],(words,expected)
    assert not section.props.get('open')
print('[PASS] All eight sidebar groups discoverable, ordered basic to advanced')
print('V6 OFFLINE REGRESSION PASSED')
