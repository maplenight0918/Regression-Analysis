import os,json
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8000',wait_until='networkidle')
 page.wait_for_selector('#results:visible');page.click('[data-method="Lasso"]')
 assert page.locator('#ks .sweet-spot').get_attribute('data-id')=='Lasso:2'
 assert page.locator('#ks .overfitting').get_attribute('data-id')=='Lasso:3'
 assert 'not a statistical test' in page.locator('#landmarkNote').inner_text()
 page.click('#ks .overfitting');assert 'Potential Overfitting Cliff' in page.locator('#metrics').inner_text()
 page.screenshot(path='artifacts/cliff-desktop.png',full_page=True)
 page.select_option('#seed','42')
 assert page.locator('#ks .sweet-spot').get_attribute('data-id')=='Lasso:3'
 assert page.locator('#ks .overfitting').get_attribute('data-id')=='Lasso:3'
 # No candidate: baseline is a single point, no neighbouring k comparison.
 page.select_option('#activeModel','Full OLS:5')
 assert 'No potential cliff meets the threshold' in page.locator('#cliffTag').inner_text()
 assert page.locator('#ks .overfitting').count()==0
 page.select_option('#seed','0');page.click('[data-method="Lasso"]');page.select_option('#activeModel','Lasso:2')
 page.screenshot(path='artifacts/desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 print('Passed: dynamic sweet spot and cliff for both seeds, baseline no-cliff, mobile layout, no JS errors')
 b.close()
