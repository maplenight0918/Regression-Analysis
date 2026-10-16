import os,re,json
from pathlib import Path
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];posts=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:posts.append(r.url) if '/api/analyze' in r.url else None)
 def english():
  text=page.locator('body').inner_text()
  assert not re.search(r'[\u3400-\u9fff]',text),re.findall(r'.{0,20}[\u3400-\u9fff].{0,20}',text)
  for title in page.locator('[title]').evaluate_all('xs=>xs.map(x=>x.title)'):
   assert not re.search(r'[\u3400-\u9fff]',title),title
 page.goto('http://127.0.0.1:8000',wait_until='networkidle');page.wait_for_selector('#results:visible');english()
 assert page.locator('html').get_attribute('lang')=='en'
 assert page.locator('#seed').input_value()=='0'
 assert page.locator('#methods .active').get_attribute('data-method')=='Lasso'
 page.screenshot(path='artifacts/desktop.png',full_page=True)
 page.select_option('#problem','boston');page.wait_for_function("document.querySelector('#equation strong').textContent==='medv' && !document.querySelector('#results').hidden")
 english();page.screenshot(path='artifacts/boston-desktop.png',full_page=True)
 page.select_option('#problem','custom');assert page.locator('#results').is_hidden();english()
 page.click('#loadExample')
 page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready') && document.querySelector('#equation strong').textContent==='tip'",timeout=120000)
 assert page.locator('#problem').input_value()=='custom'
 assert page.locator('#target').input_value()=='tip'
 assert '244 rows' in page.locator('#source').inner_text()
 assert page.locator('#previewTable tbody tr').count()==10
 assert page.locator('#activeModel option').count()==41 # 5 methods × 8 encoded predictors + baseline
 assert page.locator('#methods .active').get_attribute('data-method')=='ALL'
 english()
 page.select_option('#activeModel','Full OLS:8')
 assert page.locator('#predictInputs select').count()==4
 assert page.locator('#coefficients tr').count()==9
 old=page.locator('#prediction').inner_text();page.locator('#pred0').fill('40');assert page.locator('#prediction').inner_text()!=old
 page.locator('#predictInputs select').first.select_option(index=1);english()
 page.screenshot(path='artifacts/tips-example-desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/tips-example-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 # The bundled example reuses validated results when its target changes.
 page.select_option('#target','total_bill')
 page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready') && document.querySelector('#equation strong').textContent==='total_bill'",timeout=120000)
 english()
 # File-upload path also works independently of the example button.
 page.set_input_files('#file','data/tips.csv');page.wait_for_function("document.querySelector('#source').textContent.includes('Local CSV: tips.csv')")
 page.select_option('#target','tip')
 page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready') && document.querySelector('#equation strong').textContent==='tip'",timeout=120000)
 english()
 page.set_input_files('#file',{'name':'bad.csv','mimeType':'text/csv','buffer':b'a,b\n1,2'})
 page.wait_for_selector('#status.error');assert '25' in page.locator('#status').inner_text();english()
 assert page.locator('#results').is_hidden()
 page.locator('#url').fill('http://127.0.0.1/private.csv');page.click('#loadUrl');page.wait_for_function("document.querySelector('#status').textContent.includes('public internet')");english()
 assert not errors,errors
 assert len(posts)==1
 Path('artifacts/english-example-results.json').write_text(json.dumps({'passed':['English builtins, tooltips, statuses and errors','Custom CSV problem option','cached Tips example: 244 rows, 7 columns','all five methods: k1-8, 41 models','numeric and category live prediction','custom target switch','same CSV via local upload','invalid CSV and URL errors','390px mobile no overflow','no JavaScript errors'],'real_analysis_requests':len(posts)},indent=2))
 b.close()
 print('PASS: complete English UI and cached example/local Tips CSV analysis')
