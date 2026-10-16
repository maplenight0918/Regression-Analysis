import json
import shutil
from unittest.mock import patch
from pathlib import Path
from app import builtin
from preset_cache import ROOT,load_presets,PRESETS

def test_saved_results_and_default_seed():
    from app import AnalysisRequest
    assert AnalysisRequest(dataset='x',target='y',features=['x']).seed==0
    for problem in PRESETS:
        with patch('app.analyze',side_effect=AssertionError('Should not train on page load')):
            response=builtin(problem)
        assert set(response['presets'])=={'0','42'}
        for seed,r in response['presets'].items():
            assert r['seed']==int(seed)
            assert len(r['models'])=={'startups':26,'boston':66,'tips':41}[problem]

def test_stale_cache_rejected(tmp_path):
    shutil.copytree(ROOT/'data',tmp_path/'data')
    shutil.copy(ROOT/'analysis.py',tmp_path/'analysis.py')
    with patch('preset_cache.ROOT',tmp_path):
        assert set(load_presets('startups'))=={'0','42'}
        with (tmp_path/'data'/'50_Startups.csv').open('a') as f:f.write('\n')
        assert load_presets('startups')=={}

def test_every_numeric_target_has_correct_isolated_presets():
    from preset_cache import numeric_targets
    from app import target_presets
    total=0
    for problem in PRESETS:
        for target in numeric_targets(problem):
            response=target_presets(problem,target)
            assert response['target']==target
            assert set(response['presets'])=={'0','42'}
            for seed,result in response['presets'].items():
                assert result['target']==target and result['seed']==int(seed)
                for method in result['methods']:
                    models=[m for m in result['models'] if m['method']==method]
                    assert sorted(m['k'] for m in models)==list(range(1,result['encoded']+1))
                    assert all(target not in m['features'] for m in models)
                total+=1
    assert total==42
