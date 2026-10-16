import os
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000})
 page.goto('http://127.0.0.1:8000',wait_until='networkidle')
 page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready')",timeout=180000)
 page.evaluate('document.fonts.ready');page.screenshot(path='artifacts/desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 # Verify category dropdown when the full encoded model is selected.
 page.select_option('#activeModel','Full OLS:5')
 assert page.locator('#predictInputs select').count()==1
 b.close()
