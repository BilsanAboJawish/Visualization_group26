"""fossil atlas | NGO fossil-plant screening dashboard.

Start: python app.py
Requires the existing data/processed/power_plants_features.csv.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ALL, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate

import core
import analysis_tools as analytics

core.BASE = core.read_base()
BASE = core.BASE
YEAR_DEFAULT = 2017
FUELS = sorted(BASE.primary_fuel.dropna().unique())
CONTINENTS = sorted(BASE.continent.dropna().unique())
REGIONS = sorted(BASE.region.dropna().unique())
COUNTRIES = sorted(BASE.country_long.dropna().unique())
CAP_MAX = int(np.ceil(BASE.capacity_mw.max()/100)*100)
AGE_MAX = int(np.ceil(BASE.plant_age_2021_years.max()/10)*10)
CO2_MAX = max(1,int(np.ceil(max(core.get_year_frame(y).year_co2_mt.max(skipna=True) for y in core.YEARS))))
GEN_MAX = int(np.ceil(max(core.get_year_frame(y).year_generation_gwh.max(skipna=True) for y in core.YEARS) / 1000)*1000)

DEFAULT = {
 'groups':['Fossil'], 'fuels':[], 'continents':[], 'regions':[], 'countries':[], 'search':None,
 'year':2017,'capacity':[0,CAP_MAX], 'provenance':[],
 'age_enabled':[], 'age':[0,AGE_MAX], 'cf_enabled':[], 'cf':[0,100],
 'co2_enabled':[], 'co2':[0,CO2_MAX], 'trend':'all','unknown':[],
 'quality':'all','commissioning':'all','generation_source':'all','min_reported_years':0,
 'generation_enabled':[], 'generation':[0,GEN_MAX], 'fuel_configuration':'all',
 'color':'fuel','size':'capacity','dimensions':['capacity_mw','plant_age_2021_years','year_co2_mt'],
 'pcp_focus':'All','pcp_density':'overview',
}

app=Dash(__name__)
app.title='Fossil Atlas | Power plant analytics'


def field(label,content,description=None):
    return html.Div([html.Label(label,className='field-label'),content,
                     html.P(description,className='field-hint') if description else None],className='field')


# Small, self-contained vector icons: consistent stroke and accessible labels.
SIDEBAR_ICON_PATHS = {
    'location': '<circle cx="12" cy="10" r="3"/><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/>',
    'fuel': '<path d="M12 2v4M7 7l-3-3M17 7l3-3"/><path d="M8 22v-8c0-2 1.7-3.5 4-3.5s4 1.5 4 3.5v8"/><path d="M5 22h14M9 17h6"/>',
    'generation': '<path d="m13 2-9 12h7l-1 8 10-13h-7l0-7Z"/>',
    'screen': '<circle cx="11" cy="11" r="7"/><path d="m16.5 16.5 5 5M8 11h6M11 8v6"/>',
    'quality': '<path d="m12 2 8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4Z"/><path d="m9 12 2 2 4-4"/>',
    'display': '<path d="M3 4h18v13H3zM8 21h8M12 17v4M6 8h8M6 11h5"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
    'filters': '<path d="M4 7h16M7 12h10M10 17h4"/>',
}

def sidebar_icon(name):
    from urllib.parse import quote
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           'fill="none" stroke="currentColor" stroke-width="1.8" '
           'stroke-linecap="round" stroke-linejoin="round">'
           + SIDEBAR_ICON_PATHS[name] + '</svg>')
    return html.Img(src='data:image/svg+xml;charset=utf-8,' + quote(svg),
                    alt='', className='sidebar-svg')


def section(title,subtitle,children,open=False,icon='screen'):
    """Accessible disclosures, fixed icon/title layout, full keyboard support."""
    return html.Details([
        html.Summary([
            html.Span(sidebar_icon(icon), className=f'section-icon section-icon--{icon}',
                      **{'aria-hidden':'true'}),
            html.Span([html.Strong(title, className='section-title'),
                       html.Small(subtitle, className='section-subtitle')],
                      className='section-heading'),
            html.Span('⌄', className='section-chevron', **{'aria-hidden':'true'}),
        ]),
        html.Div(children, className='section-body')
    ], open=open, className=f'filter-section filter-section--{icon}')


def range_field(key,title,maximum,step,description):
    return html.Div([
        html.Div([
            html.Label(title,className='field-label'),
            html.Span(id=f'{key}-range-label', className='range-value'),
        ],className='range-topline'),
        dcc.Checklist(id=f'{key}-enabled',
            options=[{'label':'Apply range filter','value':'on'}],
            value=[],className='category-checklist range-enabler'),
        dcc.RangeSlider(id=f'{key}-filter',min=0,max=maximum,value=[0,maximum],
            disabled=True,step=step,marks={0:'0',maximum:f'{maximum:,}'},
            allowCross=False,tooltip={'placement':'bottom'},className='range-slider'),
        html.P(description,className='field-hint'),
    ],className='field filter-range-block')


def select(name,key,options,multi=False,value=None,placeholder=None):
    return field(name,dcc.Dropdown(id=key,options=options,multi=multi,
             value=[] if multi and value is None else value,clearable=multi,
             placeholder=placeholder,className='clean-dropdown'))


def info_chip(text):
    return html.Span(text,className='muted-chip')


def stat_card(label,output_id,sub):
    return html.Div([html.Div(label,className='stat-label'),html.Strong(id=output_id,className='stat-number'),
                     html.Span(sub,className='stat-caption')],className='stat-card')


def block_title(eyebrow,title,tag=None):
    return html.Div([html.Div([html.Span(eyebrow,className='eyebrow'),html.H2(title)]),
                     info_chip(tag) if tag else None],className='block-title')


# All original sidebar filters, plus requested source and anomaly completeness filters.
# =====================================================================
# Fossil Atlas Studio — professional workspaces; all callbacks keep stable IDs.
# =====================================================================


def icon_mark(symbol, css_class=''):
    return html.Span(symbol, className=f'ui-icon {css_class}')


def sidebar_search():
    return dcc.Dropdown(id='plant-search', options=[], value=None,
        searchable=True, clearable=True, placeholder='Name or plant ID',
        className='clean-dropdown plant-autocomplete', maxHeight=280,
        optionHeight=56)


SIDEBAR = html.Aside(className='filter-panel', children=[
    html.Div(className='filter-head', children=[
        html.Div(className='filter-head-title',children=[
            html.Div(className='filter-head-icon',children=sidebar_icon('filters')),
            html.Div([
                html.H2('Refine plants'),
                html.P('Choose your criteria', className='small-muted'),
            ]),
        ]),
        html.Button('Reset filters', id='reset-filters', n_clicks=0,
                    className='button sidebar-reset', title='Restore filters and chart settings; keep scenario criteria and shortlist'),
    ]),
    html.Div(className='filter-sticky-search',children=[
        html.Div(className='sidebar-search-label',children='Find a plant'),
        html.Div(className='sidebar-search-control',children=[
            sidebar_search(),
        ]),
    ]),
    html.Nav(className='filter-groups',**{'aria-label':'Plant filters'}, children=[
        section('Geography', 'Location and region', [
            select('Continent','continent-filter',CONTINENTS,multi=True,placeholder='Any continent'),
            select('Region / subregion','region-filter',REGIONS,multi=True,placeholder='Any region'),
            select('Country','country-filter',COUNTRIES,multi=True,placeholder='Any country'),
        ],icon='location'),
        section('Fuel & capacity', 'Energy profile and size', [
            field('Energy category', dcc.Checklist(
                id='group-filter',value=['Fossil'],className='option-list category-tiles',
                options=[{'label':'Fossil fuels','value':'Fossil'},
                         {'label':'Non-fossil','value':'Non-fossil'},
                         {'label':'Mixed / other','value':'Mixed / unspecified'}])),
            select('Primary fuel','fuel-filter',FUELS,multi=True,placeholder='Any fuel'),
            html.Div(className='field capacity-range',children=[
                html.Div([html.Label('Installed capacity',className='field-label'),
                          html.Span(id='capacity-range-label',className='range-value')],
                         className='range-topline'),
                dcc.RangeSlider(id='capacity-filter',min=0,max=CAP_MAX,value=[0,CAP_MAX],
                    step=10,marks={0:'0',CAP_MAX:f'{CAP_MAX:,}'},allowCross=False,
                    tooltip={'placement':'bottom'},className='range-slider'),
                html.P('MW · nameplate capacity',className='field-hint'),
            ]),
            select('Additional fuels recorded','fuel-configuration-filter',[
                {'label':'Any configuration','value':'all'},
                {'label':'No secondary fuel listed','value':'single'},
                {'label':'Secondary fuel listed','value':'multi'}],value='all'),
        ],icon='fuel'),
        section('Generation', 'Year, output and evidence', [
            select('Reference year','generation-year',[
                {'label':str(year),'value':year} for year in core.YEARS],value=2017),
            select('Generation data status','provenance-filter',[
                {'label':label,'value':key} for key,label in core.PROVENANCE_LABELS.items()],
                multi=True,placeholder='Any status'),
            html.Div(className='field filter-range-block',children=[
                html.Div([html.Label('Electricity generation',className='field-label'),
                          html.Span(id='generation-range-label',className='range-value')],
                         className='range-topline'),
                dcc.Checklist(id='generation-enabled',value=[],className='category-checklist range-enabler',
                    options=[{'label':'Limit to this range','value':'on'}]),
                dcc.RangeSlider(id='generation-filter',min=0,max=GEN_MAX,value=[0,GEN_MAX],
                    step=100,disabled=True,marks={0:'0',GEN_MAX:f'{GEN_MAX:,}'},
                    allowCross=False,tooltip={'placement':'bottom'},className='range-slider'),
                html.P('GWh · reported or plausibly modeled',className='field-hint'),
            ]),
            select('Historical generation trend','trend-filter',[
                {'label':'Any trend','value':'all'},
                {'label':'Declining (below −5%)','value':'declining'},
                {'label':'Stable (−5% to +5%)','value':'stable'},
                {'label':'Increasing (above +5%)','value':'increasing'},
                {'label':'Insufficient reported history','value':'unavailable'}],value='all'),
            html.P('Trend uses earliest and latest reported observations, not the chosen year. '
                   'Estimated records may exist through 2017, depending on fuel; none exist for 2018–19.',className='field-hint section-note'),
        ],icon='generation'),
        section('Plant screening','Age, utilization and CO₂', [
            range_field('age','Age (as of 2021)',AGE_MAX,1,
                        'Years since commissioning; unavailable when the year is unknown.'),
            range_field('cf','Reported capacity factor',100,1,
                        '% · calculated only from plausible reported generation.'),
            range_field('co2','Modeled CO₂ emissions',CO2_MAX,.25,
                        'Mt · modeled scenario for fossil fuels, not measured emissions.'),
            field('Missing values in active ranges',dcc.Checklist(
                id='unknown-filter',value=[],className='option-list soft-toggle',
                options=[{'label':'Include plants with unknown values','value':'include'}])),
        ],icon='screen'),
        section('Evidence quality','Completeness and anomalies', [
            select('Quality checks','quality-filter',[
                {'label':'All records','value':'all'},
                {'label':'No flagged anomalies','value':'clean'},
                {'label':'Flagged for review','value':'flagged'}],value='all'),
            select('Commissioning year','commissioning-filter',[
                {'label':'Any availability','value':'all'},
                {'label':'Year recorded','value':'known'},
                {'label':'Year not recorded','value':'unknown'}],value='all'),
            select('Generation source','generation-source-filter',[
                {'label':'Any availability','value':'all'},
                {'label':'Source recorded','value':'known'},
                {'label':'Source not recorded','value':'unknown'}],value='all'),
            field('Minimum reported years',dcc.Slider(id='min-reported-years',
                min=0,max=7,step=1,value=0,marks={i:str(i) for i in range(8)},
                tooltip={'placement':'bottom'},className='range-slider'),
                '0–7 years · counts records, including those flagged for review.'),
        ],icon='quality'),
        section('Map appearance', 'Color and marker detail', [
            field('Color points by',dcc.RadioItems(id='color-mode',value='fuel',className='option-list radio-card-list',
                options=[{'label':'Primary fuel','value':'fuel'},
                         {'label':'Generation data status','value':'provenance'},
                         {'label':'Modeled CO₂ scenario','value':'co2'}])),
            field('Marker size',dcc.RadioItems(id='size-mode',value='capacity',className='option-list radio-card-list',
                options=[{'label':'Installed capacity','value':'capacity'},
                         {'label':'Uniform size','value':'uniform'}])),
            field('Clustering',dcc.Checklist(id='cluster-mode',value=[],className='option-list soft-toggle',
                options=[{'label':'Group markers when zoomed out','value':'cluster'}]),
                'Disable clustering for precise lasso selection.'),
        ],icon='display'),
    ]),
])


PCP_LINE_LIMIT = 100  # standard overview; detailed mode shows 180 lines
VALID_IDS = set(BASE.gppd_idnr.astype(str))


def format_value(value, unit='', places=1):
    try:
        return (f'{float(value):,.{places}f}{unit}' if pd.notna(value)
                and np.isfinite(float(value)) else 'Unavailable')
    except (TypeError, ValueError):
        return 'Unavailable'


def data_note():
    return html.Div(className='evidence-note', children=[
        icon_mark('i', 'info-dot'),
        html.Div([html.Strong('About these numbers'), html.P(
            'Reported generation is not independently verified. Capacity factor uses only '
            'plausible reported generation. CO₂ reflects a fuel-based modeling scenario, '
            'not actual plant emissions. The facility dataset is historical and incomplete.')]),
    ])


def inspector_panel(output_id, pin_id, heading='Plant inspector'):
    return html.Section(className='panel inspector-panel', children=[
        block_title('FACILITY INTELLIGENCE', heading, 'Details on demand'),
        html.Div(id=output_id, className='inspector-body inspector-rich'),
        html.Div(className='inspector-action', children=[
            html.Button('＋  Add to shortlist', id=pin_id, n_clicks=0,
                        className='button primary full')]),
    ])


def axis_options():
    return [{'label':label,'value':key} for key,label in core.PCP_FIELDS.items()]

SCENARIO_FIELDS=[('co2','Min. modeled CO₂ (Mt)',0,CO2_MAX,.1),('age','Min. age in 2021 (yrs)',0,AGE_MAX,1),
                 ('cf','Max. reported CF (%)',0,100,1),('capacity','Max. capacity (MW)',0,CAP_MAX,10),
                 ('change','Max. historical change (%)',-100,None,1)]

def scenario_card(letter,title,defaults):
    prefix='scenario-'+letter.lower()+'-'
    return html.Details(className='scenario-criteria',children=[
        html.Summary([html.Span(letter,className='scenario-letter '+letter.lower()),html.Strong(title)]),
        html.Div([html.P('Leave a threshold blank to ignore it.',className='field-hint'),
            *[field(label,dcc.Input(id=prefix+key,type='number',min=lo,max=hi,step=step,value=defaults[key],debounce=0.35,persistence=True,persistence_type='session',placeholder='Any',className='scenario-number')) for key,label,lo,hi,step in SCENARIO_FIELDS],
            dcc.Checklist(id=prefix+'strict',options=[{'label':'Require complete, reported, unflagged evidence','value':'strict'}],value=[],persistence=True,persistence_type='session',className='scenario-strict')],className='scenario-fields')])


def tool_button(label,id,title=None):
    return html.Button(label,id=id,n_clicks=0,title=title or label,className='button button-outline tool-button')


def drawer(id,title,subtitle,children):
    return html.Aside(id=id+'-drawer',className='context-drawer',style={'display':'none'},children=[
        html.Div([html.Div([html.H2(title),html.P(subtitle,className='small-muted')]),
                  html.Button('×',id='close-'+id,n_clicks=0,className='drawer-close',title='Close '+title,**{'aria-label':'Close '+title})],className='drawer-header'),
        html.Div(children,className='drawer-body')])


# The sidebar is the only persistent control surface. Both primary charts stay mounted.
SCENARIO_SECTION=section('Scenario screening','Compare two strategies',[
    html.Div(id='scenario-mini-summary',className='scenario-mini-summary',role='status',**{'aria-live':'polite'}),
    field('Highlight on map',dcc.Dropdown(id='scenario-map-group',options=[{'label':'No scenario highlight','value':'off'},{'label':'All A matches','value':'A matches'},{'label':'All B matches','value':'B matches'},{'label':'Both strategies','value':'Both'},{'label':'A only','value':'A only'},{'label':'B only','value':'B only'}],value='off',clearable=False,className='clean-dropdown')),
    tool_button('Compare outcomes','open-scenario','Open candidate overlap, trade-offs and evidence sensitivity'),
    scenario_card('A','Emissions priority',analytics.DEFAULT_A),
    scenario_card('B','Age & utilization',analytics.DEFAULT_B),
    html.P('Results update after typing. Editing a strategy highlights its matches unless an overlap or exclusive group is selected. Thresholds are illustrative, not retirement recommendations.',className='field-hint'),
],icon='screen')
PCP_SECTION=section('PCP settings','Dimensions and emphasis',[
    field('Shown dimensions (2–6)',dcc.Dropdown(id='pcp-dimensions',options=axis_options(),value=DEFAULT['dimensions'],multi=True,clearable=False,className='clean-dropdown')),
    field('Reorder axis',dcc.Dropdown(id='axis-to-move',options=[{'label':core.PCP_FIELDS[k],'value':k} for k in DEFAULT['dimensions']],value=DEFAULT['dimensions'][0],clearable=False,className='clean-dropdown')),
    html.Div([tool_button('← Left','axis-left'),tool_button('Right →','axis-right')],className='axis-move-buttons'),
    html.Div(id='axis-order-label',className='field-hint'),
    field('Emphasize fuel',dcc.Dropdown(id='pcp-focus-fuel',options=[{'label':'All fuels','value':'All'}]+[{'label':f,'value':f} for f in core.PCP_FUELS],value='All',clearable=False,className='clean-dropdown')),
    field('Line density',dcc.RadioItems(id='pcp-density',options=[{'label':'Overview','value':'overview'},{'label':'Detailed','value':'detailed'}],value='overview',className='option-list')),
    html.P('Capacity, generation, CO₂ and generation change use log display (signed for change). Axis labels and brushes use real units; all complete records are evaluated.',className='field-hint')],icon='display')
# Keep scenario controls prominent, without expanding them by default.
# Existing six groups are unmodified; insert two new sections in the same rail.
SIDEBAR.children[-1].children.insert(5,SCENARIO_SECTION)
SIDEBAR.children[-1].children.insert(6,PCP_SECTION)


def regional_drawer():
    return drawer('regional','Regional comparison','Click a fuel segment to select its facilities.',[
        html.Div([field('Geography',dcc.Dropdown(id='region-level',options=[{'label':'Continent','value':'continent'},{'label':'Subregion','value':'region'},{'label':'Country','value':'country_long'}],value='continent',clearable=False,className='clean-dropdown')),
                  field('Measure',dcc.Dropdown(id='region-metric',options=[{'label':'Installed capacity','value':'capacity'},{'label':'Plant count','value':'count'},{'label':'Fuel mix (% of plants)','value':'share'},{'label':'Modeled CO₂','value':'co2'}],value='capacity',clearable=False,className='clean-dropdown'))],className='drawer-controls'),
        dcc.Graph(id='regional-chart',className='drawer-graph',responsive=True,config={'displaylogo':False,'responsive':True}),
        html.Div(id='regional-note',className='analysis-caption')])


def scatter_drawer():
    return drawer('scatter','Relationship explorer','Select points to refine the linked cohort; click a point to inspect.',[
        html.Div([field('Horizontal axis',dcc.Dropdown(id='scatter-x',options=axis_options(),value='year_capacity_factor_pct',clearable=False,className='clean-dropdown')),
                  field('Vertical axis',dcc.Dropdown(id='scatter-y',options=axis_options(),value='year_co2_mt',clearable=False,className='clean-dropdown'))],className='drawer-controls'),
        dcc.Checklist(id='scatter-log',options=[{'label':'Log display for size metrics','value':'log'}],value=['log'],className='scatter-log'),
        dcc.Graph(id='scatter-chart',className='drawer-graph',responsive=True,config={'displaylogo':False,'responsive':True,'modeBarButtonsToAdd':['lasso2d','select2d']}),
        html.Button('Apply point selection',id='apply-scatter',n_clicks=0,className='button button-primary'),html.Div(id='scatter-selection-note',className='small-muted'),
        html.Details([html.Summary('Correlation and data coverage'),html.Div(id='scatter-note',className='analysis-caption')],className='drawer-disclosure')])


def scenario_drawer():
    return drawer('scenario','Scenario outcomes','Same filtered fossil-plant cohort and reference year.',[
        html.Div(id='scenario-scope',className='analysis-caption'),
        dcc.Graph(id='overlap-chart',className='overlap-compact',responsive=True,config={'displayModeBar':False,'responsive':True}),
        html.Div(id='overlap-note',className='analysis-caption'),
        field('Candidate group',dcc.Dropdown(id='scenario-group',options=[{'label':x,'value':x} for x in ['Both','A only','B only']],value='Both',clearable=False,className='clean-dropdown')),
        field('Inspect candidate',dcc.Dropdown(id='scenario-plant',options=[],value=None,placeholder='Search qualifying facilities',clearable=True,optionHeight=56,className='clean-dropdown plant-autocomplete')),
        html.Div(id='scenario-plant-note',className='small-muted'),
        html.Button('Pin selected candidate',id='scenario-pin',n_clicks=0,disabled=True,className='button button-primary full'),
        html.Details([html.Summary('Candidate details'),html.Div(id='scenario-inspector',className='scenario-inspector')],className='drawer-disclosure'),
        html.Details([html.Summary('Compare trade-offs'),html.Div(id='scenario-table',className='scenario-table-wrap')],className='drawer-disclosure'),
        html.Details([html.Summary('Evidence sensitivity'),html.Div([dcc.RadioItems(id='evidence-scenario',options=[{'label':'A','value':'A'},{'label':'B','value':'B'}],value='A',inline=True,className='view-switch'),dcc.RadioItems(id='evidence-view',options=[{'label':'Retention','value':'steps'},{'label':'By region','value':'region'}],value='steps',inline=True,className='view-switch')],className='drawer-controls'),dcc.Graph(id='evidence-chart',className='drawer-graph evidence-graph',responsive=True,config={'displayModeBar':False,'responsive':True}),html.Div(id='evidence-note',className='analysis-caption')],className='drawer-disclosure'),
        tool_button('Export scenario results','export-scenarios'),
        html.P('Screening supports further assessment, not actual retirement decisions. Missing evidence is not a failure of suitability.',className='field-hint')])


def inspector_drawer():
    return drawer('inspect','Facility inspector','Inspect a plant without changing the cohort.',[
        dcc.Dropdown(id='inspect-picker',options=[],value=None,placeholder='Search the comparison cohort',searchable=True,clearable=True,maxHeight=280,optionHeight=56,className='clean-dropdown plant-autocomplete'),
        html.Div(id='match-count',className='small-muted'),
        html.Div(id='plant-inspector',className='inspector-rich'),
        html.Button('Pin inspected plant',id='pin-focused',n_clicks=0,className='button button-primary full')])


def shortlist_drawer():
    return drawer('shortlist','Saved shortlist','Independent of the current filters.',[
        html.Div(id='shortlist-summary',className='small-muted'),
        html.Div(id='shortlist-cards',className='shortlist-cards'),
        html.Button('Clear shortlist',id='clear-shortlist',n_clicks=0,className='button danger-ghost')])


app.layout=html.Div(className='app-shell single-workspace',children=[
    dcc.Store(id='selected-ids',data=[]),dcc.Store(id='pcp-brush',data={}),dcc.Store(id='focused-id',data=None),
    dcc.Store(id='axis-order',data=DEFAULT['dimensions']),dcc.Store(id='pinned-ids',storage_type='local',data=[]),
    dcc.Store(id='map-reset-token',data=0),dcc.Store(id='map-zoom-band',data=1.22),dcc.Store(id='active-drawer',data=None),
    dcc.Store(id='scenario-highlight',data={}),dcc.Download(id='download-shortlist'),dcc.Download(id='download-scenarios'),
    html.Header(className='topbar',children=[
        html.Div([html.Div('P',className='brand-mark'),html.Div([html.Strong('Fossil Atlas',className='brand-title'),html.Small('VISUAL DECISION SUPPORT',className='brand-subtitle')])],className='brand'),
        html.Div([html.H1('Fossil power plant screening'),html.Span('WRI Global Power Plant Database · June 2021 historical release',className='source-caption')],className='workspace-title'),
        html.Div([tool_button('Inspect plant','open-inspect'),html.Button([html.Span('Shortlist'),html.Span('0',id='nav-shortlist-total',className='shortlist-badge')],id='open-shortlist',n_clicks=0,className='button button-outline tool-button'),html.Button('Export',id='export-shortlist',n_clicks=0,disabled=True,className='button nav-export',title='Export shortlist as CSV')],className='navbar-actions')]),
    html.Main(className='page',children=[html.Div(className='workspace-grid',children=[
        SIDEBAR,
        html.Div(className='workspace-body',children=[
            html.Div(className='stats-grid',children=[stat_card('VISIBLE FACILITIES','kpi-plants','After filters'),stat_card('COUNTRIES','kpi-countries','After filters'),stat_card('INSTALLED CAPACITY','kpi-capacity','GW · nameplate'),stat_card('LINKED SELECTION','kpi-selected','Selected facilities')]),
            html.Div(className='main-charts',children=[
                html.Section(className='panel map-panel',children=[
                    html.Div([html.Div([html.H2('Global plant map'),html.Span('Select a region with box or lasso · click a plant to inspect',className='chart-hint')]),html.Div([tool_button('Regional comparison','open-regional'),tool_button('Reset view','reset-map-view'),tool_button('Clear selection','clear-map')],className='chart-actions')],className='chart-header'),
                    html.Div([html.Div(id='map-legend',className='legend-bar'),html.Div(id='selection-legend',className='selection-legend')],className='compact-legend'),
                    html.Div(dcc.Graph(id='plant-map',className='map-graph',responsive=True,style={'width':'100%'},config={'displaylogo':False,'responsive':True,'scrollZoom':True,'modeBarButtonsToAdd':['lasso2d','select2d']}),className='graph-slot'),
                    html.Div(id='map-note',className='chart-footer')]),
                html.Section(className='panel pcp-panel',children=[
                    html.Div([html.Div([html.H2('Plant characteristics'),html.Span('Brush axes to find matching plants · log scales, real units',className='chart-hint')]),html.Div([html.Span(f,className=f'fuel-key {f.lower()}') for f in core.FOSSIL]+[html.Span('Other',className='fuel-key non-fossil')],className='pcp-inline-legend',title='PCP color represents primary fuel; fuel emphasis dims other fuels.'),html.Div([tool_button('Relationships','open-scatter'),tool_button('Clear brush','clear-pcp')],className='chart-actions')],className='chart-header'),
                    html.Div(dcc.Graph(id='pcp-chart',className='pcp-graph',responsive=True,style={'width':'100%'},config={'displaylogo':False,'responsive':True}),className='graph-slot'),
                    html.Div(id='pcp-note',className='compact-pcp-note'),
                    html.Div(id='pcp-brush-summary',className='chart-footer brush-footer')])]),
            html.Div('Historical data · age in 2021 · CO₂ modeled, not measured · missing ≠ zero',className='method-footer'),
        ]),
    ])]),
    regional_drawer(),scatter_drawer(),scenario_drawer(),inspector_drawer(),shortlist_drawer(),
])


# =====================================================================
# Filtering and cohort computation
# =====================================================================

FILTER_INPUTS = [
    Input('group-filter', 'value'), Input('fuel-filter', 'value'),
    Input('continent-filter', 'value'), Input('region-filter', 'value'),
    Input('country-filter', 'value'), Input('plant-search', 'value'),
    Input('capacity-filter', 'value'), Input('provenance-filter', 'value'),
    Input('age-enabled', 'value'), Input('age-filter', 'value'),
    Input('cf-enabled', 'value'), Input('cf-filter', 'value'),
    Input('co2-enabled', 'value'), Input('co2-filter', 'value'),
    Input('trend-filter', 'value'), Input('unknown-filter', 'value'),
    Input('quality-filter', 'value'), Input('commissioning-filter', 'value'),
    Input('generation-source-filter', 'value'), Input('min-reported-years', 'value'),
    Input('generation-enabled','value'), Input('generation-filter','value'),
    Input('fuel-configuration-filter','value'),
]


def apply_filters(year, *values):
    (groups, fuels, continents, regions, countries, search, capacity,
     provenance, age_on, age, cf_on, cf, co2_on, co2, trend, unknown,
     quality, commissioning, gen_source, min_years, generation_on, generation_range, fuel_config) = values
    return core.filter_plants(
        core.get_year_frame(int(year)),
        groups=groups, fuels=fuels, continents=continents, regions=regions,
        countries=countries, search=search, capacity=capacity,
        provenance=provenance, age_on=bool(age_on), age=age,
        cf_on=bool(cf_on), cf=cf, co2_on=bool(co2_on), co2=co2,
        trend=trend, keep_unknown='include' in (unknown or []),
        quality=quality, commissioning=commissioning,
        generation_source=gen_source, min_reported_years=min_years or 0,
        generation_on=bool(generation_on), generation_range=generation_range,
        fuel_configuration=fuel_config or 'all')




@app.callback(
    Output('age-filter', 'disabled'),
    Output('cf-filter', 'disabled'),
    Output('co2-filter', 'disabled'),
    Output('generation-filter', 'disabled'),
    Input('age-enabled', 'value'),
    Input('cf-enabled', 'value'),
    Input('co2-enabled', 'value'),
    Input('generation-enabled', 'value'),
)
def toggle_analytical_ranges(age_on, cf_on, co2_on, generation_on):
    """Disabled sliders cannot suggest a filter is active when it is not."""
    return tuple(not bool(x) for x in (age_on,cf_on,co2_on,generation_on))


@app.callback(
    Output('capacity-range-label','children'),
    Output('age-range-label','children'),
    Output('cf-range-label','children'),
    Output('co2-range-label','children'),
    Output('generation-range-label','children'),
    Input('capacity-filter','value'), Input('age-filter','value'),
    Input('cf-filter','value'), Input('co2-filter','value'),
    Input('generation-filter','value'),
)
def describe_ranges(capacity,age,cf,co2,generation):
    def format_range(pair,unit='',decimals=0):
        if not pair or len(pair)!=2:
            return '—'
        return f'{pair[0]:,.{decimals}f}–{pair[1]:,.{decimals}f} {unit}'.strip()
    return (format_range(capacity,'MW'), format_range(age,'years'),
            format_range(cf,'%'), format_range(co2,'Mt',2),
            format_range(generation,'GWh'))


@app.callback(Output('nav-shortlist-total', 'children'), Input('pinned-ids', 'data'))
def update_nav_shortlist_count(ids):
    return str(len(set(str(x) for x in (ids or []) if str(x) in VALID_IDS)))


def analysis_cohort(year, values, map_ids, dimensions, brush):
    filtered = apply_filters(year, *values)
    cohort = filtered if not map_ids else filtered.loc[filtered.gppd_idnr.isin(map_ids)]
    if not brush:
        return cohort
    eligible, _ = core.pcp_cohort(filtered, map_ids, dimensions)
    matched_ids = core.brushed_ids(eligible, brush)
    return eligible.loc[eligible.gppd_idnr.isin(matched_ids)]


@app.callback(Output('fuel-filter','options'),Input('group-filter','value'))
def available_fuels(groups):
    """Disable fuel choices that cannot occur in the selected energy categories."""
    available = set(BASE.loc[BASE.fuel_group.isin(groups or []), 'primary_fuel'].dropna())
    return [{'label':fuel,'value':fuel,'disabled':fuel not in available} for fuel in FUELS]


@app.callback(Output('provenance-filter','options'),Input('generation-year','value'),
              Input('group-filter','value'))
def available_provenance(year,groups):
    """Do not offer unavailable model/reported statuses as selectable values."""
    frame = core.get_year_frame(int(year))
    available = set(frame.loc[frame.fuel_group.isin(groups or []),'year_provenance'])
    return [{'label':label,'value':key,'disabled':key not in available}
            for key,label in core.PROVENANCE_LABELS.items()]


@app.callback(Output('region-filter', 'options'), Input('continent-filter', 'value'))
def update_regions(continents):
    frame = BASE if not continents else BASE.loc[BASE.continent.isin(continents)]
    return [{'label': region, 'value': region} for region in sorted(frame.region.unique())]


@app.callback(Output('country-filter', 'options'), Input('continent-filter', 'value'),
              Input('region-filter', 'value'))
def update_countries(continents, regions):
    frame = BASE
    if continents:
        frame = frame.loc[frame.continent.isin(continents)]
    if regions:
        frame = frame.loc[frame.region.isin(regions)]
    return [{'label': name, 'value': name} for name in sorted(frame.country_long.unique())]


# =====================================================================
# PCP axis selection / order / brushing
# =====================================================================

@app.callback(Output('axis-to-move', 'value'), Input('pcp-dimensions', 'value'),
              State('axis-to-move', 'value'))
def validate_selected_axis(dimensions, old):
    dimensions = [x for x in (dimensions or []) if x in core.PCP_FIELDS]
    return old if old in dimensions else (dimensions[0] if dimensions else None)


@app.callback(Output('axis-to-move', 'options'), Output('axis-order-label', 'children'),
              Input('axis-order', 'data'))
def show_axis_order(order):
    order = [c for c in (order or []) if c in core.PCP_FIELDS]
    return ([{'label': core.PCP_FIELDS[c], 'value': c} for c in order],
            'Axis order: ' + '  →  '.join(core.PCP_FIELDS[c] for c in order))


@app.callback(Output('axis-order', 'data'), Input('pcp-dimensions', 'value'),
              Input('axis-left', 'n_clicks'), Input('axis-right', 'n_clicks'), Input('pcp-chart','restyleData'),
              State('axis-to-move', 'value'), State('axis-order', 'data'))
def reorder_axes(dimensions, left, right, restyle, chosen, current):
    dims = list(dict.fromkeys(c for c in (dimensions or []) if c in core.PCP_FIELDS))[:6]
    if ctx.triggered_id=='pcp-chart':
        if not isinstance(restyle,list) or not restyle or not isinstance(restyle[0],dict): return no_update
        moved=restyle[0].get('dimensions')
        if isinstance(moved,list) and len(moved)==1 and isinstance(moved[0],list): moved=moved[0]
        if not isinstance(moved,list) or not all(isinstance(x,dict) for x in moved): return no_update
        order=[x.get('name') or next((k for k,v in core.PCP_AXIS_LABELS.items() if v==x.get('label')),None) for x in moved]
        return order if len(order)==len(dims) and set(order)==set(dims) and order!=current else no_update
    if ctx.triggered_id == 'pcp-dimensions' or not current:
        return dims
    order = [c for c in (current or []) if c in dims] + [c for c in dims if c not in (current or [])]
    if chosen in order and ctx.triggered_id in ('axis-left', 'axis-right'):
        index = order.index(chosen)
        target = index - 1 if ctx.triggered_id == 'axis-left' else index + 1
        if 0 <= target < len(order):
            order[index], order[target] = order[target], order[index]
    return order


@app.callback(Output('pcp-chart', 'figure'), Output('pcp-note', 'children'),
              Input('generation-year', 'value'), *FILTER_INPUTS,
              Input('selected-ids', 'data'), Input('axis-order', 'data'),
              Input('pcp-focus-fuel', 'value'), Input('pcp-density', 'value'),
              Input('clear-pcp', 'n_clicks'), Input('pcp-brush', 'data'))
def update_pcp(year, *args):
    n = len(FILTER_INPUTS)
    values = args[:n]
    map_ids, dimensions, focus, density, clear_clicks, current_brush = args[n:n+6]
    dimensions = [c for c in (dimensions or []) if c in core.PCP_FIELDS][:6]
    focus = focus if focus in ('All',*core.PCP_FUELS) else 'All'
    limit = 180 if density == 'detailed' else PCP_LINE_LIMIT
    filtered = apply_filters(year, *values)
    eligible, meta = core.pcp_cohort(filtered, map_ids, dimensions)
    # Clear must redraw the actual Plotly constraintrange; clearing only the
    # server-side brush store would leave a misleading visual selection.
    brush = (current_brush or {}) if ctx.triggered_id in ('pcp-focus-fuel','pcp-density','pcp-brush',None) else {}
    brush={k:v for k,v in brush.items() if k in dimensions}
    plotted=core.prioritize_pcp_sample(eligible,limit,focus,brush)
    figure = core.make_pcp(plotted, dimensions, int(year),
                           constraints=brush, eligible=eligible,focus_fuel=focus)
    scope = 'Linked selection' if map_ids else 'Sidebar filters'
    indicators = [
        ('COMPARISON COHORT', meta['cohort']),
        ('COMPLETE RECORDS', meta['eligible']),
        ('MISSING AXIS DATA', meta['missing']),
        ('SAMPLED LINES', len(plotted)),
    ]
    note = html.Div(className='pcp-coverage', children=[
        html.Div([html.Span(label),html.Strong(f'{value:,}')],className='pcp-coverage-item') for label,value in indicators
    ] + [html.P(f'{scope} · Display sample; brushing covers all complete records. Log display uses real-unit labels.',className='pcp-coverage-explainer')])
    return figure, note


@app.callback(Output('pcp-brush', 'data'), Input('pcp-chart', 'restyleData'),
              Input('clear-pcp', 'n_clicks'), Input('generation-year', 'value'),
              *FILTER_INPUTS, Input('selected-ids', 'data'), Input('axis-order', 'data'),
              State('pcp-brush', 'data'), prevent_initial_call=True)
def update_brush(restyle, clear, year, *args):
    # A cohort/axis change invalidates old brushes; a user drag updates them.
    if ctx.triggered_id != 'pcp-chart':
        return {}
    if not restyle or not isinstance(restyle, list):
        return no_update
    order, old = args[-2], args[-1]
    if not isinstance(restyle[0],dict) or not any(k.endswith('.constraintrange') for k in restyle[0]): return no_update
    updated=core.extract_restyle_constraints(restyle, old or {}, order or [], display_scaled=True)
    return updated if updated!=(old or {}) else no_update


@app.callback(Output('pcp-brush-summary', 'children'),
              Input('pcp-brush', 'data'), Input('selected-ids', 'data'),
              Input('axis-order', 'data'), Input('generation-year', 'value'), *FILTER_INPUTS)
def show_brush_counts(brush, map_ids, axes, year, *values):
    if not brush:
        text = 'No brush active · select a range on any axis.'
        return text
    filtered = apply_filters(year, *values)
    eligible, meta = core.pcp_cohort(filtered, map_ids, axes or [])
    found = core.brushed_ids(eligible, brush)
    message = f'{len(found):,} of {len(eligible):,} complete plants match · highlighted on map.'
    return message


# =====================================================================
# Map, lasso and viewport interaction
# =====================================================================

@app.callback(Output('map-reset-token', 'data'), Input('reset-map-view', 'n_clicks'),
              prevent_initial_call=True)
def reset_map_view(clicks):
    return int(clicks or 0)


@app.callback(Output('map-zoom-band', 'data'), Input('plant-map', 'relayoutData'), Input('reset-map-view','n_clicks'),
              State('map-zoom-band', 'data'), prevent_initial_call=True)
def remember_zoom(relayout, reset_clicks, previous):
    if ctx.triggered_id=='reset-map-view': return 1.22 if previous!=1.22 else no_update
    if not relayout or not isinstance(relayout, dict):
        return no_update
    zoom = relayout.get('map.zoom')
    if zoom is None:
        return no_update
    zoom = max(-2., min(19., float(zoom)))
    # Update only when sizes should noticeably change: limits unnecessary redraws.
    band = 1.22 if zoom < 2 else 3.0 if zoom < 4 else 5.0
    if band == previous:
        return no_update
    return band


@app.callback(Output('map-legend', 'children'), Input('color-mode', 'value'))
def show_map_legend(mode):
    if mode == 'fuel':
        return ([html.Span(name, className=f'fuel-key {name.lower()}')
                 for name in core.FOSSIL] +
                [html.Span('Non-fossil', className='fuel-key non-fossil'),
                 html.Span('Mixed / unspecified', className='fuel-key mixed'),
                 html.Span('Color = primary fuel', className='legend-note')])
    if mode == 'provenance':
        return [html.Span(label,className='fuel-key',style={'--key':core.PROVENANCE_COLORS[key]}) for key,label in core.PROVENANCE_LABELS.items()]
    return [html.Span('Blue gradient · modeled CO₂ (Mt/year)',className='legend-text'),
            html.Span('Unavailable / unmodeled',className='fuel-key',style={'--key':'#AAB4C0'})]


@app.callback(
    Output('plant-map', 'figure'), Output('kpi-plants', 'children'),
    Output('kpi-countries', 'children'), Output('kpi-capacity', 'children'),
    Output('kpi-selected', 'children'), Output('selection-legend','children'),
    Output('map-note', 'children'),
    Input('generation-year', 'value'), *FILTER_INPUTS,
    Input('color-mode', 'value'), Input('size-mode', 'value'), Input('cluster-mode', 'value'),
    Input('pcp-brush', 'data'), Input('selected-ids', 'data'),
    Input('axis-order', 'data'), Input('focused-id', 'data'),
    Input('map-reset-token', 'data'), Input('map-zoom-band', 'data'), Input('scenario-highlight','data'),
)
def update_map(year, *args):
    n = len(FILTER_INPUTS)
    filters = args[:n]
    mode, size, clusters, brush, map_ids, axes, focused, reset_token, zoom_band = args[n:n+9]
    scenario = args[n+9] if len(args)>n+9 else {}
    filtered = apply_filters(year, *filters)
    eligible, _ = core.pcp_cohort(filtered, map_ids, axes or [])
    matched = core.brushed_ids(eligible, brush) if brush else []
    group=(scenario or {}).get('group')
    scenario_active=bool(group and group!='off' and (scenario or {}).get('ids'))
    figure = core.make_map(filtered, int(year), mode, size, matched, focused,
                           zoom_for_markers=float(zoom_band or 1.22),
                           cluster='cluster' in (clusters or []), map_selected_ids=map_ids,scenario_active=scenario_active)
    figure.update_layout(
        # Use the bounded graph slot for actual responsive sizing.
        height=None, autosize=True,
        showlegend=False,  # Explicit legend lives above the map for every encoding.
        uirevision=f'plant-map-camera-reset-{int(reset_token or 0)}',
        selectionrevision=f'map-selection-{hash(tuple(sorted(map_ids or [])))}'
    )
    visible_selected = int(filtered.gppd_idnr.isin(map_ids or []).sum())
    legend=[]
    if visible_selected: legend.append(html.Span(f'Linked: {visible_selected:,}',className='selection-key linked'))
    if brush: legend.append(html.Span(f'Brush: {len(matched):,}',className='selection-key brushed'))
    group=(scenario or {}).get('group')
    if group and group!='off':
        subset=filtered.loc[filtered.gppd_idnr.isin((scenario or {}).get('ids',[]))]
        if not subset.empty:
            figure.add_trace(go.Scattermap(lat=subset.latitude,lon=subset.longitude,mode='markers',
                name='Scenario '+group,text=subset.name,customdata=subset[['gppd_idnr','country_long']].to_numpy(),
                marker=dict(size=core.overlay_marker_size(float(zoom_band or 1.22)),color='#d18424',opacity=.94),showlegend=False,
                hovertemplate='<b>%{text}</b><br>%{customdata[1]}<extra>Scenario candidate</extra>'))
        legend.append(html.Span(f'Scenario · {group}: {len(subset):,}',className='selection-key scenario'))
        if any(t.name=='Focused plant' for t in figure.data):
            figure.data=tuple(t for t in figure.data if t.name!='Focused plant')+tuple(t for t in figure.data if t.name=='Focused plant')
    note=f'{year} generation · '+('Clustering enabled; turn off for precise selection.' if clusters else 'Map selection narrows PCP · axis brushes highlight matches here.')
    return (figure,f'{len(filtered):,}',f'{filtered.country_long.nunique():,}',f'{filtered.capacity_mw.sum()/1000:,.1f}',f'{visible_selected:,}',legend,note)



@app.callback(Output('selected-ids', 'data'), Input('plant-map', 'selectedData'),
              Input('clear-map', 'n_clicks'), Input('plant-search', 'value'),
              Input('regional-chart','clickData'),Input('apply-scatter','n_clicks'),Input('reset-filters','n_clicks'),
              State('scatter-chart','selectedData'),State('region-metric','value'),State('plant-map', 'figure'),
              State('generation-year', 'value'), *[State(i.component_id, i.component_property)
                  for i in FILTER_INPUTS if i.component_id != 'plant-search'], State('selected-ids', 'data'),
              prevent_initial_call=True)
def save_map_selection(selected, clear, search, region_click, scatter_apply, reset_filters, scatter_selected, region_metric, figure, year, *args):
    trigger=ctx.triggered_id
    if trigger in ('clear-map','plant-search','reset-filters'):
        return []
    filters, old = list(args[:-1]), args[-1]
    filters.insert(5, search)
    frame=apply_filters(year,*filters)
    if trigger=='regional-chart':
        if not region_click or not region_click.get('points'): return no_update
        custom=region_click['points'][0].get('customdata')
        if not custom or len(custom)!=3: return no_update
        level, region, fuel=custom
        if level not in ('continent','region','country_long'): return no_update
        fuel_group=np.where(frame.primary_fuel.isin(core.FOSSIL),frame.primary_fuel,frame.fuel_group)
        subset=frame.loc[frame[level].eq(region) & (fuel_group==fuel)]
        if region_metric=='co2': subset=subset.loc[subset.year_co2_mt.notna()]
        return subset.gppd_idnr.tolist() if not subset.empty else no_update
    if trigger=='apply-scatter':
        if not scatter_selected or not scatter_selected.get('points'): return no_update
        allowed=set(frame.gppd_idnr) if not old else set(frame.gppd_idnr)&set(old)
        ids=[str(p['customdata'][0]) for p in scatter_selected['points'] if p.get('customdata') is not None and len(p['customdata']) and str(p['customdata'][0]) in allowed]
        return list(dict.fromkeys(ids)) if ids else no_update
    if trigger!='plant-map': return no_update
    if selected is None:
        # Some graph redraws send None even though the user did not clear a lasso.
        return no_update
    allowed = set(frame.gppd_idnr)
    traces = (figure or {}).get('data', [])
    picked = []
    for point in selected.get('points', []):
        custom = point.get('customdata')
        pid = str(custom[0]) if isinstance(custom, (list, tuple)) and custom else None
        if pid is None:
            ci = point.get('curveNumber')
            pi = point.get('pointIndex', point.get('pointNumber'))
            if isinstance(ci, int) and isinstance(pi, int) and 0 <= ci < len(traces):
                payload = traces[ci].get('customdata', [])
                if 0 <= pi < len(payload) and len(payload[pi]):
                    pid = str(payload[pi][0])
        if pid in allowed:
            picked.append(pid)
    return list(dict.fromkeys(picked))


# =====================================================================
# Inspect individual plants, with no table or candidate browser
# =====================================================================

def plant_options(frame, term, limit=30, include_country=False):
    """Only real dataset records, ordered by exact/prefix/substring matches."""
    term = (term or '').strip().casefold()
    if len(term) < 2:
        return []
    names = frame.name.fillna('').str.casefold()
    ids = frame.gppd_idnr.astype(str).str.casefold()
    countries = frame.country_long.fillna('').str.casefold()
    exact = names.eq(term) | ids.eq(term)
    prefix = names.str.startswith(term) | ids.str.startswith(term)
    matches = names.str.contains(term, regex=False) | ids.str.contains(term, regex=False)
    if include_country:
        matches |= countries.str.contains(term, regex=False)
    ranked = frame.loc[matches].copy()
    ranked['_rank'] = np.where(exact.loc[matches], 0, np.where(prefix.loc[matches], 1, 2))
    ranked = ranked.sort_values(['_rank', 'name', 'gppd_idnr']).head(limit)
    return [plant_option(r) for _, r in ranked.iterrows()]


def plant_option(row):
    pid = str(row['gppd_idnr'])
    return {'label': f'{row["name"]} · {row["country_long"]} · {row["primary_fuel"]} · {pid}',
            'value': pid}


@app.callback(Output('plant-search', 'options'), Input('plant-search', 'search_value'),
              Input('generation-year', 'value'),
              *[i for i in FILTER_INPUTS if i.component_id != 'plant-search'],
              State('plant-search', 'value'))
def suggest_plants(term, year, *args):
    filters, selected = list(args[:-1]), args[-1]
    filters.insert(5, None)  # Search across other filters, not the currently selected plant.
    frame = apply_filters(year, *filters)
    options = plant_options(frame, term)
    # Preserve the selected label so an incompatible filter can be cleared;
    # the actual record still must pass every filter to appear in a chart.
    if selected and not any(o['value'] == selected for o in options):
        row = BASE.loc[BASE.gppd_idnr.eq(str(selected))]
        if not row.empty:
            options.append(plant_option(row.iloc[0]))
    return options


@app.callback(Output('inspect-picker', 'options'), Input('inspect-picker', 'search_value'),
              Input('generation-year', 'value'), Input('selected-ids', 'data'),
              Input('pcp-brush', 'data'), Input('axis-order', 'data'),
              *FILTER_INPUTS, State('focused-id', 'data'))
def search_for_inspection(term, year, map_ids, brush, axes, *args):
    filters, focused = args[:-1], args[-1]
    frame = analysis_cohort(year, filters, map_ids, axes or [], brush)
    options = plant_options(frame, term, limit=35, include_country=True)
    if focused and not (term or '').strip():
        row = frame.loc[frame.gppd_idnr.eq(str(focused))]
        if not row.empty:
            return [plant_option(row.iloc[0])]
    return options


@app.callback(Output('focused-id', 'data'), Input('plant-map', 'clickData'),
              Input('inspect-picker', 'value'), Input('plant-search', 'value'),
              Input({'type': 'shortlist-open', 'plant': ALL}, 'n_clicks'), Input('scatter-chart','clickData'),
              prevent_initial_call=True)
def focus_plant(map_click, selected_id, search, open_clicks, scatter_click=None):
    trigger = ctx.triggered_id
    if trigger=='scatter-chart' and scatter_click and scatter_click.get('points'):
        custom=scatter_click['points'][0].get('customdata')
        if custom is not None and len(custom):
            pid=str(custom[0]); return pid if pid in VALID_IDS else no_update
    if trigger == 'plant-map' and map_click and map_click.get('points'):
        custom = map_click['points'][0].get('customdata')
        if custom is not None and len(custom):
            pid = str(custom[0])
            return pid if pid in VALID_IDS else no_update
    if trigger == 'inspect-picker' and selected_id:
        return str(selected_id) if str(selected_id) in VALID_IDS else no_update
    if trigger == 'plant-search':
        return str(search) if search and str(search) in VALID_IDS else None
    if isinstance(trigger, dict) and trigger.get('type') == 'shortlist-open':
        if ctx.triggered and ctx.triggered[0].get('value'):
            pid = str(trigger.get('plant'))
            return pid if pid in VALID_IDS else no_update
    return no_update


def plant_inspector(focus_id, year):
    if not focus_id:
        return html.Div(className='empty-inspector', children=[
            html.Div('⌕', className='inspector-empty-icon'),
            html.Strong('Select a facility'),
            html.P('Click a map marker, choose a plant suggestion, or use the '
                   'comparison lookup to investigate one facility.', className='small-muted'),
        ])
    records = core.get_year_frame(int(year))
    found = records.loc[records.gppd_idnr.eq(str(focus_id))]
    if found.empty:
        return html.P('Plant not found in source data.', className='small-muted')
    r=found.iloc[0]
    year=int(year)
    provenance=str(r.year_provenance)
    provenance_label=core.PROVENANCE_LABELS.get(provenance, provenance)
    status_class = 'source-' + ('review' if 'review' in provenance else provenance)

    def detail(label, value):
        return html.Div([html.Span(label), html.Strong(str(value))],className='detail-row')

    def metric(label, value, hint=''):
        return html.Div(className='inspector-metric', children=[
            html.Div(label, className='inspector-metric-label'),
            html.Strong(value, className='inspector-metric-value'),
            html.Small(hint, className='inspector-metric-hint') if hint else None,
        ])

    series=[]
    for y in core.YEARS:
        measurement=r.get(f'generation_gwh_{y}')
        limit=r.capacity_mw*(8784 if y%4==0 else 8760)/1000
        series.append(float(measurement) if pd.notna(measurement)
                      and 0<=measurement<=limit else None)
    observed=sum(v is not None for v in series)
    chart=go.Figure(go.Scatter(
        x=list(core.YEARS), y=series, mode='lines+markers', connectgaps=False,
        line=dict(color='#177C88',width=2.8,shape='linear'),
        marker=dict(size=6,color='#177C88',line=dict(color='#fff',width=1.3)),
        fill='tozeroy',fillcolor='rgba(23,124,136,.06)',
        hovertemplate='%{x}: %{y:,.1f} GWh<extra></extra>'))
    chart.update_layout(height=190, margin=dict(l=43,r=10,t=14,b=28),
        paper_bgcolor='#fff',plot_bgcolor='#fff',
        font=dict(color='#6D8294',size=10),
        xaxis=dict(dtick=1,range=[min(core.YEARS)-.25,max(core.YEARS)+.25],showgrid=False,zeroline=False),
        yaxis=dict(title='GWh',gridcolor='#ECF2F5',zeroline=False),
        showlegend=False,hovermode='x')

    note=r.get(f'estimated_generation_note_{year}') if year<=2017 else None
    note=note if pd.notna(note) and str(note).strip() else 'Unavailable'
    flags=r.get('data_quality_flags')
    flagged=bool(pd.notna(flags) and str(flags).strip())
    flags=str(flags).replace('|',', ') if flagged else 'No quality flags recorded'
    link=r.get('url')
    link=str(link).strip() if pd.notna(link) else ''
    link=link if link.startswith(('https://','http://')) else None
    fuel_color=core.FUEL_COLORS.get(str(r.primary_fuel),'#70899D')

    return html.Div(className='inspector-content', children=[
        html.Div(className='inspector-identity', children=[
            html.Div(className='inspector-name-row', children=[
                html.H3(str(r['name']),className='plant-name'),
                html.Span(provenance_label,className=f'provenance-pill {status_class}'),
            ]),
            html.P(f'{r.country_long}  ·  {r.region}',className='plant-subtitle'),
            html.Div(className='inspector-tag-row',children=[
                html.Span(str(r.primary_fuel),className='fuel-pill',
                          style={'--fuel-color':fuel_color}),
                html.Span(f'ID  {r.gppd_idnr}',className='plant-id-pill'),
            ]),
        ]),
        html.Div(className='inspector-metric-grid',children=[
            metric('INSTALLED CAPACITY',format_value(r.capacity_mw,' MW')),
            metric('GENERATION '+str(year),format_value(r.year_generation_gwh,' GWh')),
            metric('REPORTED UTILIZATION',format_value(r.year_capacity_factor_pct,'%')),
            metric('MODELED CO₂',format_value(r.year_co2_mt,' Mt',2),'scenario estimate'),
        ]),
        html.Div('FACILITY INFORMATION',className='eyebrow inspector-section-kicker'),
        detail('Age at 2021',format_value(r.plant_age_2021_years,' years')),
        detail('Generation provenance',provenance_label),
        detail('Quality flags',flags),
        html.Div('REPORTED GENERATION HISTORY  ·  2013–2019',
                 className='eyebrow inspector-chart-title'),
        dcc.Graph(figure=chart,config={'displayModeBar':False},
                  style={'height':'196px'}),
        html.P(f'{observed} year(s) with plausible reported generation. '
               'Gaps are not interpolated.',className='small-muted'),
        html.Details(className='inspector-source-details',children=[
            html.Summary('Source details and methodology'),
            html.Div(className='source-details-body',children=[
                detail('Source', r.get('source') if pd.notna(r.get('source')) else 'Unknown'),
                detail('Generation data source',r.get('generation_data_source')
                       if pd.notna(r.get('generation_data_source')) else 'Unknown'),
                detail('Estimate method',note),
                html.A('Open original source',href=link,target='_blank',
                    rel='noopener noreferrer',className='source-link') if link else None,
            ]),
        ]),
        html.P('Emissions are hypothetical fuel-based scenarios, not observed emissions. '
               'Reported generation is not independently verified.',className='inspector-caveat'),
    ])


@app.callback(Output('plant-inspector', 'children'),
              Input('focused-id', 'data'), Input('generation-year', 'value'))
def update_inspector(focus_id, year):
    content = plant_inspector(focus_id, year)
    return content


@app.callback(Output('match-count', 'children'), Input('generation-year', 'value'),
              *FILTER_INPUTS, Input('selected-ids', 'data'),
              Input('pcp-brush', 'data'), Input('axis-order', 'data'))
def update_match_count(year, *args):
    filters = args[:len(FILTER_INPUTS)]
    map_ids, brush, dimensions = args[len(FILTER_INPUTS):]
    records = analysis_cohort(year, filters, map_ids, dimensions or [], brush)
    return f'{len(records):,} records available for inspection in the current comparison cohort.'


# =====================================================================
# Shortlist: only saved records appear as cards (not a candidate list).
# =====================================================================

def shortlist_card(plant, year):
    pid=str(plant['gppd_idnr'])
    fuel=str(plant['primary_fuel'])
    return html.Div(className='shortlist-card', children=[
        html.Div(className='shortlist-fuel-dot',
                 style={'background':core.FUEL_COLORS.get(fuel,'#8799A9')}),
        html.Div(className='shortlist-item-body', children=[
            html.Button(str(plant['name']),id={'type':'shortlist-open','plant':pid},
                n_clicks=0,className='shortlist-open',title='Inspect this plant'),
            html.Span(f'{plant["country_long"]} · {fuel} · '
                      f'{format_value(plant["capacity_mw"]," MW")}',
                      className='shortlist-meta'),
            html.Span(f'{year} generation: '
                      f'{core.PROVENANCE_LABELS.get(plant["year_provenance"],"Missing")}',
                      className='shortlist-provenance'),
        ]),
        html.Button('Remove',id={'type':'shortlist-remove','plant':pid},
            n_clicks=0,className='button danger-ghost shortlist-remove'),
    ])


@app.callback(Output('pinned-ids', 'data'),
              Input('pin-focused', 'n_clicks'),
              Input({'type':'shortlist-remove','plant':ALL}, 'n_clicks'),
              Input('clear-shortlist', 'n_clicks'), Input('scenario-pin','n_clicks'),
              State('focused-id', 'data'), State('pinned-ids', 'data'), State('scenario-plant','value'),
              prevent_initial_call=True)
def update_shortlist(pin_explore, remove_clicks, clear, scenario_pin, focused, current, scenario_plant=None):
    saved = list(dict.fromkeys(str(pid) for pid in (current or []) if str(pid) in VALID_IDS))
    trigger = ctx.triggered_id
    if trigger == 'clear-shortlist':
        return []
    if trigger=='scenario-pin':
        return list(dict.fromkeys(saved+[str(scenario_plant)])) if scenario_plant and str(scenario_plant) in VALID_IDS else no_update
    if trigger == 'pin-focused':
        if focused and str(focused) in VALID_IDS:
            return list(dict.fromkeys(saved + [str(focused)]))
        return no_update
    if isinstance(trigger, dict) and trigger.get('type') == 'shortlist-remove':
        if ctx.triggered and ctx.triggered[0].get('value'):
            return [pid for pid in saved if pid != str(trigger.get('plant'))]
    return no_update


@app.callback(Output('pin-focused', 'disabled'),
              Output('pin-focused', 'children'),
              Output('export-shortlist', 'disabled'), Output('clear-shortlist', 'disabled'),
              Input('focused-id', 'data'), Input('pinned-ids', 'data'))
def update_action_states(focused, pinned):
    saved = set(str(i) for i in (pinned or []) if str(i) in VALID_IDS)
    can_pin = bool(focused) and str(focused) in VALID_IDS and str(focused) not in saved
    message = ('Pinned to shortlist' if focused and str(focused) in saved
               else 'Pin inspected plant' if can_pin else 'Select a plant to pin')
    return not can_pin, message, not bool(saved), not bool(saved)


@app.callback(Output('shortlist-summary', 'children'),
              Output('shortlist-cards', 'children'), Input('pinned-ids', 'data'),
              Input('generation-year', 'value'))
def render_shortlist(ids, year):
    rows = core.get_year_frame(int(year)).set_index('gppd_idnr', drop=False)
    valid = list(dict.fromkeys(str(pid) for pid in (ids or []) if str(pid) in rows.index))
    cards = [shortlist_card(rows.loc[pid], int(year)) for pid in valid]
    if not cards:
        cards = [html.P('No plants saved yet. Select any facility from the map or '
                        'inspection search, then click “Pin inspected plant”.',
                        className='shortlist-empty')]
    return (f'{len(valid):,} saved candidate(s) · independent of map filters', cards)


@app.callback(Output('download-shortlist', 'data'), Input('export-shortlist', 'n_clicks'),
              State('pinned-ids', 'data'), State('generation-year', 'value'),
              prevent_initial_call=True)
def export_shortlist(clicks, ids, year):
    if not ids:
        raise PreventUpdate
    records = core.get_year_frame(int(year))
    records = records.loc[records.gppd_idnr.isin(ids)].copy()
    return dcc.send_data_frame(core.frame_to_export(records, int(year)).to_csv,
                               f'PlantScope_shortlist_{year}.csv', index=False)


# =====================================================================
# Restore all filters: one reset callback; no duplicate outputs.
# =====================================================================

@app.callback(
    Output('group-filter', 'value'), Output('fuel-filter', 'value'),
    Output('continent-filter', 'value'), Output('region-filter', 'value'),
    Output('country-filter', 'value'), Output('plant-search', 'value'),
    Output('generation-year', 'value'), Output('capacity-filter', 'value'),
    Output('provenance-filter', 'value'), Output('age-enabled', 'value'),
    Output('age-filter', 'value'), Output('cf-enabled', 'value'),
    Output('cf-filter', 'value'), Output('co2-enabled', 'value'),
    Output('co2-filter', 'value'), Output('trend-filter', 'value'),
    Output('unknown-filter', 'value'), Output('quality-filter', 'value'),
    Output('commissioning-filter', 'value'),
    Output('generation-source-filter', 'value'),
    Output('min-reported-years', 'value'), Output('color-mode', 'value'),
    Output('size-mode', 'value'), Output('pcp-dimensions', 'value'),
    Output('generation-enabled','value'), Output('generation-filter','value'),
    Output('fuel-configuration-filter','value'),
    Output('pcp-focus-fuel','value'), Output('pcp-density','value'),
    Input('reset-filters', 'n_clicks'), prevent_initial_call=True)
def reset_all_filters(clicks):
    d = DEFAULT
    return (d['groups'], d['fuels'], d['continents'], d['regions'], d['countries'],
            d['search'], d['year'], d['capacity'], d['provenance'], d['age_enabled'],
            d['age'], d['cf_enabled'], d['cf'], d['co2_enabled'], d['co2'],
            d['trend'], d['unknown'], d['quality'], d['commissioning'],
            d['generation_source'], d['min_reported_years'], d['color'],
            d['size'], d['dimensions'], d['generation_enabled'],
            d['generation'], d['fuel_configuration'], d['pcp_focus'], d['pcp_density'])


# =====================================================================
# Analytical extensions — all charts use the same authoritative dataset.
# =====================================================================
@app.callback(Output('regional-chart','figure'),Output('regional-note','children'),
              Input('generation-year','value'),*FILTER_INPUTS,Input('region-level','value'),Input('region-metric','value'))
def update_regions_chart(year,*args):
    return analytics.regional_figure(apply_filters(year,*args[:-2]),args[-2],args[-1])

@app.callback(Output('scatter-chart','figure'),Output('scatter-note','children'),
              Input('generation-year','value'),*FILTER_INPUTS,Input('selected-ids','data'),Input('pcp-brush','data'),Input('axis-order','data'),
              Input('scatter-x','value'),Input('scatter-y','value'),Input('scatter-log','value'))
def update_scatter(year,*args):
    n=len(FILTER_INPUTS); filters=args[:n]; selected,brush,axes,x,y,log=args[n:]
    frame=apply_filters(year,*filters)
    cohort=frame if not selected else frame.loc[frame.gppd_idnr.isin(selected)]
    highlights=None if not brush else set(core.brushed_ids(core.pcp_cohort(frame,selected,axes or [])[0],brush))
    return analytics.scatter_figure(cohort,x,y,highlights,'log' in (log or []))

@app.callback(Output('scatter-selection-note','children'),Output('apply-scatter','disabled'),Input('scatter-chart','selectedData'))
def scatter_selection_note(data):
    count=len((data or {}).get('points',[]))
    return (f'{count:,} points selected · apply to linked cohort' if count else 'Draw a lasso or box first.',not bool(count))

SCENARIO_INPUTS=[Input('scenario-'+letter+'-'+key,'value') for letter in ('a','b') for key in [x[0] for x in SCENARIO_FIELDS]+['strict']]

def unpack_scenarios(args):
    keys=[x[0] for x in SCENARIO_FIELDS]+['strict']; n=len(keys)
    configs=[dict(zip(keys,args[:n])),dict(zip(keys,args[n:2*n]))]
    for c in configs: c['strict']='strict' in (c['strict'] or [])
    return configs

def scenario_frame(year,filters,selected):
    frame=apply_filters(year,*filters)
    frame=frame.loc[frame.fuel_group.eq('Fossil')]
    return frame if not selected else frame.loc[frame.gppd_idnr.isin(selected)]

def scenario_context(year,args):
    n=len(FILTER_INPUTS); frame=scenario_frame(year,args[:n],args[n]); a,b=unpack_scenarios(args[n+1:]); return frame,a,b

@app.callback(Output('scenario-scope','children'),Output('overlap-chart','figure'),Output('overlap-note','children'),
              Output('evidence-chart','figure'),Output('evidence-note','children'),Output('scenario-table','children'),
              Output('scenario-plant','options'),Output('scenario-plant','value'),Output('scenario-plant-note','children'),
              Input('generation-year','value'),*FILTER_INPUTS,Input('selected-ids','data'),*SCENARIO_INPUTS,
              Input('evidence-scenario','value'),Input('evidence-view','value'),Input('scenario-group','value'),State('scenario-plant','value'))
def update_scenarios(year,*args):
    frame,a,b=scenario_context(year,args[:-4]); evidence_choice,evidence_view,group,old_plant=args[-4:]
    aa,bb,au,bu,groups=analytics.compare(frame,a,b)
    evconfig=dict(a if evidence_choice=='A' else b,strict=False)
    baseline=analytics.screen(frame,evconfig)[0]; strict=analytics.evidence_steps(baseline)[-1]
    overlap=analytics.overlap_figure(groups)
    if evidence_view=='region':
        evidence=analytics.evidence_region_figure(baseline,strict)
    else: evidence=analytics.evidence_figure(baseline)
    note=(f'{len(strict):,} / {len(baseline):,} initial matches retained with strict evidence ({len(strict)/len(baseline)*100:.1f}%).' if len(baseline) else '0 initial matches · no evidence retention rate.')+' Excluded records are not proven unsuitable.'
    def fmt(x):
        if pd.isna(x): return '—'
        return f'{x:,}' if isinstance(x,(int,np.integer)) else f'{x:,.1f}'
    summaries=[analytics.summary(r) for r in (aa,bb,baseline,strict)]
    rows=[html.Tr([html.Th('Indicator'),html.Th('A'),html.Th('B'),html.Th(f'{evidence_choice} initial'),html.Th(f'{evidence_choice} strict')])]
    for key in summaries[0]:
        rows.append(html.Tr([html.Th(key)]+[html.Td(fmt(d[key])) for d in summaries]))
    rows.append(html.Tr([html.Th('Insufficient evidence'),html.Td(f'{len(au):,}'),html.Td(f'{len(bu):,}'),html.Td('—'),html.Td('—')]))
    table=html.Div([html.Table(rows,className='scenario-table'),html.P('CO₂ totals exclude missing values; medians use available values. Initial/strict columns hold screening thresholds constant.',className='analysis-caption')])
    candidates=frame.loc[frame.gppd_idnr.isin(groups.get(group,set()))].sort_values(['name','gppd_idnr'])
    options=[plant_option(r) for _,r in candidates.iterrows()]
    keep=old_plant if old_plant and old_plant in set(candidates.gppd_idnr) else None
    union=len(set(aa.gppd_idnr)|set(bb.gppd_idnr)); both=len(groups['Both'])
    overlapnote=f'{both:,} qualify in both · '+(f'{100*both/union:.1f}% of the union.' if union else 'No qualifying candidates.')+' Click a bar to inspect its group.'
    scope=f'{len(frame):,} fossil plants · {year} generation year · current sidebar filters and linked selection; PCP brushes excluded. Clear screening filters for an unrestricted comparison.'
    return scope,overlap,overlapnote,evidence,note,table,options,keep,f'{len(candidates):,} qualifying plants in this group.'

@app.callback(Output('scenario-group','value'),Input('overlap-chart','clickData'),prevent_initial_call=True)
def choose_scenario_group(data):
    pts=(data or {}).get('points',[]); group=pts[0].get('customdata') if pts else None
    return group if group in ('A only','Both','B only') else no_update

@app.callback(Output('scenario-inspector','children'),Output('scenario-pin','disabled'),Output('scenario-pin','children'),
              Input('scenario-plant','value'),Input('generation-year','value'),Input('pinned-ids','data'))
def scenario_inspect(pid,year,pinned):
    if not pid or pid not in VALID_IDS: return [],True,'Pin selected candidate'
    saved=pid in (pinned or [])
    return plant_inspector(pid,year),saved,'Already pinned' if saved else 'Pin selected candidate'

@app.callback(Output('download-scenarios','data'),Input('export-scenarios','n_clicks'),
              State('generation-year','value'),*[State(i.component_id,i.component_property) for i in FILTER_INPUTS],State('selected-ids','data'),
              *[State(i.component_id,i.component_property) for i in SCENARIO_INPUTS],prevent_initial_call=True)
def export_scenarios(clicks,year,*args):
    frame,a,b=scenario_context(year,args); aa,bb,au,bu,groups=analytics.compare(frame,a,b)
    out=core.frame_to_export(frame,int(year))
    # Preserve all cohort records, including failed and insufficient-evidence records.
    for letter,passed,unknown,cfg in [('A',aa,au,a),('B',bb,bu,b)]:
        out['scenario_'+letter+'_status']=np.select([frame.gppd_idnr.isin(passed.gppd_idnr),frame.gppd_idnr.isin(unknown.gppd_idnr)],['qualifies','insufficient_evidence'],default='does_not_meet_thresholds')
        for k,v in cfg.items(): out['scenario_'+letter+'_'+k]=v
    return dcc.send_data_frame(out.to_csv,f'PlantScope_scenarios_{year}.csv',index=False)


DRAWERS=('regional','scatter','scenario','inspect','shortlist')

@app.callback(Output('active-drawer','data'),*[Input('open-'+k,'n_clicks') for k in DRAWERS],
    *[Input('close-'+k,'n_clicks') for k in DRAWERS],Input('focused-id','data'),State('active-drawer','data'),prevent_initial_call=True)
def choose_drawer(*args):
    trigger=ctx.triggered_id; current=args[-1]; focused=args[-2]
    if trigger=='focused-id':
        return 'inspect' if focused else (None if current=='inspect' else no_update)
    if isinstance(trigger,str) and trigger.startswith('open-'):
        key=trigger[5:]; return key if key in DRAWERS and key!=current else None
    if isinstance(trigger,str) and trigger.startswith('close-'): return None
    return no_update

@app.callback(*[Output(k+'-drawer','style') for k in DRAWERS],Input('active-drawer','data'))
def display_drawer(active):
    return tuple({'display':'flex' if k==active else 'none'} for k in DRAWERS)

@app.callback(Output('scenario-map-group','value'),Output('cluster-mode','value'),Input('reset-filters','n_clicks'),*SCENARIO_INPUTS,State('scenario-map-group','value'),prevent_initial_call=True)
def reset_display_overlays(_, *args):
    # Start a map highlight when the analyst first edits a scenario, not on page load.
    # Keep an explicit overlap/exclusive-group choice when parameters change.
    trigger=ctx.triggered_id
    if not args or trigger=='reset-filters':
        return 'off',[]
    if isinstance(trigger,str) and trigger.startswith(('scenario-a-','scenario-b-')):
        current=args[-1]
        if current in (None,'off','A matches','B matches'):
            group='A matches' if trigger.startswith('scenario-a-') else 'B matches'
            return (group if current!=group else no_update),no_update
    return no_update,no_update

@app.callback(Output('scenario-mini-summary','children'),Output('scenario-highlight','data'),
    Input('generation-year','value'),*FILTER_INPUTS,Input('selected-ids','data'),*SCENARIO_INPUTS,Input('scenario-map-group','value'))
def scenario_sidebar(year,*args):
    frame,a,b=scenario_context(year,args[:-1]); group=args[-1]
    aa,bb,au,bu,groups=analytics.compare(frame,a,b)
    groups={**groups,'A matches':set(aa.gppd_idnr),'B matches':set(bb.gppd_idnr)}
    content=html.Div([
        html.Div([html.Span('Live results',className='scenario-live-label'),html.Span(f'{len(frame):,} plants · {year}',className='scenario-live-scope')],className='scenario-live-heading'),
        html.Div([html.Div([html.Span('A matches'),html.Strong(f'{len(aa):,}')]),html.Div([html.Span('B matches'),html.Strong(f'{len(bb):,}')]),html.Div([html.Span('Both'),html.Strong(f'{len(groups["Both"]):,}')])],className='scenario-counts'),
        html.Div(f'Insufficient evidence: A {len(au):,} · B {len(bu):,}',className='scenario-live-scope'),
    ],className='scenario-live-results')
    return content,{'group':group,'ids':sorted(groups.get(group,set()))}


if __name__ == '__main__':
    print(f'Fossil Atlas ready: {len(BASE):,} plants in {BASE.country.nunique()} countries')
    app.run(debug=False, host='127.0.0.1', port=8050)
