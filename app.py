import io, json, math, socket, ipaddress, uuid, threading, time
from pathlib import Path
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from typing import Literal
from analysis import analyze, METHODS
from preset_cache import load_presets, numeric_targets

ROOT=Path(__file__).parent
app=FastAPI(title='DIC-2 Regression Explorer')
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
DATA={};JOBS={};LOCK=threading.Lock()
SOURCES={'startups':('50_Startups.csv','Profit','https://raw.githubusercontent.com/Avik-Jain/100-Days-Of-ML-Code/master/datasets/50_Startups.csv'),'boston':('BostonHousing.csv','medv','https://raw.githubusercontent.com/selva86/datasets/master/BostonHousing.csv'),'tips':('tips.csv','tip','https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv')}

def clean(obj):
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [clean(v) for v in obj]
    if isinstance(obj,(np.integer,)):return int(obj)
    if isinstance(obj,(np.floating,float)):return float(obj) if math.isfinite(obj) else None
    return obj

def ingest(raw,source,target=None,key=None):
    if len(raw)>5_000_000:raise ValueError('The CSV size limit is 5 MB.')
    try:d=pd.read_csv(io.BytesIO(raw),encoding='utf-8-sig')
    except Exception:raise ValueError('Unable to read the CSV. Use UTF-8 encoding, comma-separated values, and a header row.')
    if not 25<=len(d)<=5000 or not 2<=len(d.columns)<=60:raise ValueError('The dataset must contain 25–5,000 rows and 2–60 columns.')
    d=d.replace([np.inf,-np.inf],np.nan)
    if not any(pd.api.types.is_numeric_dtype(d[c]) for c in d):raise ValueError('No numeric columns were found.')
    key=key or uuid.uuid4().hex
    if key not in DATA and len(DATA)>=20:DATA.pop(next(iter(DATA)))
    DATA[key]=d
    cols=[dict(name=c,type='numeric' if pd.api.types.is_numeric_dtype(d[c]) else 'category',missing=int(d[c].isna().sum())) for c in d]
    return clean(dict(id=key,source=source,target=target or next(c['name'] for c in reversed(cols) if c['type']=='numeric'),rows=len(d),columns=cols,preview=d.head(10).astype(object).where(d.head(10).notna(),None).to_dict('records')))

def builtin(problem:str):
    if problem not in SOURCES:raise HTTPException(404,'Unknown problem.')
    f,t,s=SOURCES[problem]
    payload=ingest((ROOT/'data'/f).read_bytes(),s,t,key='builtin:'+problem)
    payload['presets']=load_presets(problem)
    payload['preset_key']=problem
    if problem=='tips':payload['example']='Restaurant Tips'
    else:payload['builtin']=problem
    payload['preset_targets']=numeric_targets(problem)
    return payload

@app.get('/api/builtin/{problem}')
def builtin_response(problem:str):
    # Presets are already validated JSON; avoid FastAPI recursively re-encoding
    # hundreds of thousands of numeric values before serializing them again.
    return JSONResponse(builtin(problem))

def target_presets(problem:str,target:str):
    if problem not in SOURCES:raise HTTPException(404,'Unknown problem.')
    if target not in numeric_targets(problem):raise HTTPException(400,'The target must be a numeric column in this dataset.')
    return {'target':target,'presets':load_presets(problem,target)}

@app.get('/api/builtin/{problem}/presets')
def target_presets_response(problem:str,target:str):
    return JSONResponse(target_presets(problem,target))

class URLRequest(BaseModel):url:str
@app.post('/api/url')
def url_load(req:URLRequest):
    try:
        url=req.url
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            for _ in range(5):
                u=urlparse(url)
                if u.scheme not in ('https','http') or not u.hostname or u.username:raise ValueError('Enter a public HTTP(S) CSV URL.')
                addresses=socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80))
                if any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise ValueError('Only public internet data sources are allowed.')
                with client.stream('GET',url) as r:
                    if r.is_redirect:
                        from urllib.parse import urljoin
                        url=urljoin(url,r.headers['location']);continue
                    r.raise_for_status();raw=b''
                    for chunk in r.iter_bytes():
                        raw+=chunk
                        if len(raw)>5_000_000:raise ValueError('The CSV size limit is 5 MB.')
                    return ingest(raw,req.url)
            raise ValueError('The source redirected too many times.')
    except Exception as e:raise HTTPException(400,f'Loading failed: {e}')

@app.post('/api/upload')
async def upload(file:UploadFile=File(...)):
    try:return ingest(await file.read(5_000_001),f'Local CSV: {file.filename}')
    except ValueError as e:raise HTTPException(400,str(e))

class AnalysisRequest(BaseModel):
    dataset:str
    target:str
    features:list[str]
    seed:Literal[0,42]=0
    methods:list[str]=METHODS

@app.post('/api/analyze')
def start(req:AnalysisRequest):
    # Browser-cached bundled descriptors remain usable after server restart or
    # eviction from the bounded dataset registry. Custom CSV ids still expire.
    if req.dataset not in DATA and req.dataset.startswith('builtin:'):
        problem=req.dataset.removeprefix('builtin:')
        if problem in SOURCES:
            filename,target,source=SOURCES[problem]
            ingest((ROOT/'data'/filename).read_bytes(),source,target,key=req.dataset)
    if req.dataset not in DATA:raise HTTPException(400,'This dataset has expired. Load it again.')
    if not req.methods or any(m not in METHODS for m in req.methods):raise HTTPException(400,'Invalid selection method.')
    if not LOCK.acquire(blocking=False):raise HTTPException(429,'Another analysis is running. Try again after it finishes.')
    key=uuid.uuid4().hex;frame=DATA[req.dataset].copy();JOBS[key]={'status':'running'}
    def run():
        try:JOBS[key]={'status':'done','result':clean(analyze(frame,req.target,req.features,None,list(dict.fromkeys(req.methods)),seed=req.seed))}
        except Exception as e:JOBS[key]={'status':'error','error':str(e)}
        finally:LOCK.release()
    if len(JOBS)>30:JOBS.pop(next(iter(JOBS)))
    threading.Thread(target=run,daemon=True).start();return {'job':key}

@app.get('/api/jobs/{key}')
def job(key:str):
    if key not in JOBS:raise HTTPException(404,'Analysis job not found.')
    return JOBS[key]

app.mount('/',StaticFiles(directory=ROOT/'static',html=True),name='static')
