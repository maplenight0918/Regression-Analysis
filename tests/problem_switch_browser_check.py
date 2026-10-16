"""Bundled navigation downloads once and safely ignores late navigation results."""
import os,json,time
from pathlib import Path
os.environ['PLAYWRIGHT_BROWSERS_PATH']='/tmp/dic2-browsers'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(args=['--no-sandbox'])
    page=browser.new_page();requests=[];errors=[];timings=[]
    page.on('request',lambda r:requests.append(r.url) if '/api/' in r.url else None)
    page.on('pageerror',lambda e:errors.append(str(e)))
    def ready(target):
        page.wait_for_function('t=>!document.querySelector("#results").hidden && document.querySelector("#equation strong").textContent===t',arg=target)
    page.goto('http://127.0.0.1:8000');ready('Profit')
    for problem,target in [('boston','medv'),('startups','Profit'),('boston','medv')]:
        start=time.perf_counter();page.select_option('#problem',problem);ready(target)
        timings.append({'problem':problem,'ms':round((time.perf_counter()-start)*1000)})
    page.select_option('#problem','custom');page.click('#loadExample');ready('tip')
    page.select_option('#problem','startups');ready('Profit')
    page.click('#loadExample');ready('tip')
    for problem in ['startups','boston','tips']:
        assert sum(url.endswith('/api/builtin/'+problem) for url in requests)==1,requests
    assert not any('/api/analyze' in url for url in requests)
    # Simultaneous requests reuse one pending download. Last choice wins.
    page.evaluate("builtinMemory.delete('boston')")
    before=sum(url.endswith('/api/builtin/boston') for url in requests)
    page.evaluate("document.querySelector('#problem').value='boston';builtin();document.querySelector('#problem').value='startups';builtin();document.querySelector('#problem').value='boston';builtin();")
    ready('medv')
    assert sum(url.endswith('/api/builtin/boston') for url in requests)==before+1
    assert not errors,errors
    Path('artifacts/switch-browser-after.json').write_text(json.dumps(timings,indent=2))
    print('PASS: one download per problem; zero training; in-flight reuse; latest selection wins',timings)
    browser.close()
