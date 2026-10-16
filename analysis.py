"""Nested training-only feature selection; final inference in original units."""
import itertools, math, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.model_selection import train_test_split, KFold
from sklearn.linear_model import LinearRegression, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.stats.outliers_influence import variance_inflation_factor

METHODS = ['Lasso','Forward SFS','RFE','ElasticNet','Exhaustive Search']
LIMIT = 10000

class Prep:
    def fit(self, frame):
        self.spec = []
        for col in frame:
            s = frame[col]
            if pd.api.types.is_numeric_dtype(s):
                vals = pd.to_numeric(s, errors='coerce').replace([np.inf,-np.inf],np.nan)
                fill = float(vals.median()) if vals.notna().any() else 0.
                self.spec.append(dict(column=col, kind='numeric', fill=fill, min=float(vals.min()) if vals.notna().any() else 0., max=float(vals.max()) if vals.notna().any() else 1., names=[col]))
            else:
                clean=s.dropna().astype(str)
                fill=clean.mode().iloc[0] if len(clean) else '(Missing)'
                cats=sorted(set(clean.tolist()+[fill]))
                self.spec.append(dict(column=col,kind='category',fill=fill,categories=cats,names=[f'{col} = {v}' for v in cats[1:]]))
        self.names=[n for s in self.spec for n in s['names']]
        if len(set(self.names))!=len(self.names): raise ValueError('Encoded feature names are duplicated. Rename the conflicting columns.')
        return self
    def transform(self, frame):
        out={}
        for s in self.spec:
            c=frame[s['column']]
            if s['kind']=='numeric':
                out[s['column']]=pd.to_numeric(c,errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(s['fill']).to_numpy(float)
            else:
                c=c.fillna(s['fill']).astype(str)
                for cat,name in zip(s['categories'][1:],s['names']):out[name]=(c==cat).to_numpy(float)
        return pd.DataFrame(out,index=frame.index)

def rmse(y,p):return float(np.sqrt(mean_squared_error(y,p)))

def cv_cache(x,y,seed=42):
    # Fit each fold's preprocessing once. Subset OLS can then use the same
    # standardized columns without refitting identical preprocessing thousands of times.
    cache=[]
    for a,b in KFold(3,shuffle=True,random_state=seed).split(x):
        p=Prep().fit(x.iloc[a]); train=p.transform(x.iloc[a]); valid=p.transform(x.iloc[b])
        scaler=StandardScaler().fit(train)
        cache.append((dict(zip(train.columns,range(len(train.columns)))),scaler.transform(train),scaler.transform(valid),y[a],y[b]))
    return cache

def subset_score(names,cache):
    scores=[]
    for index,a,b,ya,yb in cache:
        # Unseen encoded columns are zero; vocabulary is learned only from this fold.
        aa=np.column_stack([a[:,index[n]] if n in index else np.zeros(len(a)) for n in names])
        bb=np.column_stack([b[:,index[n]] if n in index else np.zeros(len(b)) for n in names])
        aa=design(aa);bb=design(bb)
        beta=np.linalg.lstsq(aa,ya,rcond=None)[0]
        scores.append(float(np.sqrt(np.mean((yb-bb@beta)**2))))
    return float(np.mean(scores))

def selections(x,y,maxk,methods,seed=42):
    prep=Prep().fit(x); mat=prep.transform(x); names=list(mat.columns); p=len(names)
    if p<maxk:raise ValueError('A CV training fold has fewer encoded features than k. Remove candidate fields or merge rare categories.')
    z=StandardScaler().fit_transform(mat); yz=StandardScaler().fit_transform(y.reshape(-1,1)).ravel()
    result={}; cache=None
    for method in methods:
        if method in ['Lasso','ElasticNet']:
            fit=(Lasso(alpha=.01,max_iter=20000) if method=='Lasso' else ElasticNet(alpha=.01,l1_ratio=.5,max_iter=20000)).fit(z,yz)
            rank=np.argsort(-np.abs(fit.coef_),kind='stable')
            result[method]={k:[names[i] for i in rank[:k]] for k in range(1,maxk+1)}
        elif method=='RFE':
            alive=list(range(p)); ranks={}
            while alive:
                if len(alive)<=maxk:ranks[len(alive)]=[names[i] for i in alive]
                if len(alive)==1:break
                fit=LinearRegression().fit(z[:,alive],yz)
                alive.pop(int(np.argmin(np.abs(fit.coef_))))
            result[method]=ranks
        else:
            if cache is None:cache=cv_cache(x,y,seed)
            ranks={}; chosen=[]
            for k in range(1,maxk+1):
                choices=([*chosen,n] for n in names if n not in chosen) if method=='Forward SFS' else itertools.combinations(names,k)
                chosen=list(min(choices,key=lambda ns:subset_score(list(ns),cache)))
                ranks[k]=chosen.copy()
            result[method]=ranks
    return prep,result

def design(a):return np.column_stack([np.ones(len(a)),a])

def final_model(method,names,prep,xtr,xte,ytr,yte,ids,cv):
    a=prep.transform(xtr)[names].to_numpy(); b=prep.transform(xte)[names].to_numpy()
    # Solve standardized OLS for numerical stability; map all inference to original units.
    scaler=StandardScaler().fit(a); za=design(scaler.transform(a)); zb=design(scaler.transform(b))
    fit=sm.OLS(ytr,za).fit(); pred=fit.predict(zb)
    transform=np.eye(len(names)+1);transform[0,1:]=-scaler.mean_/scaler.scale_
    transform[1:,1:]=np.diag(1/scaler.scale_)
    beta=transform@fit.params; cov=transform@fit.cov_params()@transform.T
    se=np.sqrt(np.maximum(np.diag(cov),0))
    from scipy.stats import t
    singular=np.linalg.matrix_rank(za)<za.shape[1]
    reason='The design matrix is rank-deficient; coefficients are not uniquely identifiable.' if singular else ('Insufficient residual degrees of freedom.' if fit.df_resid<=0 else None)
    rows=[]
    for i,name in enumerate(['Intercept']+names):
        stat=beta[i]/se[i] if se[i]>0 else np.nan
        ci=t.ppf(.975,fit.df_resid)*se[i]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');vif=variance_inflation_factor(za,i) if i and not singular else np.nan
        rows.append(dict(feature=name,estimate=beta[i],se=se[i] if not reason else None,t=stat if not reason else None,p=2*t.sf(abs(stat),fit.df_resid) if not reason else None,lo=beta[i]-ci if not reason else None,hi=beta[i]+ci if not reason else None,vif=vif,reason=reason or ('VIF is not applicable to the intercept.' if i==0 else 'Non-finite statistics indicate constant predictors or collinearity and are shown as N/A.')))
    threshold=2*rmse(ytr,fit.predict(za))
    residuals=[dict(id=int(idx)+1,actual=yt,predicted=yp,residual=yt-yp,absolute=abs(yt-yp),percentage=100*abs((yt-yp)/yt) if yt!=0 else None,high=bool(abs(yt-yp)>threshold)) for idx,yt,yp in zip(ids,yte,pred)]
    residuals.sort(key=lambda r:-r['absolute'])
    specs=[s for s in prep.spec if any(n in names for n in s['names'])]
    return dict(id=f'{method}:{len(names)}',method=method,k=len(names),features=names,cv_rmse=cv,rmse=rmse(yte,pred),r2=r2_score(yte,pred),mae=mean_absolute_error(yte,pred),adj_r2=fit.rsquared_adj if not reason else None,f=fit.fvalue if not reason else None,fp=fit.f_pvalue if not reason else None,reason=reason,coefficients=rows,residuals=residuals,threshold=threshold,inputs=specs)

def analyze(frame,target,features,maxk,methods,seed=42):
    if seed not in (0,42):raise ValueError("Seed must be 0 or 42.")
    if target not in frame or not pd.api.types.is_numeric_dtype(frame[target]):raise ValueError('The target must be a numeric column.')
    if not features or target in features or len(set(features))!=len(features) or any(c not in frame for c in features):raise ValueError('Select valid candidate predictors without including the target.')
    y=pd.to_numeric(frame[target],errors='coerce').replace([np.inf,-np.inf],np.nan)
    keep=y.notna();d=frame.loc[keep];y=y[keep].to_numpy(float)
    if len(d)<25:raise ValueError('At least 25 rows with valid target values are required for holdout testing and nested cross-validation.')
    if np.std(y)==0:raise ValueError('The target is constant; regression evaluation is not meaningful.')
    train,test=train_test_split(np.arange(len(d)),test_size=.2,random_state=seed)
    xtr=d.iloc[train][features];xte=d.iloc[test][features];yt=y[train];ye=y[test]
    p=len(Prep().fit(xtr).names)
    if maxk is None:maxk=p
    if not 1<=maxk<=p:raise ValueError(f'The number of features must be between 1 and {p}.')
    if p>30:raise ValueError('At most 30 encoded predictors are supported. Remove fields or merge high-cardinality categories.')
    count=sum(math.comb(p,k) for k in range(1,maxk+1))
    skipped=[]
    if 'Exhaustive Search' in methods and count>LIMIT:
        message=f'Exhaustive Search requires {count:,} combinations per selection round, exceeding the {LIMIT:,} limit. It was not run. Remove candidate predictors to reduce the search space; other methods are unaffected.'
        if len(methods)==1:raise ValueError(message)
        skipped.append(dict(method='Exhaustive Search',reason=message))
        methods=[m for m in methods if m!='Exhaustive Search']
    if maxk+2 >= int(len(train)*.8*2/3):raise ValueError('Too many predictors for the inner CV training folds. Remove candidate predictors or add more rows.')
    scores={(m,k):[] for m in methods for k in range(1,maxk+1)};baseline=[]
    for a,b in KFold(5,shuffle=True,random_state=seed).split(xtr):
        xa=xtr.iloc[a];xb=xtr.iloc[b];ya=yt[a];yb=yt[b]
        prep,sel=selections(xa,ya,maxk,methods,seed)
        aa=prep.transform(xa);bb=prep.transform(xb)
        for m in methods:
            for k,names in sel[m].items():
                scaler=StandardScaler().fit(aa[names]);lr=LinearRegression().fit(scaler.transform(aa[names]),ya)
                scores[m,k].append(rmse(yb,lr.predict(scaler.transform(bb[names]))))
        scaler=StandardScaler().fit(aa);lr=LinearRegression().fit(scaler.transform(aa),ya);baseline.append(rmse(yb,lr.predict(scaler.transform(bb))))
    prep,sel=selections(xtr,yt,maxk,methods,seed)
    cv={key:float(np.mean(v)) for key,v in scores.items()}
    # Winner is frozen before inspecting independent test predictions.
    winner=min([(v,k,m) for (m,k),v in cv.items()]+[(float(np.mean(baseline)),p,'Full OLS')])
    models=[final_model(m,sel[m][k],prep,xtr,xte,yt,ye,d.index[test],cv[m,k]) for m in methods for k in range(1,maxk+1)]
    models.append(final_model('Full OLS',prep.names,prep,xtr,xte,yt,ye,d.index[test],float(np.mean(baseline))))
    return dict(skipped=skipped,seed=seed,models=models,best=f'{winner[2]}:{winner[1]}',train=len(train),test=len(test),dropped=int((~keep).sum()),encoded=p,target=target,combinations=count,methods=methods)
