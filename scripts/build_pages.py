"""Export a real static Pages frontend, including all validated model results.

No API credentials, server code, or uploaded datasets are included in the output.
The build deliberately fails if any committed result is stale or missing.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import builtin
from preset_cache import ROOT,PRESETS,numeric_targets,load_presets,cache_path


def build(output,api_base=''):
    api_base=api_base.strip().rstrip('/')
    if api_base:
        parsed=urlparse(api_base)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError('API_BASE_URL must be an HTTPS origin without credentials, path, query, or fragment.')
    output=Path(output)
    if output.resolve() in (ROOT.resolve(),(ROOT/'static').resolve()):
        raise ValueError('Export to a separate build directory.')
    output.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'static',output,dirs_exist_ok=True)
    datasets=output/'datasets';datasets.mkdir(exist_ok=True)
    presets=output/'presets';presets.mkdir(exist_ok=True)
    count=0
    for problem in PRESETS:
        descriptor=builtin(problem)
        descriptor.pop('presets')
        descriptor['preset_files']={}
        for target in numeric_targets(problem):
            saved=load_presets(problem,target)
            if set(saved)!={'0','42'}:
                raise ValueError(f'Stale or missing presets for {problem}/{target}. Install requirements-runtime.txt and run scripts/build_presets.py before exporting.')
            filename=cache_path(problem,0,target).name.replace('-0','',1)
            descriptor['preset_files'][target]='./presets/'+filename
            (presets/filename).write_text(json.dumps({'target':target,'presets':saved},ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
            count+=len(saved)
        (datasets/f'{problem}.json').write_text(json.dumps(descriptor,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    config={'staticData':True,'apiBase':api_base}
    (output/'deployment-config.js').write_text('window.REGRESSION_CONFIG = '+json.dumps(config)+';\n',encoding='utf-8')
    (output/'.nojekyll').write_text('')
    print(f'Pages export ready: {count} validated target/seed results; custom backend: {api_base or "not connected"}.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'dist'))
    args=parser.parse_args()
    configured=json.loads((ROOT/'deployment.json').read_text()).get('apiBase','')
    build(args.output,os.environ.get('API_BASE_URL') or configured)
