"""Check the new default contrast and interaction-dependent emphasis."""
from pathlib import Path
import runpy
p=runpy.run_path(str(Path(__file__).with_name('offline_smoke.py')))
core,app=p['core'],p['app']
f=app.apply_filters(2017,*p['values'])
base=[v for _,v in core._fuel_color_scale('All')][::2]
assert base[:4]==[core._blend(core.FUEL_COLORS[k],.76) for k in core.PCP_FUELS]
assert base[4]=='#8494a3'
focus=[v for _,v in core._fuel_color_scale('Gas')][::2]
assert focus[1]==core.FUEL_COLORS['Gas'] and all(focus[i]=='#e3e9ed' for i in (0,2,3,4))
brush=[v for _,v in core._fuel_color_scale('All',True)][::2]
assert brush[:4]==[core.FUEL_COLORS[k] for k in core.PCP_FUELS]
assert core.make_map(f,2017).data[0].marker.opacity==.82
assert abs(core.make_map(f,2017,highlight_ids=f.gppd_idnr.iloc[:1].tolist()).data[0].marker.opacity-.328)<1e-12
print('[PASS] Default fuel contrast restored; brush, focus and map context remain differentiated')
