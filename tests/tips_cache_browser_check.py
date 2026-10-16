"""The bundled Tips example must never train for supported full-feature presets."""
import os
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(args=['--no-sandbox'])
    page=browser.new_page()
    training=[];errors=[]
    page.on('request',lambda r:training.append(r.url) if '/api/analyze' in r.url else None)
    page.on('pageerror',lambda e:errors.append(str(e)))
    def ready(target):
        page.wait_for_function("target=>!document.querySelector('#results').hidden && document.querySelector('#equation strong').textContent===target && document.querySelector('#status').textContent.includes('no retraining')",arg=target)
    def example():
        page.select_option('#problem','custom')
        page.click('#loadExample')
        ready('tip')
        assert page.locator('#problem option:checked').inner_text()=='Custom · Restaurant Tips'
        assert page.locator('#activeModel option').count()==41
    page.goto('http://127.0.0.1:8000')
    ready('Profit')
    example()
    for target in ['total_bill','size','tip']:
        page.select_option('#target',target)
        for seed in ['42','0']:
            page.select_option('#seed',seed)
            ready(target)
            assert page.evaluate('result.seed')==int(seed)
            assert page.evaluate('result.target')==target
    feature=page.locator('#features input').first
    feature.uncheck()
    assert page.locator('#results').is_hidden()
    feature.check();ready('tip')
    page.click('#loadExample');ready('tip')
    page.reload();ready('Profit');example()
    assert not training,training
    assert not errors,errors
    browser.close()
print('PASS: Tips all targets/seeds, full-feature restoration, repeat load and reload: zero training requests')
