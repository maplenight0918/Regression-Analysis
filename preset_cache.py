"""Validated, persistent results for bundled datasets; including the bundled Tips example; never for arbitrary CSV."""
import hashlib
import json
from pathlib import Path
import numpy, pandas, sklearn, statsmodels
from analysis import METHODS

ROOT=Path(__file__).parent
PRESETS={'startups':('50_Startups.csv','Profit',5),'boston':('BostonHousing.csv','medv',13),'tips':('tips.csv','tip',8)}

def fingerprint(problem,seed,target=None):
    filename,default_target,maxk=PRESETS[problem]
    target=target or default_target
    h=hashlib.sha256()
    for raw in [(ROOT/'data'/filename).read_bytes(),(ROOT/'analysis.py').read_bytes()]:h.update(raw)
    h.update(json.dumps([seed,target,maxk,METHODS,numpy.__version__,pandas.__version__,sklearn.__version__,statsmodels.__version__]).encode())
    return h.hexdigest()

def numeric_targets(problem):
    frame=pandas.read_csv(ROOT/'data'/PRESETS[problem][0])
    return [c for c in frame if pandas.api.types.is_numeric_dtype(frame[c])]

def cache_path(problem,seed,target=None):
    default_target=PRESETS[problem][1]
    suffix='' if target is None or target==default_target else '-'+hashlib.sha256(target.encode()).hexdigest()[:12]
    return ROOT/'data'/'presets'/f'{problem}-{seed}{suffix}.json'

def load_presets(problem,target=None):
    loaded={}
    for seed in (0,42):
        path=cache_path(problem,seed,target)
        try:
            record=json.loads(path.read_text())
            if record['fingerprint']==fingerprint(problem,seed,target):loaded[str(seed)]=record['result']
        except (OSError,ValueError,KeyError):pass
    return loaded
