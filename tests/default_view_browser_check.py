import os
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});requests=[]
 page.on('request',lambda r:requests.append(r.url) if '/api/analyze' in r.url else None)
 page.goto('http://127.0.0.1:8000',wait_until='networkidle');page.wait_for_selector('#results:visible')
 assert page.locator('#methods .active').get_attribute('data-method')=='Lasso'
 assert page.locator('#activeModel').input_value()=='Lasso:2'
 assert page.locator('#seed').input_value()=='0'
 assert 'R&D Spend' in page.locator('#chips').inner_text()
 assert 'Marketing Spend' in page.locator('#chips').inner_text()
 assert page.locator('#description').inner_text().startswith('50 Startups: Predict')
 page.screenshot(path='artifacts/desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.select_option('#problem','boston')
 page.wait_for_function("document.querySelector('#description').textContent.startsWith('Boston Housing: Predict') && document.querySelector('#equation').textContent.includes('medv')")
 assert page.locator('#activeModel').input_value().startswith('Lasso:')
 assert not requests
 b.close()
 print('PASS: default L1, seed 0, k=2, English descriptions, both datasets, mobile, no training requests')
