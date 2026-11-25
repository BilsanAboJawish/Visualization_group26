"""Pure analytical functions for PlantScope. No Dash dependency."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import core

FIELDS = dict(core.PCP_FIELDS)
SCREEN = {'co2': ('year_co2_mt', 'min'), 'age': ('plant_age_2021_years','min'),
          'cf': ('year_capacity_factor_pct','max'), 'capacity': ('capacity_mw','max'),
          'change': ('reported_gen_change_pct','max')}
DEFAULT_A = dict(co2=2, age=None, cf=None, capacity=None, change=None, strict=False)
DEFAULT_B = dict(co2=.5, age=35, cf=40, capacity=None, change=None, strict=False)
EVIDENCE_FIELDS = ['year_co2_mt','plant_age_2021_years','year_capacity_factor_pct','reported_gen_change_pct','capacity_mw']
COLORS = {'A only':'#347FC7','Both':'#147A70','B only':'#B45E78'}

def graph_layout(fig, **kw):
    fig.update_layout(template='plotly_white', autosize=True, paper_bgcolor='#fff', plot_bgcolor='#fff',
        font=dict(family='Arial, sans-serif',size=11,color='#28485b'),
        margin=dict(l=58,r=24,t=35,b=48),legend=dict(orientation='h',y=1.04,x=0), **kw)
    return fig

def regional_figure(frame, level, metric):
    level = level if level in ('continent','region','country_long') else 'continent'
    metric = metric if metric in ('count','capacity','co2','share') else 'capacity'
    f=frame.copy(); f['_fuel']=np.where(f.primary_fuel.isin(core.FOSSIL),f.primary_fuel,f.fuel_group)
    colors={**core.FUEL_COLORS,'Non-fossil':'#71859B','Mixed / unspecified':'#B2A3C1'}
    if metric=='co2': f=f.loc[f.year_co2_mt.notna()].copy()
    f['_v']=f.capacity_mw/1000 if metric=='capacity' else f.year_co2_mt if metric=='co2' else 1.
    g=f.groupby([level,'_fuel'], observed=True)['_v'].sum().unstack(fill_value=0)
    totals=g.sum(axis=1); ordered=totals.sort_values(ascending=False).index.tolist()
    if metric=='share': g=g.div(totals.replace(0,np.nan),axis=0)*100
    # Show all groups with an adjustable chart height/scrolling UI, rather than silently truncating.
    fig=go.Figure()
    for fuel in colors:
        if fuel not in g: continue
        fig.add_bar(x=ordered,y=g.loc[ordered,fuel],name=fuel,marker_color=colors[fuel],
            customdata=[[level,r,fuel] for r in ordered],hovertemplate='%{x}<br>'+fuel+': %{y:,.2f}<extra></extra>')
    title={'count':'Plants','capacity':'Installed capacity (GW)','co2':'Modeled CO₂ (Mt/year)','share':'Plant share (%)'}[metric]
    graph_layout(fig,barmode='stack',clickmode='event',xaxis=dict(title='',type='category',categoryorder='array',categoryarray=ordered,automargin=True,tickangle=-25 if len(ordered)>6 else 0),yaxis=dict(title=title,rangemode='tozero',**({'range':[0,100]} if metric=='share' else {})))
    if len(ordered)>12:
        fig.update_xaxes(range=[-.5,11.5]); fig.update_layout(dragmode='pan')
    return fig, f'{len(f):,} of {len(frame):,} filtered records contribute · {len(ordered)} groups · click a fuel segment to select those plants' + (' · estimated and reported generation included; unavailable excluded' if metric=='co2' else '') + (' · pan horizontally to see all groups' if len(ordered)>15 else '')

def scatter_figure(frame, x, y, highlighted=None, log=False):
    x=x if x in FIELDS else 'year_capacity_factor_pct'; y=y if y in FIELDS else 'year_co2_mt'
    valid=frame[x].notna() & frame[y].notna() & np.isfinite(frame[x]) & np.isfinite(frame[y]);
    logx=bool(log and x in core.PCP_LOG_FIELDS); logy=bool(log and y in core.PCP_LOG_FIELDS)
    # log1p preserves meaningful zero values unlike standard log axes.
    f=frame.loc[valid].copy(); fig=go.Figure()
    colors={**core.FUEL_COLORS,'Non-fossil':'#71859B','Mixed / unspecified':'#B2A3C1'}
    f['_fuel']=np.where(f.primary_fuel.isin(core.FOSSIL),f.primary_fuel,f.fuel_group)
    for fuel,color in colors.items():
        p=f.loc[f._fuel.eq(fuel)]
        if p.empty: continue
        marker=dict(color=color,size=6,opacity=.58)
        active=[i for i,pid in enumerate(p.gppd_idnr) if pid in highlighted] if highlighted is not None else None
        fig.add_trace(go.Scattergl(x=np.log10(1+p[x].clip(lower=0)) if logx else p[x],y=np.log10(1+p[y].clip(lower=0)) if logy else p[y],mode='markers',name=fuel,marker=marker,
            customdata=p[['gppd_idnr','name','country_long',x,y]].to_numpy() if x!=y else np.column_stack((p.gppd_idnr,p.name,p.country_long,p[x],p[y])), selectedpoints=active,
            selected=dict(marker=dict(opacity=1,size=8)),unselected=dict(marker=dict(opacity=.12)),
            hovertemplate='<b>%{customdata[1]}</b><br>%{customdata[2]}<br>'+FIELDS[x]+': %{customdata[3]:,.2f}<br>'+FIELDS[y]+': %{customdata[4]:,.2f}<extra></extra>'))
    graph_layout(fig,dragmode='lasso',clickmode='event',xaxis=dict(title=FIELDS[x]+(' · log₁₀(1+x)' if logx else ''),zeroline=False),yaxis=dict(title=FIELDS[y]+(' · log₁₀(1+x)' if logy else ''),zeroline=False))
    def corr(p):
        return p[x].rank().corr(p[y].rank()) if x!=y and len(p)>1 and p[x].nunique()>1 and p[y].nunique()>1 else np.nan
    rho=corr(f)
    fuel_stats=[]
    for fuel,p in f.groupby('_fuel'):
        value=corr(p)
        fuel_stats.append(f'{fuel}: {value:.2f} (n={len(p):,})' if pd.notna(value) else f'{fuel}: n={len(p):,}')
    note=f'{len(f):,} of {len(frame):,} cohort plants with both values · '+(f'Spearman ρ = {rho:.2f}' if pd.notna(rho) else 'Spearman ρ unavailable')
    if fuel_stats and x!=y: note+=' · By fuel: '+', '.join(fuel_stats)
    if x==y: note+=' · Choose distinct axes to investigate a relationship.'
    if {'year_co2_mt','year_capacity_factor_pct'} <= {x,y}: note+=' · CO₂ and capacity factor share generation inputs.'
    return fig,note+' · Association is not causation.'

def screen(frame, config):
    """Three-valued screening: known failure wins over missing evidence."""
    fail=pd.Series(False,index=frame.index); unknown=fail.copy()
    for key,(col,direction) in SCREEN.items():
        value=config.get(key)
        if value is None: continue
        values=frame[col]; missing=values.isna() | ~np.isfinite(values)
        unknown |= missing
        fail |= (~missing) & (values.lt(float(value)) if direction=='min' else values.gt(float(value)))
    # Strict evidence is an eligibility rule, not evidence of technical unsuitability.
    eligible=~fail & ~unknown
    if config.get('strict'):
        strict=frame.year_provenance.eq('reported') & frame[EVIDENCE_FIELDS].notna().all(axis=1) & ~frame.quality_flagged
        unknown |= eligible & ~strict
        eligible &= strict
    return frame.loc[eligible],frame.loc[~fail & unknown],frame.loc[fail]

def compare(frame,a,b):
    aa,au,af=screen(frame,a); bb,bu,bf=screen(frame,b)
    ai=set(aa.gppd_idnr); bi=set(bb.gppd_idnr)
    groups={'A only':ai-bi,'Both':ai&bi,'B only':bi-ai}
    return aa,bb,au,bu,groups

def evidence_steps(frame):
    reported=frame.loc[frame.year_provenance.eq('reported')]
    complete=reported.loc[reported[EVIDENCE_FIELDS].notna().all(axis=1)]
    clean=complete.loc[~complete.quality_flagged]
    return [frame,reported,complete,clean]

def summary(frame):
    return {'Plants':len(frame),'Capacity (GW)':frame.capacity_mw.sum()/1000,
        'Modeled CO₂ (Mt)':frame.year_co2_mt.sum(min_count=1),'CO₂ coverage':int(frame.year_co2_mt.notna().sum()),
        'Median age (years)':frame.plant_age_2021_years.median(),'Median CF (%)':frame.year_capacity_factor_pct.median(),
        'Median generation change (%)':frame.reported_gen_change_pct.median(), 'Countries':frame.country_long.nunique(),
        'Complete screening attributes':int(frame[EVIDENCE_FIELDS].notna().all(axis=1).sum())}

def overlap_figure(groups):
    fig=go.Figure(go.Bar(x=list(groups),y=[len(v) for v in groups.values()],marker_color=[COLORS[k] for k in groups],customdata=list(groups),text=[str(len(v)) for v in groups.values()],textposition='outside',cliponaxis=False,hovertemplate='%{x}: %{y} plants<extra></extra>'))
    return graph_layout(fig,showlegend=False,yaxis=dict(title='Plants',rangemode='tozero'),xaxis=dict(title=''))

def evidence_figure(frame):
    stages=evidence_steps(frame); labels=['Initial matches','Reported generation','Complete attributes','No flagged anomalies']; vals=[len(f) for f in stages]
    fig=go.Figure(go.Bar(x=vals[::-1],y=labels[::-1],orientation='h',marker_color=['#147A70','#438e9d','#70a4ba','#9cbacb'],text=vals[::-1],textposition='outside',cliponaxis=False,hovertemplate='%{y}: %{x} plants<extra></extra>'))
    graph_layout(fig,showlegend=False,xaxis=dict(title='Plants',rangemode='tozero'),yaxis=dict(automargin=True)); fig.update_layout(margin=dict(l=135,r=35,t=12,b=30)); return fig


def evidence_region_figure(baseline,strict):
    levels=sorted(baseline.continent.unique())
    fig=go.Figure()
    for f,name,color in [(baseline,'Initial matches','#9cbacb'),(strict,'Strict evidence','#147A70')]:
        counts=f.groupby('continent').size().reindex(levels,fill_value=0)
        fig.add_bar(x=levels,y=counts.tolist(),name=name,marker_color=color,hovertemplate='%{x}: %{y} plants<extra></extra>')
    return graph_layout(fig,barmode='group',yaxis=dict(title='Plants',rangemode='tozero'),xaxis=dict(automargin=True))
