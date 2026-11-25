"""PlantScope data model and visualization functions.

Source data are historical WRI facilities, not a decommissioning decision system.
No user CSV is overwritten. A fuel-specific CO2 scenario is illustrative only.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / 'data' / 'processed' / 'power_plants_features.csv'
REGIONS_PATH = ROOT / 'data' / 'reference' / 'country_regions.csv'
FOSSIL = ('Coal', 'Gas', 'Oil', 'Petcoke')
YEARS = tuple(range(2013, 2020))
FUEL_COLORS = {'Coal':'#B45E78', 'Gas':'#347FC7', 'Oil':'#168D94', 'Petcoke':'#8464B0'}
PROVENANCE = ('reported','estimated','missing','reported_requires_review','estimate_requires_review')
PROVENANCE_LABELS = {
 'reported':'Reported · plausibility checked', 'estimated':'Model estimate',
 'missing':'Missing', 'reported_requires_review':'Reported · review required',
 'estimate_requires_review':'Estimated · review required',
}
PROVENANCE_COLORS = {
 'reported':'#147C83', 'estimated':'#357CC5', 'missing':'#9CA7B5',
 'reported_requires_review':'#B45E78', 'estimate_requires_review':'#8065B0',
}
CO2_FACTORS = {'Coal':3.6*94.6/.35,'Gas':3.6*56.1/.50,'Oil':3.6*77.4/.35,'Petcoke':3.6*97.5/.35}
PCP_FIELDS = {
 'capacity_mw':'Capacity · MW',
 'plant_age_2021_years':'Age in 2021 · yrs',
 'year_capacity_factor_pct':'Reported capacity factor · %',
 'year_generation_gwh':'Generation · GWh',
 'year_co2_mt':'Modeled CO₂ · Mt',
 'reported_gen_change_pct':'Reported generation change · %',
}
# Compact axis captions are intentionally different from verbose dropdown labels.
# Parcoords places text above each axis; long captions at the edge get clipped.
PCP_AXIS_LABELS = {
 'capacity_mw': 'Capacity (MW)',
 'plant_age_2021_years': 'Age in 2021 (yr)',
 'year_capacity_factor_pct': 'Cap. factor (%)',
 'year_generation_gwh': 'Generation (GWh)',
 'year_co2_mt': 'Modeled CO₂ (Mt)',
 'reported_gen_change_pct': 'Gen. change (%)',
}

DEFAULT_PCP_FIELDS = ['capacity_mw','plant_age_2021_years','year_co2_mt']
BASE: pd.DataFrame | None = None


def read_base(path: Path | str = DATA_PATH, regions_path: Path | str = REGIONS_PATH) -> pd.DataFrame:
    path, regions_path = Path(path), Path(regions_path)
    if not path.is_file():
        raise FileNotFoundError(f'Data missing: {path}\nCopy your existing power_plants_features.csv into data/processed/.')
    if not regions_path.is_file():
        raise FileNotFoundError(f'Region reference missing: {regions_path}\nExtract the bundled data/reference/country_regions.csv.')
    source = pd.read_csv(path, low_memory=False)
    required = {'gppd_idnr','name','country','country_long','primary_fuel','fuel_group',
                'capacity_mw','latitude','longitude','plant_age_2021_years','reported_gen_change_pct',
                'data_quality_flags','commissioning_year','source','generation_data_source'}
    required |= {f'generation_gwh_{y}' for y in YEARS}
    required |= {f'estimated_generation_gwh_{y}' for y in range(2013, 2018)}
    if missing := required.difference(source.columns):
        raise ValueError(f'Missing columns in feature-engineered file: {sorted(missing)}')
    if 'co2_scenario_tonnes_per_gwh' not in source:
        source['co2_scenario_tonnes_per_gwh'] = source.primary_fuel.map(CO2_FACTORS)
    numeric = ['capacity_mw','latitude','longitude','plant_age_2021_years','commissioning_year',
               'reported_gen_change_pct','co2_scenario_tonnes_per_gwh']
    numeric += [f'generation_gwh_{y}' for y in YEARS]
    numeric += [f'estimated_generation_gwh_{y}' for y in range(2013,2018)]
    for name in numeric:
        source[name] = pd.to_numeric(source[name], errors='coerce')
    source['gppd_idnr'] = source.gppd_idnr.astype(str)
    if source.gppd_idnr.duplicated().any():
        raise ValueError('Duplicate plant IDs; the app requires unique gppd_idnr values.')
    if not (source.capacity_mw.gt(0)&source.latitude.between(-90,90)&source.longitude.between(-180,180)).all():
        raise ValueError('Bad capacity or coordinates detected; revisit cleaning before visualization.')
    mapping = pd.read_csv(regions_path)
    if mapping.country.duplicated().any():
        raise ValueError('Duplicate country codes in region map.')
    source = source.merge(mapping[['country','continent','region']],on='country',how='left',validate='many_to_one')
    if source.continent.isna().any():
        raise ValueError('Region reference is incomplete: '+str(source.loc[source.continent.isna(),'country'].unique()))
    source['quality_flagged'] = source.data_quality_flags.fillna('').astype(str).str.strip().ne('')
    source['commissioning_known'] = source.commissioning_year.notna()
    source['generation_source_known'] = source.generation_data_source.fillna('').astype(str).str.strip().ne('')
    source['has_other_fuel'] = source[[c for c in ('other_fuel1','other_fuel2','other_fuel3') if c in source]].notna().any(axis=1)
    source['reported_years_available'] = sum(source[f'generation_gwh_{y}'].notna().astype(int) for y in YEARS)
    return source


@lru_cache(maxsize=8)
def get_year_frame(year: int) -> pd.DataFrame:
    if BASE is None:
        raise RuntimeError('Initialize core.BASE = core.read_base() before calling get_year_frame.')
    return derive_year(BASE,int(year))


def derive_year(base: pd.DataFrame, year: int) -> pd.DataFrame:
    if year not in YEARS:
        raise ValueError('Generation year must be between 2013 and 2019')
    data = base.copy()
    reported = data[f'generation_gwh_{year}']
    estimated = data[f'estimated_generation_gwh_{year}'] if year <= 2017 else pd.Series(np.nan,index=data.index)
    hours = 8784 if year % 4 == 0 else 8760
    theoretical = data.capacity_mw * hours / 1000
    valid_reported = reported.notna() & reported.between(0,theoretical)
    review_reported = reported.notna() & ~valid_reported
    valid_estimated = reported.isna() & estimated.notna() & estimated.between(0,theoretical)
    review_estimated = reported.isna() & estimated.notna() & ~estimated.between(0,theoretical)
    data['year_provenance'] = np.select(
        [review_reported,valid_reported,valid_estimated,review_estimated],
        ['reported_requires_review','reported','estimated','estimate_requires_review'],default='missing')
    data['year_generation_gwh'] = np.where(valid_reported,reported,np.where(valid_estimated,estimated,np.nan))
    data['year_capacity_factor_pct'] = np.where(valid_reported,100*reported/theoretical,np.nan)
    data['year_co2_mt'] = np.where(data.primary_fuel.isin(FOSSIL),
                                  data.year_generation_gwh*data.co2_scenario_tonnes_per_gwh/1e6,np.nan)
    data['generation_year'] = year
    return data


def filter_plants(data: pd.DataFrame, *, groups=None,fuels=None,continents=None,regions=None,countries=None,
                  search='',capacity=None,provenance=None,age_on=False,age=None,cf_on=False,cf=None,
                  co2_on=False,co2=None,trend='all',keep_unknown=False,quality='all',
                  commissioning='all',generation_source='all',min_reported_years=0,
                  generation_on=False,generation_range=None,fuel_configuration='all') -> pd.DataFrame:
    groups = ['Fossil'] if groups is None else groups
    ok = data.fuel_group.isin(groups)
    for col,items in [('primary_fuel',fuels),('continent',continents),('region',regions),
                      ('country_long',countries),('year_provenance',provenance)]:
        if items:
            ok &= data[col].isin(items)
    if search and search.strip():
        term = search.strip()
        exact_id = data.gppd_idnr.str.casefold().eq(term.casefold())
        # An autocomplete choice is a unique ID; preserve literal free-text
        # matching for direct calls to this function.
        ok &= exact_id if exact_id.any() else (data.name.fillna('').str.contains(term,case=False,regex=False)
               | data.gppd_idnr.str.contains(term,case=False,regex=False))
    if capacity is not None:
        low,high = sorted(capacity)
        ok &= data.capacity_mw.between(low,high)
    if fuel_configuration == 'single': ok &= ~data.has_other_fuel
    elif fuel_configuration == 'multi': ok &= data.has_other_fuel
    if generation_on and generation_range is not None:
        lo,hi=sorted(generation_range)
        matching=data.year_generation_gwh.between(lo,hi)
        ok &= (matching | data.year_generation_gwh.isna()) if keep_unknown else matching
    for active,col,rng in [(age_on,'plant_age_2021_years',age),
                           (cf_on,'year_capacity_factor_pct',cf),
                           (co2_on,'year_co2_mt',co2)]:
        if active and rng is not None:
            low,high = sorted(rng)
            match = data[col].between(low,high)
            ok &= match|data[col].isna() if keep_unknown else match
    values = data.reported_gen_change_pct
    if trend == 'declining': ok &= values.lt(-5)
    elif trend == 'stable': ok &= values.between(-5,5)
    elif trend == 'increasing': ok &= values.gt(5)
    elif trend == 'unavailable': ok &= values.isna()
    if quality == 'clean': ok &= ~data.quality_flagged
    elif quality == 'flagged': ok &= data.quality_flagged
    if commissioning == 'known': ok &= data.commissioning_known
    elif commissioning == 'unknown': ok &= ~data.commissioning_known
    if generation_source == 'known': ok &= data.generation_source_known
    elif generation_source == 'unknown': ok &= ~data.generation_source_known
    if min_reported_years:
        ok &= data.reported_years_available.ge(int(min_reported_years))
    return data.loc[ok]


def pcp_cohort(filtered: pd.DataFrame, map_ids: list[str] | None, dimensions: list[str]):
    cohort = filtered if not map_ids else filtered[filtered.gppd_idnr.isin(map_ids)]
    dims = [c for c in dimensions if c in PCP_FIELDS]
    eligible = cohort.dropna(subset=dims) if len(dims)>=2 else cohort.iloc[:0]
    return eligible,{'cohort':len(cohort),'eligible':len(eligible),'missing':len(cohort)-len(eligible)}


# Field-specific log1p transforms preserve zero and retain every extreme.
# The signed generation-change transform also preserves negative changes.
# Every brush and export is converted back to the original numerical units.
PCP_LOG_PIVOTS = {'capacity_mw': 1., 'year_generation_gwh': 1., 'year_co2_mt': .01}
PCP_SIGNED_PIVOTS = {'reported_gen_change_pct': 100.}
PCP_LOG_FIELDS = frozenset(PCP_LOG_PIVOTS)
PCP_FUELS = ('Coal','Gas','Oil','Petcoke')


def pcp_to_display(field: str, x):
    values = np.asarray(x, dtype=float)
    if field in PCP_LOG_PIVOTS:
        return np.log1p(np.maximum(0., values)/PCP_LOG_PIVOTS[field])/np.log(10.)
    if field in PCP_SIGNED_PIVOTS:
        return np.sign(values)*np.log1p(np.abs(values)/PCP_SIGNED_PIVOTS[field])/np.log(10.)
    return values


def pcp_from_display(field: str, x):
    values = np.asarray(x, dtype=float)
    if field in PCP_LOG_PIVOTS:
        return PCP_LOG_PIVOTS[field]*np.maximum(0., np.expm1(values*np.log(10.)))
    if field in PCP_SIGNED_PIVOTS:
        return np.sign(values)*PCP_SIGNED_PIVOTS[field]*np.expm1(np.abs(values)*np.log(10.))
    return values


def _sample_by_capacity_bins(frame: pd.DataFrame, limit: int, seed: int):
    """Reproducible, capacity-stratified visual sample (not the brush cohort)."""
    if len(frame) <= limit: return frame
    # Equal-width ranks approximate capacity quantiles and retain low/high plants.
    bins = min(8, limit, len(frame))
    ranks = frame.capacity_mw.rank(method='first')
    labels = pd.qcut(ranks, q=bins, labels=False, duplicates='drop')
    parts = []
    for i in range(bins):
        group = frame.loc[labels == i]
        quota = limit // bins + (1 if i < limit % bins else 0)
        if len(group):
            parts.append(group.sample(n=min(quota, len(group)), random_state=seed+i))
    selected = pd.concat(parts) if parts else frame.iloc[:0]
    if len(selected) < limit:
        remainder = frame.loc[~frame.index.isin(selected.index)]
        extra = remainder.sample(n=min(limit-len(selected),len(remainder)), random_state=seed+53)
        selected = pd.concat([selected,extra])
    return selected


def pcp_plot_sample(eligible: pd.DataFrame, max_lines: int = 100,
                    focus_fuel: str = 'All') -> pd.DataFrame:
    """Display-only stratified sample; full-cohort brushing is unaffected.

    When a fuel is focused, reserve roughly 70% of visual lines for that fuel;
    all other fuels remain faint context. This NEVER filters the cohort.
    """
    if eligible.empty or max_lines <= 0: return eligible.iloc[:0]
    if len(eligible) <= max_lines: return eligible.sort_values('gppd_idnr')
    if focus_fuel in PCP_FUELS and eligible.primary_fuel.eq(focus_fuel).any():
        focused = eligible.loc[eligible.primary_fuel.eq(focus_fuel)]
        context = eligible.loc[~eligible.primary_fuel.eq(focus_fuel)]
        n_focus = min(len(focused), max(1,round(max_lines * 0.7)))
        a = _sample_by_capacity_bins(focused, n_focus, 2026)
        b = _sample_by_capacity_bins(context, max_lines-len(a), 2041)
        if len(a)+len(b) < max_lines:
            leftover = eligible.loc[~eligible.index.isin(pd.concat([a,b]).index)]
            c = _sample_by_capacity_bins(leftover, max_lines-len(a)-len(b), 2061)
            return pd.concat([a,b,c]).sort_values('gppd_idnr')
        return pd.concat([a,b]).sort_values('gppd_idnr')
    # Approximate real fuel proportions while guaranteeing visible representation
    # for small groups where possible. Then stratify capacity within each fuel.
    shares = eligible.primary_fuel.fillna('Other').value_counts(sort=False)
    quotas = {f: max(1,round(max_lines * n/len(eligible))) for f,n in shares.items()}
    while sum(quotas.values()) > max_lines:
        k=max((k for k in quotas if quotas[k]>1),key=lambda k:quotas[k],default=None)
        if k is None:break
        quotas[k]-=1
    while sum(quotas.values()) < max_lines:
        k=max(shares.index,key=lambda f: shares[f]-quotas[f])
        quotas[k]+=1
    blocks=[]
    for index,(fuel,quota) in enumerate(quotas.items()):
        block=eligible.loc[eligible.primary_fuel.fillna('Other').eq(fuel)]
        blocks.append(_sample_by_capacity_bins(block,min(quota,len(block)),2026+index*17))
    result=pd.concat(blocks)
    if len(result)<max_lines:
        rest=eligible.loc[~eligible.index.isin(result.index)]
        result=pd.concat([result,_sample_by_capacity_bins(rest,max_lines-len(result),2099)])
    return result.sort_values('gppd_idnr')


def prioritize_pcp_sample(eligible, max_lines, focus_fuel='All', constraints=None):
    """Reserve 80% of the display budget for brush matches; keep faint context.
    The original full eligible dataframe remains the authoritative brush cohort.
    """
    if not constraints or eligible.empty:
        return pcp_plot_sample(eligible,max_lines,focus_fuel)
    ids=set(brushed_ids(eligible,constraints))
    matches=eligible.loc[eligible.gppd_idnr.isin(ids)]
    context=eligible.loc[~eligible.gppd_idnr.isin(ids)]
    n=min(len(matches),max(1,round(max_lines*.8))) if len(context) else max_lines
    chosen=pcp_plot_sample(matches,n,focus_fuel)
    others=pcp_plot_sample(context,max_lines-len(chosen),focus_fuel)
    remaining=max_lines-len(chosen)-len(others)
    if remaining>0:
        extra=matches.loc[~matches.index.isin(chosen.index)]
        chosen=pd.concat([chosen,pcp_plot_sample(extra,remaining,focus_fuel)])
    return pd.concat([others,chosen])


def _tick_label(x):
    if abs(x)>=1e6: return f'{x/1e6:.3g}M'
    if abs(x)>=1000: return f'{x/1000:.3g}k'
    return f'{x:.3g}'


def _pcp_ticks(field: str, low: float, high: float):
    """At most five labels, well separated in DISPLAY space on a short chart.
    No separately rendered min/max labels compete with these labels.
    """
    lo,hi=map(float,pcp_to_display(field,[low,high])); span=hi-lo
    if not np.isfinite(span) or span<=0: return [lo],[_tick_label(low)]
    if field in PCP_LOG_FIELDS or field in PCP_SIGNED_PIVOTS:
        positives=[m*10.**power for power in range(-6,10) for m in (1,2,5)]
        candidates=sorted(set([0.]+positives+([-x for x in positives] if field in PCP_SIGNED_PIVOTS else [])))
    else:
        step0=(high-low)/8
        magnitude=10.**np.floor(np.log10(step0))
        step=next(m*magnitude for m in (1,2,2.5,5,10) if m*magnitude>=step0)
        candidates=list(np.arange(np.ceil(low/step)*step,high+step*.000001,step))
    candidates=[x for x in candidates if low-1e-10<=x<=high+1e-10]
    # Display both true endpoints plus up to three nicely spaced interior ticks.
    selected=[low,high]
    for target in np.linspace(lo,hi,5)[1:-1]:
        available=[x for x in candidates if all(abs(float(pcp_to_display(field,x))-float(pcp_to_display(field,y)))>=span*.18 for y in selected)]
        if available:
            best=min(available,key=lambda x:abs(float(pcp_to_display(field,x))-target))
            if abs(float(pcp_to_display(field,best))-target)<=span*.17: selected.append(best)
    selected=sorted(selected)
    vals=[float(pcp_to_display(field,x)) for x in selected]
    texts=[_tick_label(x) for x in selected]
    if len(set(texts))<len(texts): texts=[f'{x:.7g}' for x in selected]
    return vals,texts


def _blend(hex_color, strength):
    rgb=[int(hex_color[i:i+2],16) for i in (1,3,5)]
    return '#'+''.join(f'{round(255+(c-255)*strength):02x}' for c in rgb)


def _fuel_color_scale(focus_fuel: str, brushed=False):
    # WebGL parcoords may discard RGBA alpha. Use actual light RGB colors,
    # not alpha alone, to guarantee subdued context on a white background.
    colors=[]
    for fuel in PCP_FUELS:
        if focus_fuel not in ('All',fuel): colors.append('#e3e9ed')
        elif focus_fuel==fuel or brushed: colors.append(FUEL_COLORS[fuel])
        else: colors.append(_blend(FUEL_COLORS[fuel],.76))
    colors.append('#8494a3' if brushed or focus_fuel=='All' else '#e3e9ed')
    scale=[]
    for i,c in enumerate(colors):
        scale.extend([[0. if i==0 else (i-.5)/4,c],[1. if i==4 else (i+.5)/4,c]])
    return scale


def make_pcp(plotted: pd.DataFrame, dimensions: list[str], year: int,
             constraints=None, eligible=None, focus_fuel='All'):
    fig = go.Figure()
    if len(dimensions)<2 or plotted.empty:
        # Draw only an axis skeleton. No dummy observations, fabricated bounds,
        # or centered messages in place of the visualization.
        labels = [PCP_AXIS_LABELS[d] for d in dimensions if d in PCP_AXIS_LABELS]
        fig.add_trace(go.Scatter(x=[], y=[], mode='markers', showlegend=False, hoverinfo='skip'))
        for i, label in enumerate(labels):
            fig.add_shape(type='line', x0=i, x1=i, y0=.06, y1=.91,
                          line=dict(color='#A9B8C4',width=1))
            fig.add_annotation(x=i,y=.96,text=label,showarrow=False,
                               font=dict(size=13,color='#18374a'))
        return fig.update_layout(autosize=True,margin=dict(l=24,r=28,t=24,b=18),
            paper_bgcolor='#fff',plot_bgcolor='#fff',dragmode=False,
            xaxis=dict(visible=False,fixedrange=True,range=[-.35,max(1,len(labels)-1)+.35]),
            yaxis=dict(visible=False,fixedrange=True,range=[0,1]))
    dims=[]
    for field in dimensions:
        values=plotted[field].astype(float)
        bounds_values=eligible[field].dropna() if eligible is not None else values
        raw_low,raw_high=float(bounds_values.min()),float(bounds_values.max())
        if raw_low==raw_high:
            pad=max(abs(raw_low)*0.04,1)
            raw_low-=pad;raw_high+=pad
        # Clamp logarithmic fields to their actual nonnegative domain.
        if field in PCP_LOG_FIELDS: raw_low=max(0,raw_low)
        lower,upper=float(pcp_to_display(field,raw_low)),float(pcp_to_display(field,raw_high))
        if lower==upper: upper+=0.01
        label=PCP_AXIS_LABELS[field]
        item=dict(name=field,label=label,values=pcp_to_display(field,values),range=[lower,upper])
        ticks,texts=_pcp_ticks(field,raw_low,raw_high)
        if ticks:
            item['tickvals']=ticks;item['ticktext']=texts
        if constraints and field in constraints:
            transformed=[[float(pcp_to_display(field,lo)),float(pcp_to_display(field,hi))]
                         for lo,hi in constraints[field]]
            item['constraintrange']=transformed[0] if len(transformed)==1 else transformed
        dims.append(item)
    numeric_colors=plotted.primary_fuel.apply(lambda x: PCP_FUELS.index(x) if x in PCP_FUELS else 4).to_numpy()
    fig.add_trace(go.Parcoords(
        dimensions=dims,
        line=dict(color=numeric_colors,cmin=0,cmax=4,
                  colorscale=_fuel_color_scale(focus_fuel,bool(constraints)),showscale=False),
        unselected=dict(line=dict(color='#e1e7eb',opacity=.22)),
        labelfont=dict(size=14,color='#18374a'),tickfont=dict(size=12,color='#395568'),
        rangefont=dict(size=10,color='rgba(255,255,255,0)'),domain=dict(x=[.09,.86],y=[.06,.96]),
    ))
    fig.update_layout(autosize=True,margin=dict(l=14,r=16,t=25,b=8),paper_bgcolor='#fff',
                      plot_bgcolor='#fff')
    return fig


def normalize_ranges(value: Any) -> list[list[float]]:
    if value is None: return []
    if isinstance(value,(tuple,list)) and len(value)==2 and all(isinstance(x,(int,float)) for x in value):
        return [[min(float(value[0]),float(value[1])),max(float(value[0]),float(value[1]))]]
    if isinstance(value,(tuple,list)):
        result=[]
        for item in value: result+=normalize_ranges(item)
        return result
    return []


def extract_restyle_constraints(restyle: Any,previous: dict,dimensions: list[str],
                                 display_scaled: bool = False):
    out=dict(previous or {})
    if not isinstance(restyle,list) or not restyle or not isinstance(restyle[0],dict):
        return out
    for key,val in restyle[0].items():
        m=re.fullmatch(r'dimensions\[(\d+)\]\.constraintrange',key)
        if m is None: continue
        idx=int(m.group(1))
        if idx >= len(dimensions): continue
        if isinstance(val,list) and len(val)==1 and isinstance(val[0],(list,tuple)):
            val=val[0]
        normalized=normalize_ranges(val)
        if normalized and display_scaled:
            # Plotly supplies the *display-space* interval; store original units
            # so every record in eligible can be evaluated correctly.
            field=dimensions[idx]
            normalized=[[float(pcp_from_display(field,lo)),float(pcp_from_display(field,hi))]
                        for lo,hi in normalized]
        if normalized: out[dimensions[idx]]=normalized
        else: out.pop(dimensions[idx],None)
    return out


def brushed_ids(eligible: pd.DataFrame, constraints: dict) -> list[str]:
    if eligible.empty or not constraints: return []
    mask=pd.Series(True,index=eligible.index)
    for field,ranges in constraints.items():
        if field not in eligible: continue
        match=pd.Series(False,index=eligible.index)
        for low,high in ranges:
            match |= eligible[field].between(low,high)
        mask &= match
    return eligible.loc[mask,'gppd_idnr'].tolist()


def marker_sizes(data,size_mode,zoom=1.22):
    # Restore the V5.1 marker diameter curve: tiny overview markers were
    # difficult to distinguish even after opacity was raised in V6.1.
    factor = .72 if zoom < 2 else .95 if zoom < 4 else 1.35
    if size_mode == 'uniform': return 6.0 * factor
    return np.clip(2.8 + 1.05*np.log1p(data.capacity_mw.to_numpy()), 3.3, 11.5) * factor


def overlay_marker_size(zoom):
    return 9.0 if zoom<2 else 11.0 if zoom<4 else 16.0


def make_map(data,year,color_mode='fuel',size_mode='capacity',highlight_ids=None,focus_id=None,zoom_for_markers=1.22, cluster=False, map_selected_ids=None, scenario_active=False):
    fig=go.Figure()
    context_active=bool(map_selected_ids or highlight_ids or scenario_active)
    opacity=(.82 if zoom_for_markers<2 else .90 if zoom_for_markers<4 else .96) * (.40 if context_active else 1.)
    overlay_size=overlay_marker_size(zoom_for_markers)
    def add(part,name,marker,showlegend=True):
        payload=part[['gppd_idnr','country_long','primary_fuel','capacity_mw','year_provenance']].fillna('—').to_numpy()
        fig.add_trace(go.Scattermap(
            lat=part.latitude,lon=part.longitude,mode='markers',name=name,
            text=part.name.fillna('Unnamed'),customdata=payload,marker=marker,showlegend=showlegend,
            cluster=dict(enabled=True,maxzoom=4,size=18,opacity=.86) if cluster and name not in ('Focused plant','PCP matches','Selected on map') else None,
            selected=dict(marker=dict(opacity=1)),unselected=dict(marker=dict(opacity=.17)),
            hovertemplate=('<b>%{text}</b><br>%{customdata[1]} · %{customdata[2]}'
                           '<br>Capacity: %{customdata[3]:,.1f} MW'
                           f'<br>{year} data: '+'%{customdata[4]}<extra></extra>')
        ))
    if color_mode=='fuel':
        for category in FOSSIL:
            subset=data.loc[data.primary_fuel.eq(category)]
            if not subset.empty:
                add(subset,category,dict(size=marker_sizes(subset,size_mode,zoom_for_markers),color=FUEL_COLORS[category],opacity=opacity))
        for category,color in [('Non-fossil','#71859B'),('Mixed / unspecified','#B2A3C1')]:
            subset=data.loc[data.fuel_group.eq(category)]
            if not subset.empty:
                add(subset,category,dict(size=marker_sizes(subset,size_mode,zoom_for_markers),color=color,opacity=opacity))
    elif color_mode=='provenance':
        for status,label in PROVENANCE_LABELS.items():
            subset=data.loc[data.year_provenance.eq(status)]
            if not subset.empty:
                add(subset,label,dict(size=marker_sizes(subset,size_mode,zoom_for_markers),color=PROVENANCE_COLORS[status],opacity=opacity))
    else:
        available=data.loc[data.year_co2_mt.notna()]
        if not available.empty:
            # Year-scaled globally instead of shifting when the country filter changes.
            all_year=get_year_frame(int(year)).year_co2_mt
            top=float(all_year.quantile(.98)) if all_year.notna().any() else 1
            add(available,'CO₂ modeled',dict(size=marker_sizes(available,size_mode,zoom_for_markers),color=available.year_co2_mt.to_numpy(),
                colorscale='Blues',cmin=0,cmax=max(top,.001),showscale=True,
                colorbar=dict(title='Mt CO₂',thickness=10,len=.75,y=.5),opacity=opacity),showlegend=False)
        unavailable=data.loc[data.year_co2_mt.isna()]
        if not unavailable.empty:
            add(unavailable,'CO₂ unavailable',dict(size=marker_sizes(unavailable,size_mode,zoom_for_markers),color='#AAB4C0',opacity=opacity))
    if map_selected_ids:
        picked=data.loc[data.gppd_idnr.isin(map_selected_ids)]
        if not picked.empty:
            add(picked,'Selected on map',dict(size=overlay_size,color='#0B5065',opacity=.88))
    if highlight_ids:
        matched=data.loc[data.gppd_idnr.isin(highlight_ids)]
        if not matched.empty:
            # All matches are mapped: sampling would distort geographical concentration.
            add(matched,'PCP matches',dict(size=overlay_size,color='#12394C',opacity=.92))
    if focus_id:
        single=data.loc[data.gppd_idnr.eq(str(focus_id))]
        if not single.empty:
            add(single,'Focused plant',dict(size=15,color='#E4C053',opacity=1))
    fig.update_layout(autosize=True,
          map=dict(style='carto-positron',center=dict(lat=19,lon=0),zoom=.20),
          margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='#fff',dragmode='lasso',
          uirevision='keep-map-camera',legend=dict(orientation='h',x=0,y=1.02,yanchor='bottom',
          bgcolor='rgba(255,255,255,.93)',font=dict(size=12,color='#536778')))
    if data.empty:
        # A null coordinate initializes the map subplot without displaying a marker.
        fig.add_trace(go.Scattermap(lat=[None],lon=[None],mode='markers',
                                    showlegend=False,hoverinfo='skip'))
    return fig


def plant_overview(plant: pd.Series, year:int) -> dict:
    fields=['gppd_idnr','name','country_long','region','primary_fuel','capacity_mw','plant_age_2021_years',
            'year_generation_gwh','year_capacity_factor_pct','year_co2_mt','year_provenance',
            'quality_flagged','commissioning_known','generation_source_known','reported_years_available']
    return {field:plant.get(field) for field in fields}


def frame_to_export(df: pd.DataFrame, year:int) -> pd.DataFrame:
    fields=['gppd_idnr','name','country_long','continent','region','primary_fuel','capacity_mw',
            'plant_age_2021_years','year_generation_gwh','year_capacity_factor_pct','year_co2_mt',
            'year_provenance','reported_gen_change_pct','quality_flagged','data_quality_flags','source','generation_data_source']
    keep=[f for f in fields if f in df]
    export=df[keep].copy()
    export.rename(columns={'year_generation_gwh':f'generation_{year}_gwh',
                           'year_capacity_factor_pct':f'reported_capacity_factor_{year}_pct',
                           'year_co2_mt':f'co2_{year}_mt_modeled_scenario',
                           'year_provenance':f'generation_provenance_{year}'},inplace=True)
    return export
