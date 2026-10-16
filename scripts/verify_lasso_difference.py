"""Reproduce the reference repository's Lasso ranking without changing the app."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LassoCV,LinearRegression
from sklearn.metrics import mean_squared_error
ROOT=Path(__file__).resolve().parents[1]
d=pd.read_csv(ROOT/'data/50_Startups.csv')
d=pd.get_dummies(d,columns=['State'],dtype=int)
features=['R&D Spend','Administration','Marketing Spend','State_Florida','State_New York']
a,b,c,e=train_test_split(d[features].astype(float),d.Profit,test_size=.20,random_state=0)
z=StandardScaler().fit_transform(a)
fit=LassoCV(cv=5,random_state=0,max_iter=100000).fit(z,c)
rank=[name for _,name in sorted(zip(abs(fit.coef_),features),reverse=True)]
assert all(fit.coef_[features.index(name)]==0 for name in ['Administration','State_Florida','State_New York'])
assert rank==['R&D Spend','Marketing Spend','State_New York','State_Florida','Administration']
current=json.loads((ROOT/'data/presets/startups-0.json').read_text())['result']
comparisons=[]
for k in range(1,6):
 chosen=rank[:k];pred=LinearRegression().fit(a[chosen],c).predict(b[chosen])
 rmse=float(np.sqrt(mean_squared_error(e,pred)))
 ours=next(m for m in current['models'] if m['id']==f'Lasso:{k}')
 if k in (1,2,5):assert np.isclose(rmse,ours['rmse'],rtol=1e-9,atol=1e-5)
 comparisons.append({'k':k,'reference_features':chosen,'current_features':ours['features'],'reference_rmse':rmse,'current_rmse':ours['rmse']})
report={'source':'https://github.com/huanchen1107/AIoT-DIC2-MultipleLR/blob/main/feature_progression_analysis.py','seed':0,'reference_alpha':float(fit.alpha_),'reference_lasso_coefficients':dict(zip(features,map(float,fit.coef_))),'reference_ranking':rank,'zero_coefficient_tie_confirmed':True,'comparison':comparisons}
(ROOT/'artifacts/lasso-difference-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
