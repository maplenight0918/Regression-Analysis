"""Check Pages under a project subpath, both without and with a real API."""
import os,json
from pathlib import Path
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
BASE=os.environ.get('PAGES_TEST_URL','http://127.0.0.1:8765/Regression-Analysis/')
BACKEND=os.environ.get('PAGES_TEST_API','http://127.0.0.1:8001')
Path('artifacts').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000})
    requests=[];errors=[];failed=[]
    page.on('request',lambda r:requests.append(r.url))
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:failed.append((r.url,r.status)) if r.status>=400 else None)
    def ready(target):
        page.wait_for_function('t=>!document.querySelector("#results").hidden && document.querySelector("#equation strong").textContent===t',arg=target,timeout=60000)
    page.goto(BASE);ready('Profit')
    assert page.locator('#methods .active').get_attribute('data-method')=='Lasso'
    for problem in ['startups','boston','tips']:
        if problem=='tips':page.click('#loadExample');ready('tip')
        else:
            page.select_option('#problem',problem);ready('Profit' if problem=='startups' else 'medv')
        targets=page.locator('#target option').evaluate_all('xs=>xs.map(x=>x.value)')
        for target in targets:
            page.select_option('#target',target)
            for seed in ['0','42']:
                page.select_option('#seed',seed);ready(target)
                assert 'no retraining' in page.locator('#status').inner_text()
        for method in ['Lasso','Forward SFS','RFE','ElasticNet','Exhaustive Search']:
            page.click(f'[data-method="{method}"]')
            count=page.locator('#ks button').count();assert count=={'startups':5,'boston':13,'tips':8}[problem]
            page.locator('#ks button').last.click()
            assert page.locator('#coefficients tr').count()==count+1
        page.click('[data-method="ALL"]')
        assert page.evaluate('charts[0].data.datasets.length')==6
    page.select_option('#target','tip');ready('tip');page.select_option('#activeModel','Full OLS:8')
    old=page.locator('#prediction').inner_text();page.locator('#pred0').fill('40');assert page.locator('#prediction').inner_text()!=old
    page.locator('#predictInputs select').first.select_option(index=1)
    page.locator('#features input').first.uncheck();page.click('#run');page.wait_for_selector('#status.error')
    assert 'not connected' in page.locator('#status').inner_text()
    page.locator('#features input').first.check();ready('tip')
    page.screenshot(path='artifacts/pages-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path='artifacts/pages-mobile.png',full_page=True)
    assert not any('/api/' in r for r in requests),requests
    assert not failed,failed
    assert not errors,errors
    print('PASS: Pages subpath, all 42 preset settings, all methods, prediction, mobile; zero backend requests',flush=True)
    # Inject the test API origin only in this browser. Production config stays blank.
    page.route('**/deployment-config.js',lambda route:route.fulfill(content_type='text/javascript',body='window.REGRESSION_CONFIG='+json.dumps({'staticData':True,'apiBase':BACKEND})+';'))
    page.reload();ready('Profit')
    page.locator('#features input[value="State"]').uncheck();page.click('#run')
    page.wait_for_function('!document.querySelector("#results").hidden && document.querySelector("#status").textContent.includes("Analysis ready")',timeout=120000)
    assert page.locator('#ks button').count()==3
    page.set_input_files('#file','data/tips.csv');page.wait_for_function('document.querySelector("#source").textContent.includes("Local CSV")')
    page.select_option('#target','tip');ready('tip')
    page.locator('#url').fill('https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv')
    page.click('#loadUrl');page.wait_for_function('document.querySelector("#source").textContent.includes("50_Startups.csv") && document.querySelector("#features").textContent.includes("State")')
    page.select_option('#target','Profit');ready('Profit')
    assert not errors,errors
    assert any('/api/analyze' in r for r in requests)
    browser.close()
    print('PASS: cross-origin real backend, custom feature training, CSV upload and public URL analysis')
