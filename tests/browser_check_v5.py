"""Optional actual browser smoke check. Start app.py first; requires Playwright/Chromium."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width,height in ((1536,830),(1366,700),(1920,950)):
        page=browser.new_page(viewport={'width':width,'height':height})
        page.goto('http://127.0.0.1:8050/',wait_until='domcontentloaded')
        page.locator('#kpi-plants').filter(has_text='8,660').wait_for(timeout=60000)
        page.locator('#plant-map .js-plotly-plot').wait_for(timeout=60000)
        page.locator('#pcp-chart .js-plotly-plot').wait_for(timeout=60000)
        page.wait_for_function("() => {const m=document.querySelector('#plant-map .js-plotly-plot')?._fullLayout?.map?._subplot?.map; return m && m.getRenderWorldCopies()===false;}",timeout=60000)
        m=page.locator('#plant-map').bounding_box(); q=page.locator('#pcp-chart').bounding_box()
        assert m and q and m['height']>120 and q['height']>120
        assert m['y']+m['height'] <= q['y']+1
        assert q['y']+q['height'] <= height+1
        assert page.evaluate('document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('#workspace-tab').count()==0
        for key in ('regional','scatter','inspect','shortlist'):
            page.locator('#open-'+key).click()
            page.locator('#'+key+'-drawer').wait_for(state='visible')
            assert page.locator('#plant-map').is_visible() and page.locator('#pcp-chart').is_visible()
            page.locator('#close-'+key).click()
            page.locator('#'+key+'-drawer').wait_for(state='hidden')
        page.locator('summary').filter(has_text='Scenario screening').click()
        page.locator('#scenario-mini-summary').get_by_text('1,587',exact=True).wait_for(timeout=60000)
        page.locator('.scenario-criteria summary').filter(has_text='Emissions priority').click()
        page.locator('#scenario-a-co2').fill('5')
        # No Enter, blur or Apply click: the result must update during editing.
        page.locator('#scenario-mini-summary').get_by_text('687',exact=True).wait_for(timeout=60000)
        page.locator('#selection-legend').get_by_text('Scenario · A matches: 687',exact=True).wait_for(timeout=60000)
        page.locator('#open-scenario').click()
        page.locator('#scenario-drawer').wait_for(state='visible')
        page.locator('#close-scenario').click()
        page.locator('#scenario-drawer').wait_for(state='hidden')
        print(f'[PASS] Actual layout and contextual drawer controls at {width}×{height}')
        page.close()
    browser.close()
