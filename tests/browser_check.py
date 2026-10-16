import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('https://huanchen1107.github.io/AIoT-DIC2-MultipleLR/',wait_until='networkidle')
    page.screenshot(path='artifacts/reference-desktop.png',full_page=True)
    page.goto('http://127.0.0.1:8000',wait_until='networkidle')
    page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready')",timeout=240000)
    page.evaluate('document.fonts.ready');page.screenshot(path='artifacts/desktop.png',full_page=True)
    assert page.locator('#coefficients tr').count()>=2
    page.select_option('#activeModel','Lasso:1');one=page.locator('#equation').inner_text()
    page.select_option('#activeModel','Lasso:3');assert page.locator('#equation').inner_text()!=one
    assert page.locator('#coefficients tr').count()==4
    old=page.locator('#prediction').inner_text();page.locator('#pred0').fill('0');assert old!=page.locator('#prediction').inner_text()
    page.click('[data-method="RFE"]');assert 'RFE' in page.locator('#modelCaption').inner_text()
    page.click('[data-method="ALL"]')
    page.select_option('#problem','boston');page.wait_for_function("document.querySelector('#source').textContent.includes('506 rows')")
    page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready') || document.querySelector('#status').classList.contains('error')",timeout=300000)
    assert not page.locator('#status').evaluate("el=>el.classList.contains('error')"),page.locator('#status').inner_text()
    page.screenshot(path='artifacts/boston-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/mobile.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.locator('#url').fill('https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv');page.click('#loadUrl');page.wait_for_function("document.querySelector('#source').textContent.includes('50 rows')")
    page.set_input_files('#file',{'name':'custom.csv','mimeType':'text/csv','buffer':('area,kind,price\n'+'\n'.join(f'{i},'+('A' if i%2 else 'B')+f',{i*3+i%3}' for i in range(1,61))).encode()})
    page.wait_for_function("document.querySelector('#source').textContent.includes('custom.csv')")
    page.click('#run');page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready')",timeout=120000)
    assert 'price' in page.locator('#equation').inner_text()
    page.set_input_files('#file',{'name':'bad.csv','mimeType':'text/csv','buffer':b'a,b\n1,2'})
    page.wait_for_selector('#status.error');assert page.locator('#results').is_hidden()
    assert not errors,errors
    Path('artifacts/browser-results.json').write_text(json.dumps({'passed':['reference screenshot','startups all five methods','model and k synchronization','live prediction','Boston all five methods k1-13','mobile 390px no overflow','remote CSV URL','custom local CSV','invalid CSV error','no JavaScript errors']},ensure_ascii=False,indent=2))
    b.close()
