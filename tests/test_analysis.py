import numpy as np
import pandas as pd
import pytest
from analysis import Prep,analyze,METHODS

def test_preprocessing_train_only():
    p=Prep().fit(pd.DataFrame({'x':[1.,3.,None],'state':['a','b','a']}))
    z=p.transform(pd.DataFrame({'x':[None,999.],'state':['unknown','b']}))
    assert z.iloc[0]['x']==2 and z.iloc[0]['state = b']==0
    assert p.spec[0]['max']==3

def test_startups_all():
    d=pd.read_csv('data/50_Startups.csv');r=analyze(d,'Profit',list(d.columns[:-1]),5,METHODS)
    assert len(r['models'])==26 and r['train']==40 and r['test']==10
    assert r['encoded']==5
    best=next(m for m in r['models'] if m['id']==r['best'])
    assert best['cv_rmse']==min(m['cv_rmse'] for m in r['models'])
    for m in r['models']:
        assert m['k']==len(m['features'])
        for row in m['residuals']:assert row['residual']==pytest.approx(row['actual']-row['predicted'])
        # Serialized original-unit equation must reproduce held-out predictions.
        prep=Prep().fit(d.drop(columns='Profit'))
        for row in m['residuals']:
            source=d.iloc[[row['id']-1]]
            encoded=prep.transform(source)
            pred=m['coefficients'][0]['estimate']+sum(c['estimate']*encoded.iloc[0][c['feature']] for c in m['coefficients'][1:])
            assert pred==pytest.approx(row['predicted'],abs=1e-6)

def test_guards():
    d=pd.read_csv('data/BostonHousing.csv')
    d['extra']=np.arange(len(d))
    candidates=[c for c in d if c!='medv']
    with pytest.raises(ValueError,match='exceeding'):analyze(d,'medv',candidates,None,['Exhaustive Search'])
    with pytest.raises(ValueError,match='25'):analyze(d.head(10),'medv',candidates,1,['Lasso'])

def test_custom_missing_zero_and_singular():
    rng=np.random.RandomState(42);d=pd.DataFrame({'a':rng.randn(60),'b':rng.randn(60),'group':['x','y','z']*20,'target':rng.randn(60)})
    d.loc[::7,'a']=np.nan;d.loc[::6,'target']=0;d['duplicate']=d.b
    r=analyze(d,'target',['a','b','group','duplicate'],2,METHODS)
    full=r['models'][-1]
    assert full['reason'] and full['coefficients'][1]['p'] is None
    for m in r['models']:
        for row in m['residuals']:
            if row['actual']==0:assert row['percentage'] is None

def test_seed_zero_reproduces_reference_two_feature_model():
    d=pd.read_csv('data/50_Startups.csv')
    r=analyze(d,'Profit',list(d.columns[:-1]),2,['Lasso'],seed=0)
    m=next(m for m in r['models'] if m['id']=='Lasso:2')
    assert r['seed']==0
    assert m['rmse']==pytest.approx(8198.79719078855)
    assert m['r2']==pytest.approx(.947438644726848)
    again=analyze(d,'Profit',list(d.columns[:-1]),2,['Lasso'],seed=0)
    assert again['best']==r['best']
    assert [x['id'] for x in again['models'][0]['residuals']]==[x['id'] for x in r['models'][0]['residuals']]
    different=analyze(d,'Profit',list(d.columns[:-1]),2,['Lasso'],seed=42)
    assert set(x['id'] for x in different['models'][0]['residuals'])!=set(x['id'] for x in r['models'][0]['residuals'])
    with pytest.raises(ValueError,match='Seed'):analyze(d,'Profit',list(d.columns[:-1]),2,['Lasso'],seed=7)


def test_optimized_inner_cv_matches_independent_sklearn():
    from analysis import cv_cache,subset_score
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LinearRegression
    d=pd.read_csv('data/50_Startups.csv');x=d.drop(columns='Profit');y=d.Profit.to_numpy()
    names=['R&D Spend','Marketing Spend','State = New York'];scores=[]
    for a,b in KFold(3,shuffle=True,random_state=0).split(x):
        prep=Prep().fit(x.iloc[a]);aa=prep.transform(x.iloc[a]).reindex(columns=names,fill_value=0);bb=prep.transform(x.iloc[b]).reindex(columns=names,fill_value=0)
        scale=StandardScaler().fit(aa);fit=LinearRegression().fit(scale.transform(aa),y[a])
        scores.append(np.sqrt(np.mean((y[b]-fit.predict(scale.transform(bb)))**2)))
    assert subset_score(names,cv_cache(x,y,0))==pytest.approx(np.mean(scores),rel=1e-10)

def test_full_progression_infers_encoded_count():
    d=pd.read_csv('data/BostonHousing.csv')
    r=analyze(d,'medv',[c for c in d if c!='medv'],None,['Lasso','RFE'],seed=0)
    for method in ['Lasso','RFE']:
        assert [m['k'] for m in r['models'] if m['method']==method]==list(range(1,14))
    d['extra']=np.arange(len(d))
    r=analyze(d,'medv',[c for c in d if c!='medv'],None,['Lasso','Exhaustive Search'],seed=0)
    assert r['skipped'][0]['method']=='Exhaustive Search'
    assert not any(m['method']=='Exhaustive Search' for m in r['models'])
    assert len([m for m in r['models'] if m['method']=='Lasso'])==14
