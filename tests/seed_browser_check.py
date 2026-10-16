import os,json
from pathlib import Path
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=b.new_page(viewport={'width':1440,'height':1000});errors=[];analysis_requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:analysis_requests.append(r.url) if '/api/analyze' in r.url else None)
    def ready(seed):
        page.wait_for_function("seed=>document.querySelector('#status').textContent.includes('Analysis ready · Seed '+seed)",arg=seed,timeout=15000)
        assert page.locator('#results').is_visible()
        assert 'no retraining' in page.locator('#status').inner_text()
        assert f'Seed {seed}' in page.locator('#modelCaption').inner_text()
    page.goto('http://127.0.0.1:8000',wait_until='networkidle');ready(0)
    assert page.locator('#seed').input_value()=='0'
    page.select_option('#activeModel','Lasso:2')
    assert '8,198.8' in page.locator('#metrics').inner_text()
    page.reload(wait_until='networkidle');ready(0)
    page.select_option('#seed','42');ready(42)
    page.select_option('#activeModel','Lasso:2')
    assert '8,206.33' in page.locator('#metrics').inner_text()
    page.select_option('#seed','0');page.select_option('#seed','42');page.select_option('#seed','0');ready(0)
    page.screenshot(path='artifacts/desktop.png',full_page=True)
    page.screenshot(path='artifacts/seed0-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/mobile.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.select_option('#problem','boston');ready(0)
    assert 'medv' in page.locator('#equation').inner_text()
    page.select_option('#seed','42');ready(42)
    page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path='artifacts/boston-desktop.png',full_page=True)
    assert not analysis_requests,analysis_requests
    # Changed configuration cannot silently reuse the default preset.
    page.locator('#features input').first.uncheck()
    assert page.locator('#results').is_hidden()
    assert 'Run Analysis' in page.locator('#status').inner_text()
    page.click('[data-method="Lasso"]');page.click('#run')
    page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready')",timeout=60000)
    assert len(analysis_requests)==1
    assert 'no retraining' not in page.locator('#status').inner_text()
    assert not errors,errors
    Path('artifacts/seed-browser-results.json').write_text(json.dumps({'passed':['default seed 0 ready without training','reload without training','both seeds and both builtins without training','rapid seed switches','modified configuration runs actual analysis','mobile no overflow','no JavaScript errors'],'analysis_requests_during_builtin_navigation':0},ensure_ascii=False,indent=2))
    b.close()
