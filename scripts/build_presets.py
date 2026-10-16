"""Precompute every numeric target of the bundled datasets, for both seeds."""
import sys,json,time,argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from analysis import analyze,METHODS
from app import clean
from preset_cache import ROOT,PRESETS,fingerprint,load_presets,numeric_targets,cache_path

def build_one(task):
    problem,target,seed=task
    start=time.time();filename,_,_=PRESETS[problem];d=pd.read_csv(ROOT/'data'/filename)
    result=clean(analyze(d,target,[c for c in d if c!=target],None,METHODS,seed=seed))
    path=cache_path(problem,seed,target);path.parent.mkdir(exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'fingerprint':fingerprint(problem,seed,target),'result':result},ensure_ascii=False,separators=(',',':')))
    temporary.replace(path)
    return f'{problem} / {target} / seed={seed}: saved {len(result["models"])} models in {time.time()-start:.1f}s'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);args=parser.parse_args()
    jobs=[]
    for problem in PRESETS:
        for target in numeric_targets(problem):
            valid=load_presets(problem,target)
            for seed in (0,42):
                if str(seed) not in valid:jobs.append((problem,target,seed))
    print(f'{len(jobs)} target/seed combinations to build; unchanged caches reused.',flush=True)
    with ProcessPoolExecutor(max_workers=max(1,args.workers)) as pool:
        futures=[pool.submit(build_one,job) for job in jobs]
        for future in as_completed(futures):print(future.result(),flush=True)
    print('All numeric targets ready.',flush=True)
