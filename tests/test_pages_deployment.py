import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app
from scripts.build_pages import build


def test_pages_export_contains_every_validated_target(tmp_path):
    build(tmp_path)
    for problem,count in [('startups',4),('boston',14),('tips',3)]:
        descriptor=json.loads((tmp_path/'datasets'/f'{problem}.json').read_text())
        assert descriptor['id']=='builtin:'+problem
        assert len(descriptor['preset_files'])==count
        for target,path in descriptor['preset_files'].items():
            payload=json.loads((tmp_path/path).read_text())
            assert payload['target']==target
            assert set(payload['presets'])=={'0','42'}
            assert all(result['target']==target for result in payload['presets'].values())
    assert '"staticData": true' in (tmp_path/'deployment-config.js').read_text()
    assert 'href="/style.css"' not in (tmp_path/'index.html').read_text()
    assert not (tmp_path/'app.py').exists()


def test_stale_export_fails(tmp_path):
    import pytest
    with patch('scripts.build_pages.load_presets',return_value={}):
        with pytest.raises(ValueError,match='Stale or missing'):build(tmp_path)


def test_api_url_must_be_https_origin(tmp_path):
    import pytest
    for url in ['http://example.com','https://user:pass@example.com','https://example.com/path','javascript:alert(1)']:
        with pytest.raises(ValueError):build(tmp_path,url)


def test_pages_cors_and_health():
    with TestClient(app) as client:
        response=client.get('/api/health',headers={'Origin':'https://maplenight0918.github.io'})
        assert response.json()=={'status':'ok','service':'dic2-regression'}
        assert response.headers['access-control-allow-origin']=='https://maplenight0918.github.io'
        preflight=client.options('/api/analyze',headers={'Origin':'https://maplenight0918.github.io','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
        assert preflight.status_code==200
        assert 'access-control-allow-origin' not in client.get('/api/health',headers={'Origin':'https://unrelated.example'}).headers
