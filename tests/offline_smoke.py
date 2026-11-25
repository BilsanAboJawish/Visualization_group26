"""Offline callback/data smoke tests using lightweight Dash component stubs.

Run from project root: python tests/offline_smoke.py
These tests do not replace a real browser integration test.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

class Component:
    def __init__(self, component_name, *children, **props):
        self.component_name = component_name
        self.children = props.get('children', children)
        self.props = props
        self.id = props.get('id')
    def __repr__(self):
        return f'<{self.component_name} {self.id or ""}>'

class ComponentFactory:
    def __getattr__(self, name):
        def build(*children, **props):
            return Component(name, *children, **props)
        return build

class IO:
    def __init__(self, component_id, component_property):
        self.component_id = component_id
        self.component_property = component_property

class In(IO): pass
class Out(IO): pass
class St(IO): pass

class Context:
    triggered_id = None
    triggered = []

class FakeDash:
    def __init__(self, *args, **kwargs):
        self._callbacks = []
        self.layout = None
    def callback(self, *args, **kwargs):
        def decorate(fn):
            self._callbacks.append((fn.__name__, args))
            return fn
        return decorate
    def run(self, *args, **kwargs):
        raise RuntimeError('Dash must be installed to run the app')

fake_dash = types.ModuleType('dash')
fake_dash.Dash = FakeDash
fake_dash.Input = In
fake_dash.Output = Out
fake_dash.State = St
fake_dash.ALL = 'ALL'
fake_dash.ctx = Context()
fake_dash.dcc = ComponentFactory()
fake_dash.html = ComponentFactory()
fake_dash.no_update = object()
fake_dash.dcc.send_data_frame = lambda *a, **k: ('csv', a, k)
errors = types.ModuleType('dash.exceptions')
class PreventUpdate(Exception):
    pass
errors.PreventUpdate = PreventUpdate
sys.modules['dash'] = fake_dash
sys.modules['dash.exceptions'] = errors

import numpy as np
import app
import core


def walk(node):
    if isinstance(node, Component):
        yield node
        for c in walk(node.children):
            yield c
    elif isinstance(node, (tuple, list)):
        for value in node:
            yield from walk(value)

components = list(walk(app.app.layout))
ids = [p.id for p in components if isinstance(p.id, str)]
assert len(ids) == len(set(ids)), 'Duplicate component id'
assert 'candidate-list' not in ids and 'candidate-search' not in ids
assert 'plant-map' in ids and 'pcp-chart' in ids and 'shortlist-cards' in ids
assert 'cluster-mode' in ids and 'pcp-dimensions' in ids and 'inspect-picker' in ids
for name, bindings in app.app._callbacks:
    for b in bindings:
        if isinstance(b, IO) and isinstance(b.component_id, str):
            assert b.component_id in ids, f'{name} references unknown component {b.component_id}'
print('[PASS] Component IDs and callback references')

outputs = []
for name, bindings in app.app._callbacks:
    for b in bindings:
        if isinstance(b, Out):
            outputs.append((str(b.component_id), b.component_property))
assert len(outputs) == len(set(outputs)), 'Duplicate Dash callback outputs'
print('[PASS] No duplicate callback outputs')

assert len(app.BASE) == 34936
assert len(core.get_year_frame(2017).loc[lambda d: d.fuel_group.eq('Fossil')]) == 8660
assert len(app.FILTER_INPUTS) == 23
print('[PASS] Dataset and filter schema')

values = [
    ['Fossil'], [], [], [], [], '', [0, app.CAP_MAX], [],
    [], [0, app.AGE_MAX], [], [0,100], [], [0, app.CO2_MAX],
    'all', [], 'all', 'all', 'all', 0,
    [], [0, app.GEN_MAX], 'all'
]
base = app.apply_filters(2017, *values)
assert len(base) == 8660
values[1] = ['Coal']
assert len(app.apply_filters(2017, *values)) == 2330
values[1] = []
values[2] = ['Europe']
assert 0 < len(app.apply_filters(2017, *values)) < len(base)
values[2] = []
print('[PASS] Fuel, region and default filtering')

fig = core.make_map(base, 2017, 'fuel', 'capacity', cluster=True,
                    map_selected_ids=[str(base.iloc[0].gppd_idnr)])
assert any(getattr(trace.cluster, 'enabled', False) for trace in fig.data[:4])
assert any(trace.name == 'Selected on map' for trace in fig.data)
assert len(fig.data) >= 4
print('[PASS] Map overlays, clustering and Plotly data traces')

axes = app.DEFAULT['dimensions']
eligible, meta = core.pcp_cohort(base, [], axes)
assert meta['cohort'] == 8660
assert meta['eligible'] > 0
sample = core.pcp_plot_sample(eligible, max_lines=650)
assert len(sample) <= 650
pcp_fig = core.make_pcp(sample, axes, 2017, eligible=eligible)
for axis, name in zip(pcp_fig.data[0].dimensions, axes):
    assert np.isclose(axis.range[0],float(core.pcp_to_display(name,eligible[name].min())))
    assert np.isclose(axis.range[1],float(core.pcp_to_display(name,eligible[name].max())))
    if name in core.PCP_LOG_FIELDS:
        assert axis.label == core.PCP_AXIS_LABELS[name] and axis.tickvals and axis.ticktext
print('[PASS] PCP has compact axis labels, full-cohort bounds, and real-unit log ticks')

bounds = eligible['capacity_mw'].quantile([.2,.3]).tolist()
selected_all = core.brushed_ids(eligible, {'capacity_mw':[bounds]})
assert len(selected_all) > 0
assert set(selected_all) == set(eligible.loc[eligible.capacity_mw.between(*bounds),'gppd_idnr'])
assert len(selected_all) >= len(set(selected_all).intersection(set(sample.gppd_idnr)))
print('[PASS] PCP brushing evaluates full eligible data')

# Simulated Dash callbacks
fake_dash.ctx.triggered_id = 'pcp-dimensions'
assert app.reorder_axes(axes, 0, 0, None, axes[0], []) == axes
fake_dash.ctx.triggered_id = 'axis-right'
assert app.reorder_axes(axes, 0, 1, None, axes[0], axes)[:2] == axes[1::-1]
print('[PASS] PCP axis reorder actions')

fake_dash.ctx.triggered_id = 'plant-map'
point = {'points':[{'customdata':[str(base.iloc[0].gppd_idnr)]}]}
map_fig = core.make_map(base, 2017).to_plotly_json()
picked = app.save_map_selection(point, 0, values[5], None,0,0,None,"capacity",map_fig, 2017, *values[:5], *values[6:], [])
assert picked == [str(base.iloc[0].gppd_idnr)]
print('[PASS] Map selection to plant ID')

fake_dash.ctx.triggered_id = 'pin-focused'
chosen = str(base.iloc[0].gppd_idnr)
assert app.update_shortlist(1,[],0,0,chosen,[]) == [chosen]
fake_dash.ctx.triggered_id = {'type':'shortlist-remove','plant':chosen}
fake_dash.ctx.triggered = [{'value':1}]
assert app.update_shortlist(1,[1],0,0,chosen,[chosen]) == []
print('[PASS] Pin and remove plant')

saved=app.render_shortlist([chosen],2017)
assert saved[0].startswith('1 saved')
assert saved[1]
export=app.export_shortlist(1,[chosen],2017)
assert export[0]=='csv'
print('[PASS] Shortlist render and CSV export wiring')

for y in [2013,2017,2019]:
    frame = core.get_year_frame(y)
    assert len(frame)==34936
    assert not frame.loc[~frame.primary_fuel.isin(core.FOSSIL),'year_co2_mt'].notna().any()
print('[PASS] Year-specific provenance and modeled CO2 boundaries')
print('Offline smoke tests all passed; actual browser interactions still require Dash.')

# End-to-end callback function checks (without real browser plumbing).
values = [
    ['Fossil'], [], [], [], [], '', [0, app.CAP_MAX], [],
    [], [0, app.AGE_MAX], [], [0,100], [], [0, app.CO2_MAX],
    'all', [], 'all', 'all', 'all', 0,
    [], [0, app.GEN_MAX], 'all'
]
map_result = app.update_map(2017, *values, 'fuel', 'capacity', [], {}, [],
                            app.DEFAULT['dimensions'], None, 0, 1.22)
assert len(map_result) == 7
assert map_result[1] == '8,660'
assert map_result[2] == '152'
assert len(map_result[0].data) == 4
pcp_result = app.update_pcp(2017, *values, [], app.DEFAULT['dimensions'], 'All', 'overview', 0, {})
assert len(pcp_result[0].data) == 1
assert isinstance(pcp_result[1], Component)
assert len(list(walk(pcp_result[1]))) >= 5
print('[PASS] Main map and PCP callbacks with complete default filter payload')

# Demographics / external inputs are intentionally not fabricated.
assert not any(p.id == 'population-overlay' for p in components)
assert any(p.id == 'cluster-mode' for p in components)
assert any(p.id == 'inspect-picker' for p in components)
assert 'country_regions.csv' in str(core.REGIONS_PATH)
print('[PASS] Unavailable population overlay removed; regional map is present')

matched = app.search_for_inspection('sur', 2017, [], {}, app.DEFAULT['dimensions'], *values, None)
assert len(matched) <= 35
assert all('label' in m and 'value' in m for m in matched)
print('[PASS] Scoped search returns bounded dynamic choices without candidate list')

# Action-state controls never offer to pin an empty selection.
assert app.update_action_states(None, [])[0] is True
assert app.update_action_states(chosen, [chosen])[0] is True
assert app.update_action_states(chosen, [])[0] is False
print('[PASS] Context-aware pin/export actions')

# Ensure a 2019 selection never reports modeled generation as available.
f2019 = core.get_year_frame(2019)
assert not (f2019.year_provenance == 'estimated').any()
print('[PASS] No estimated generation silently extrapolated into 2018–2019')


# Extra filters added by the Studio redesign are real data filters, not styling.
from copy import deepcopy
filters = [
    ['Fossil'], [], [], [], [], '', [0, app.CAP_MAX], [],
    [], [0, app.AGE_MAX], [], [0,100], [], [0, app.CO2_MAX],
    'all', [], 'all', 'all', 'all', 0,
    [], [0, app.GEN_MAX], 'all'
]
only_single = deepcopy(filters)
only_single[-1] = 'single'
only_multi = deepcopy(filters)
only_multi[-1] = 'multi'
a = app.apply_filters(2017, *only_single)
b = app.apply_filters(2017, *only_multi)
assert len(a)+len(b) == len(base)
assert not a.has_other_fuel.any()
assert b.has_other_fuel.all()
print('[PASS] Single/multiple-fuel screening')

with_generation = deepcopy(filters)
with_generation[-3] = ['on']
with_generation[-2] = [0,1000]
g = app.apply_filters(2017, *with_generation)
assert len(g) > 0 and len(g) < len(base)
assert g.year_generation_gwh.notna().all()
assert g.year_generation_gwh.between(0,1000).all()
print('[PASS] Generation-value range screening')

# The new look contains no candidate browser or table, and all layout inputs exist.
for required in ('nav-shortlist-total','generation-year','generation-enabled',
                 'generation-filter','fuel-configuration-filter','export-shortlist'):
    assert required in ids, required
assert not any(c.component_name in ('Table','DataTable') for c in components)
assert any(c.component_name=='Details' for c in components)
print('[PASS] Professional layout retains all filter and shortlist controls')

# Advanced-generation filters can preserve missing when the user explicitly opts in.
with_unknown = deepcopy(with_generation)
with_unknown[15] = ['include']
x = app.apply_filters(2019, *with_unknown)
assert len(x) >= len(app.apply_filters(2019, *with_generation))
print('[PASS] Explicit missing-data inclusion in new range filter')

# Verify new presentation widgets are meaningful and callback outputs line up.
assert len(app.reset_all_filters(1)) == 29
assert 'active-filter-chips' not in ids
assert 'active-filter-count' not in ids
assert 'population-overlay' not in ids
assert 'generation-year' in ids
assert app.toggle_analytical_ranges([], [], [], []) == (True,True,True,True)
assert app.toggle_analytical_ranges(['on'], [], [], ['on']) == (False,True,True,False)
assert 'MW' in app.describe_ranges([0,100],[0,50],[0,100],[0,2],[0,100])[0]
assert app.update_nav_shortlist_count([]) == '0'
assert app.update_nav_shortlist_count([chosen, chosen]) == '1'

inspected=app.plant_inspector(chosen, 2017)
inspected_types={el.component_name for el in walk(inspected)}
assert 'Graph' in inspected_types and 'Details' in inspected_types
print('[PASS] Navigator, minimal filter sidebar and redesigned inspector')

# The PCP coverage should refer to all cohort records, not only plotted sample.
card_text = ' '.join(str(child.children) for child in walk(pcp_result[1])
                     if child.component_name in ('Span','Strong'))
assert f'{len(eligible):,}' in card_text
assert f'{min(len(eligible), app.PCP_LINE_LIMIT):,}' in card_text
print('[PASS] PCP coverage panel shows whole cohort and displayed sample')

# A one-screen app must have responsive graphs rather than taller fixed-size canvases.
map_component = next(x for x in components if x.id == 'plant-map')
pcp_component = next(x for x in components if x.id == 'pcp-chart')
assert 'height' not in map_component.props['style']
assert 'height' not in pcp_component.props['style']
assert core.make_map(base, 2017).layout.autosize is True
assert core.make_map(base, 2017).layout.height is None
assert core.make_pcp(core.pcp_plot_sample(core.pcp_cohort(base, None, app.DEFAULT['dimensions'])[0]),
                     app.DEFAULT['dimensions'], 2017).layout.autosize is True
css = (Path(__file__).resolve().parents[1] / 'assets' / 'zzz_one_screen.css').read_text()
assert '.app-shell {height:100dvh' in css
assert '.workspace-body {display:flex;flex-direction:column;height:100%' in css
assert '.filter-panel {position:relative;' in css
assert '.compare-view {flex:1;' in css
assert '.pcp-graph {flex:1 1 0;' in css
assert '.map-graph {display:block;flex:1 1 0;' in css
assert 'workspace-tab' not in ids
assert all(c.component_name not in ('Tabs','Tab') for c in components)
print('[PASS] Bounded one-screen layout and responsive Plotly canvas sizing')

# Submission visual clarity: drawing fewer records never reduces eligible brush membership.
assert app.PCP_LINE_LIMIT == 100
full_plotted = core.pcp_plot_sample(eligible, max_lines=app.PCP_LINE_LIMIT)
assert len(full_plotted) == min(len(eligible), app.PCP_LINE_LIMIT)
assert set(core.brushed_ids(eligible, {'capacity_mw':[bounds]})) == set(selected_all)
assert len(core.make_pcp(full_plotted, axes, 2017, eligible=eligible).data[0].line.color)==len(full_plotted)
print('[PASS] Fuel-colored low-overplotting PCP with unchanged full-cohort brushing')

# Log-axis interaction roundtrips use ORIGINAL units when applying a brush.
raw_bounds=eligible['capacity_mw'].quantile([.2,.3]).tolist()
visual_bounds=[float(core.pcp_to_display('capacity_mw',x)) for x in raw_bounds]
restyle=[{'dimensions[0].constraintrange':[visual_bounds]},[0]]
restored=core.extract_restyle_constraints(restyle,{},axes,display_scaled=True)
assert np.allclose(restored['capacity_mw'][0],raw_bounds)
assert set(core.brushed_ids(eligible,restored)) == set(core.brushed_ids(eligible,{'capacity_mw':[raw_bounds]}))
assert len(core.pcp_plot_sample(eligible,100,focus_fuel='Coal')) <=100
assert len(core.pcp_plot_sample(eligible,180,focus_fuel='Gas'))<=180
# A focused fuel changes the displayed sample, not the eligible population.
assert len(eligible)==meta['eligible']
focused_fig=core.make_pcp(core.pcp_plot_sample(eligible,100,focus_fuel='Gas'),
                          axes,2017,eligible=eligible,focus_fuel='Gas',constraints=restored)
assert focused_fig.data[0].dimensions[0].constraintrange is not None
assert np.isclose(focused_fig.data[0].dimensions[0].constraintrange[0],visual_bounds[0])
# The clear button must cause a real plot redraw and reset its constraints.
app.ctx.triggered_id='clear-pcp'
cleared_fig,_=app.update_pcp(2017,*values,[],axes,'All','overview',1,restored)
assert all(d.constraintrange is None for d in cleared_fig.data[0].dimensions)
print('[PASS] Log-scale brushing, fuel focus and visual brush reset')

# Regression: edge axis label should be short, with reserve at both plot edges.
label_fig = core.make_pcp(full_plotted, axes, 2017, eligible=eligible)
assert label_fig.data[0].domain.x[1] <= 0.86
assert label_fig.data[0].domain.x[0] >= 0.09
assert label_fig.data[0].dimensions[-1].label == 'Modeled CO₂ (Mt)'
assert not any('log scale' in d.label for d in label_fig.data[0].dimensions)
assert 'log display' in app.app.layout.children.__repr__() or 'log display' in Path(app.__file__).read_text()
assert core._blend(core.FUEL_COLORS['Gas'],.76) in str(label_fig.data[0].line.colorscale)
print('[PASS] Edge-safe PCP labels and subdued baseline line palette')

# Multi-axis brush semantics, clear, and visual-only focus/detail remain invariant.
raw2=eligible['year_co2_mt'].quantile([.35,.65]).tolist()
visual2=[float(core.pcp_to_display('year_co2_mt',x)) for x in raw2]
restyle_two=[{'dimensions[0].constraintrange':[visual_bounds],
             'dimensions[2].constraintrange':[visual2]},[0]]
two=core.extract_restyle_constraints(restyle_two,{},axes,display_scaled=True)
expected=set(eligible.loc[eligible.capacity_mw.between(*raw_bounds) &
                          eligible.year_co2_mt.between(*raw2),'gppd_idnr'])
assert set(core.brushed_ids(eligible,two))==expected
app.ctx.triggered_id='pcp-chart'
callback_brush=app.update_brush(restyle_two,0,2017,*values,[],axes,{})
assert set(core.brushed_ids(eligible,callback_brush))==expected
summary=app.show_brush_counts(callback_brush, [], axes, 2017, *values)
assert f'{len(expected):,}' in summary
# Clearing an individual axis resets it while retaining other selected dimensions.
unselect=[{'dimensions[2].constraintrange':[None]},[0]]
retained=core.extract_restyle_constraints(unselect,two,axes,display_scaled=True)
assert set(retained)=={'capacity_mw'}
app.ctx.triggered_id='clear-pcp'
assert app.update_brush(None,1,2017,*values,[],axes,two)=={}
print('[PASS] Two-axis brush events, full-cohort match counts, axis-clear and clear-all')

# Cross-link contract: the same full-cohort brush drives map highlights and
# the inspector cohort; it does not silently use the displayed PCP sample.
link_map=app.update_map(2017,*values,'fuel','capacity',[],two,[],axes,None,0,1.22)[0]
link_traces=[tr for tr in link_map.data if tr.name == 'PCP matches']
assert len(link_traces)==1, 'PCP brush must produce map highlight overlay'
assert len(link_traces[0].lat)==len(expected)
inspector_cohort=app.analysis_cohort(2017,values,[],axes,two)
assert set(inspector_cohort.gppd_idnr)==expected
cleared_map=app.update_map(2017,*values,'fuel','capacity',[],{},[],axes,None,0,1.22)[0]
assert not any(tr.name == 'PCP matches' for tr in cleared_map.data)
print('[PASS] Brush -> matching map overlay -> inspection scope -> clear overlay')
print(f'[CHECK] Default 2017: {meta["cohort"]:,} fossil plants; {len(eligible):,} PCP eligible; '
      f'{len(expected):,} plants match the two-axis sample brush.')
