"""Check the V5 layout contract, drawer state and scenario overlays with real data."""
from pathlib import Path
import runpy
parts=runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
app,core,dash,walk=parts['app'],parts['core'],parts['fake_dash'],parts['walk']
components=list(walk(app.app.layout)); byid={c.id:c for c in components if isinstance(c.id,str)}
assert not {'workspace-tab','regional-toggle','comparison-mode','go-compare'}&set(byid)
assert not any(c.component_name in ('Tabs','Tab') for c in components)
main=next(c for c in components if c.props.get('className')=='main-charts')
assert len(main.children)==2
assert 'plant-map' in {c.id for c in walk(main.children[0])}
assert 'pcp-chart' in {c.id for c in walk(main.children[1])}
assert all(not c.props.get('style',{}).get('display')=='none' for c in walk(main))
rail={c.id for c in walk(app.SIDEBAR) if isinstance(c.id,str)}
assert {'scenario-a-co2','scenario-b-age','scenario-map-group','scenario-mini-summary','pcp-dimensions','open-scenario'}<=rail
assert all(byid[k+'-drawer'].props['style']=={'display':'none'} for k in app.DRAWERS)
assert sum(x['display']=='flex' for x in app.display_drawer('scenario'))==1
assert all(x['display']=='none' for x in app.display_drawer(None))
for key in app.DRAWERS:
    dash.ctx.triggered_id='open-'+key
    assert app.choose_drawer(*([0]*10),None,None)==key
    assert app.choose_drawer(*([0]*10),None,key) is None
    dash.ctx.triggered_id='close-'+key
    assert app.choose_drawer(*([0]*10),None,key) is None
    dash.ctx.triggered_id='focused-id'
    assert app.choose_drawer(*([0]*10),'test-id',key)=='inspect'
print('[PASS] Map above PCP in one mounted page; scenario controls in sidebar; optional drawers are mutually exclusive')
v=parts['values']; A=[2,None,None,None,None,[]]; B=[.5,35,40,None,None,[]]
summary,highlight=app.scenario_sidebar(2017,*v,[],*A,*B,'Both')
assert len(highlight['ids'])==26
frame=app.apply_filters(2017,*v)
assert len(frame)==8660
assert set(highlight['ids'])==app.analytics.compare(frame,app.analytics.DEFAULT_A,app.analytics.DEFAULT_B)[-1]['Both']
fig,*_=app.update_map(2017,*v,'fuel','capacity',[],{},[],app.DEFAULT['dimensions'],None,0,1.22,highlight)
overlay=next(t for t in fig.data if t.name=='Scenario Both')
assert len(overlay.lat)==26 and set(x[0] for x in overlay.customdata)==set(highlight['ids'])
assert fig.layout.height is None and fig.layout.autosize
_,off=app.scenario_sidebar(2017,*v,[],*A,*B,'off')
assert off['ids']==[]
assert not any(t.name=='Scenario Both' for t in app.update_map(2017,*v,'fuel','capacity',[],{},[],app.DEFAULT['dimensions'],None,0,1.22,off)[0].data)
assert app.reset_display_overlays(1)==('off',[])
print('[PASS] Scenario overlap IDs highlight exactly 26 facilities without narrowing the comparison baseline; reset clears display overlays')
