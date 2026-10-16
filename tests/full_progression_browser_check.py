import os,json
from pathlib import Path
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});requests=[];errors=[]
 page.on('request',lambda r:requests.append(r.url) if '/api/analyze' in r.url else None)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8000',wait_until='networkidle');page.wait_for_selector('#results:visible')
 assert page.locator('#maxk').count()==0
 assert page.locator('#ks button').count()==5
 assert page.locator('#seed').input_value()=='0'
 page.select_option('#problem','boston');page.wait_for_function("document.querySelectorAll('#ks button').length===13")
 for seed in ('0','42'):
  page.select_option('#seed',seed)
  for method in ['Lasso','Forward SFS','RFE','ElasticNet','Exhaustive Search']:
   page.click(f'[data-method="{method}"]');assert page.locator('#ks button').count()==13
   page.select_option('#activeModel',f'{method}:13')
   assert page.locator('#coefficients tr').count()==14
   assert page.locator('#chips .feature-chip').count()==13
   assert f'{method} / k=13' in page.locator('#modelCaption').inner_text()
   assert page.evaluate("Chart.getChart(document.getElementById('rmseChart')).data.datasets[0].data.length") == 13
 page.click('[data-method="ALL"]')
 assert page.evaluate("Chart.getChart(document.getElementById('rmseChart')).data.datasets.length")==6
 page.select_option('#seed','0');page.click('[data-method="Lasso"]')
 page.screenshot(path='artifacts/boston-desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/boston-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not requests,requests
 assert not errors,errors
 Path('artifacts/full-progression-results.json').write_text(json.dumps({'passed':['no search maximum control','startups k1-5','Boston all five methods k1-13 for both seeds','k13 coefficients and chips synchronized','all-method charts','mobile no overflow','no training on builtin navigation','no JS errors']},indent=2))
 b.close()
 print('PASS: complete 1–13 progressions, both seeds and all methods, no training, mobile layout')
