from unittest.mock import patch
import threading
from fastapi.testclient import TestClient
from app import app,DATA,AnalysisRequest,start


def test_compressed_builtin_and_target_results():
    with TestClient(app) as client:
        for path in ['/api/builtin/boston','/api/builtin/tips/presets?target=size']:
            response=client.get(path,headers={'Accept-Encoding':'gzip'})
            assert response.status_code==200
            assert response.headers['content-encoding']=='gzip'
            assert int(response.headers['content-length'])<len(response.content)*.4
            assert set(response.json()['presets'])=={'0','42'}


def test_evicted_builtin_is_restored_for_manual_analysis():
    DATA.pop('builtin:tips',None)
    completed=threading.Event()
    def fake_analyze(frame,target,features,*args,**kwargs):
        assert len(frame)==244 and target=='tip' and features==['total_bill']
        completed.set()
        return {'models':[]}
    with patch('app.analyze',side_effect=fake_analyze):
        result=start(AnalysisRequest(dataset='builtin:tips',target='tip',features=['total_bill'],methods=['Lasso']))
        assert result['job']
        assert completed.wait(5)
