"""Static guarantees for the one-screen layout; run alongside the offline suite.
A rendered-browser screenshot is still required for a true end-to-end Dash test.
"""
from pathlib import Path
appdir = Path(__file__).resolve().parents[1]
css = (appdir/'assets'/'zzzz_viewport_lock.css').read_text()
app = (appdir/'app.py').read_text()
assert 'position:fixed !important' in css
assert 'overflow:hidden !important' in css
assert 'overflow-y:auto !important' in css
assert "app.run(debug=False" in app
assert 'VISUAL DECISION SUPPORT' in app
print('[PASS] Fixed viewport, independent filter scrolling, debug toolbar disabled')
