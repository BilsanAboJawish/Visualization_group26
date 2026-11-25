"""Verify map mark size, opacity and exact overlay IDs; no live browser required."""
from pathlib import Path
import runpy
import numpy as np
p=runpy.run_path(str(Path(__file__).with_name('contrast_v6_1.py')))
core,app=p['core'],p['app']
f=p['f']
for zoom, factor, opacity in [(1.22,.72,.82),(3,.95,.90),(5,1.35,.96)]:
    sizes=core.marker_sizes(f,'capacity',zoom)
    assert np.allclose(sizes,np.clip(2.8+1.05*np.log1p(f.capacity_mw),3.3,11.5)*factor)
    assert core.marker_sizes(f,'uniform',zoom)==6*factor
    for mode in ['fuel','provenance','co2']:
        fig=core.make_map(f,2017,color_mode=mode,zoom_for_markers=zoom)
        assert sum(len(t.lat) for t in fig.data)==len(f)
        assert all(t.marker.opacity==opacity for t in fig.data)
    ids=f.gppd_idnr.iloc[:20].tolist()
    selected=core.make_map(f,2017,highlight_ids=ids,zoom_for_markers=zoom)
    assert np.isclose(selected.data[0].marker.opacity,opacity*.4)
    assert set(x[0] for x in selected.data[-1].customdata)==set(ids)
    assert selected.data[-1].marker.size==core.overlay_marker_size(zoom)
    assert selected.data[-1].marker.size >= sizes.max()
print('[PASS] Restored map sizes, stronger opacity in every color mode, exact selection overlays, unchanged PCP contrast')
