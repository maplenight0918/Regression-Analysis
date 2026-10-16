import os,json,time
from pathlib import Path
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});posts=[];gets=[];errors=[]
 page.on('request',lambda r:posts.append(r.url) if '/api/analyze' in r.url else gets.append(r.url) if '/presets?' in r.url else None)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8000',wait_until='networkidle');page.wait_for_selector('#results:visible')
 assert page.locator('#problem option').all_text_contents()==['50 Startups','Boston Housing','Custom CSV']
 def ready(target,count):
  try:page.wait_for_function("t=>document.querySelector('#results').hidden===false && document.querySelector('#equation strong').textContent===t",arg=target,timeout=15000)
  except Exception:
   print('FAILED TARGET',target,'actual target',page.locator('#target').input_value(),'status',page.locator('#status').inner_text(),'JS errors',errors,flush=True);raise
  assert 'no retraining' in page.locator('#status').inner_text()
  assert target in page.locator('#description').inner_text() or target=='medv'
  ks=page.locator('#ks button').evaluate_all("bs=>bs.map(b=>Number(b.dataset.id.split(':').pop()))")
  assert ks==list(range(1,count+1)),ks
 for problem in ['startups','boston']:
  page.select_option('#problem',problem)
  page.wait_for_function("name=>document.querySelector('#source').textContent.includes(name)",arg='50_Startups' if problem=='startups' else 'BostonHousing')
  targets=page.locator('#target option').evaluate_all('xs=>xs.map(x=>x.value)')
  for target in targets:
   page.select_option('#target',target)
   for seed in ['0','42']:
    page.select_option('#seed',seed);ready(target,5 if problem=='startups' else 13)
   assert page.locator('#features input').evaluate_all("(xs,t)=>xs.every(x=>x.value!==t)",target)
  # Cached target should not make another target endpoint request.
  before=len(gets);page.select_option('#target',targets[0]);ready(targets[0],5 if problem=='startups' else 13)
  assert len(gets)==before
 assert not posts,posts
 # Reproduce candidate changes + Compare All, which previously mutated k order.
 page.select_option('#problem','startups');ready('Profit',5)
 page.locator('#features input[value="State"]').uncheck()
 assert page.locator('#results').is_hidden()
 assert page.locator('#ks button').all_text_contents()==['k = 1','k = 2','k = 3']
 page.locator('#features input[value="State"]').check();ready('Profit',5)
 assert not posts
 page.locator('#features input[value="State"]').uncheck();page.click('[data-method="ALL"]');page.click('#run')
 page.wait_for_function("document.querySelector('#status').textContent.includes('Analysis ready')",timeout=60000)
 page.click('[data-method="Lasso"]')
 assert page.locator('#ks button').evaluate_all("bs=>bs.map(b=>Number(b.dataset.id.split(':').pop()))")==[1,2,3]
 assert len(posts)==1
 page.locator('#features input[value="State"]').check();ready('Profit',5)
 page.select_option('#target','R&D Spend');ready('R&D Spend',5)
 page.screenshot(path='artifacts/target-switch-desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='artifacts/target-switch-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 Path('artifacts/target-switch-results.json').write_text(json.dumps({'passed':['short problem names','all 18 numeric targets and both seeds','target excluded from predictors','no training during builtin target switches','repeat target reuses browser cache','candidate changes preserve sorted disabled k','restore all features reuses cache','Compare All training does not reorder k','mobile no overflow','no JS errors'],'builtin_training_requests':0,'custom_feature_training_requests':len(posts)},indent=2))
 b.close()
 print('PASS: 36 target/seed combinations, cached restoration, candidate k order, mobile')
