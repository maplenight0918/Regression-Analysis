function presetKey(d){return d?.preset_key||d?.builtin;}
const $=id=>document.getElementById(id), methods=['Lasso','Forward SFS','RFE','ElasticNet','Exhaustive Search'];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,n=3)=>v==null||!Number.isFinite(v)?'N/A':Number(v).toLocaleString('en-US',{maximumFractionDigits:n});
const pv=v=>v==null?'N/A':v<.0001?v.toExponential(2):v.toFixed(4);
const presetMemory=new Map(),presetRequests=new Map();
const builtinMemory=new Map(),builtinRequests=new Map();
async function loadBuiltin(problem){
    if(builtinMemory.has(problem))return builtinMemory.get(problem);
    if(!builtinRequests.has(problem)){
        builtinRequests.set(problem,api('/api/builtin/'+problem).then(d=>{
            builtinMemory.set(problem,d);
            return d;
        }).finally(()=>builtinRequests.delete(problem)));
    }
    return builtinRequests.get(problem);
}
const EXAMPLE_URL='https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv';
let dataLoadToken=0;
let dataset=null,result=null,mode='Lasso',active=null,charts=[],generation=0,busy=false,pendingAuto=false;
async function api(url,body){const r=await fetch(url,body instanceof FormData?{method:'POST',body}:body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const data=await r.json();if(!r.ok)throw Error(data.detail||'Request failed.');return data;}
function status(text,error=false){$('status').textContent=text;$('status').className='status'+(error?' error':'');}
function invalidate(){pendingAuto=false;generation++;result=null;active=null;$('results').hidden=true;$('activeModel').disabled=true;$('activeModel').innerHTML='<option>Available after analysis</option>';$('ks').innerHTML='';$('bestTag').textContent='★ Awaiting cross-validation';$('cliffTag').hidden=true;charts.forEach(c=>c.destroy());charts=[];status('Data or settings changed. Click Run Analysis.');}
function renderMethods(){const hints=['L1 Ranking','Forward','Backward','L1 + L2','Best subset'];$('methods').innerHTML=[...methods,'ALL'].map((m,i)=>`<button class="tab-btn ${mode===m?'active':''}" data-method="${m}"><i class="fa-solid ${['fa-filter','fa-arrow-trend-up','fa-scissors','fa-diagram-project','fa-magnifying-glass-chart','fa-layer-group'][i]}"></i> ${m==='ALL'?'Compare All Methods':m} <span class="badge-pill">${hints[i]||'Compare all'}</span></button>`).join('');$('methods').querySelectorAll('button').forEach(b=>b.onclick=()=>{mode=b.dataset.method;renderMethods();if(result){const candidates=result.models.filter(m=>mode==='ALL'||m.method===mode);if(candidates.length){active=candidates.find(m=>m.id===active?.id)||candidates.find(m=>m.k===active?.k)||candidates[0];renderResult();}else{const skip=result.skipped?.find(x=>x.method===mode);status(skip?skip.reason:'This method has not been run. Click Run Analysis.',!!skip);}}});}
function datasetName(d){
    if(d.builtin==='startups')return '50 Startups';
    if(d.builtin==='boston')return 'Boston Housing';
    if(d.example)return d.example;
    if(d.source?.split('?')[0]===EXAMPLE_URL)return 'Restaurant Tips';
    if(d.source?.startsWith('Local CSV: '))return d.source.slice('Local CSV: '.length);
    try{return decodeURIComponent(new URL(d.source).pathname.split('/').filter(Boolean).pop()||'Dataset');}
    catch{return 'Dataset';}
}
function setCustomProblemName(name=null){
    const option=$('problem').querySelector('option[value="custom"]');
    option.textContent=name?`Custom · ${name}`:'Custom CSV';
    option.title=option.textContent;
}
function acceptData(d){invalidate();dataset=d;setCustomProblemName(d.builtin?null:datasetName(d));$('target').disabled=false;if(presetKey(d))presetMemory.set(presetKey(d)+'|'+d.target,d.presets||{});$('datasetTag').textContent=`◉ ${datasetName(d)} · ${d.rows} rows`;$('source').textContent=`Source: ${d.source} ｜ ${d.rows} rows · ${d.columns.length} columns`;$('schema').innerHTML=d.columns.map(c=>`<span>${esc(c.name)} · ${c.type==='numeric'?'Numeric':'Categorical'} · Missing ${c.missing}</span>`).join('');$('previewTable').innerHTML=`<table class="data-table"><thead><tr>${d.columns.map(c=>`<th>${esc(c.name)}</th>`).join('')}</tr></thead><tbody>${d.preview.map(row=>`<tr>${d.columns.map(c=>`<td>${esc(row[c.name]??'—')}</td>`).join('')}</tr>`).join('')}</tbody></table>`;$('target').innerHTML=d.columns.filter(c=>c.type==='numeric').map(c=>`<option value="${esc(c.name)}" ${c.name===d.target?'selected':''}>${esc(c.name)}</option>`).join('');renderFeatures();updateDescription();status('Dataset loaded. Select the target and candidate predictors, then click Run Analysis.');}
function renderFeatures(){const target=$('target').value;$('features').innerHTML=dataset.columns.filter(c=>c.name!==target).map(c=>`<label><input type="checkbox" value="${esc(c.name)}" checked><span class="predictor-name">${esc(c.name)}</span></label>`).join('');$('features').querySelectorAll('input').forEach(el=>el.onchange=featuresChanged);}
async function builtin(){setCustomProblemName();const loadToken=++dataLoadToken;invalidate();dataset=null;$('run').disabled=true;$('target').disabled=true;$('source').textContent='Loading dataset…';$('features').innerHTML='';const problem=$('problem').value;$('description').textContent=problem==='boston'?'Boston Housing: Predict median home value (MEDV, in thousands of dollars) using housing and neighborhood characteristics from 506 Boston-area observations.':'50 Startups: Predict Profit from R&D Spend, Administration, Marketing Spend, and State. Explore how feature selection affects model simplicity and predictive performance.';try{const d=await loadBuiltin(problem);if($('problem').value!==problem||loadToken!==dataLoadToken)return;acceptData(d);$('url').value=d.source;requestAutoAnalysis();}catch(e){status(e.message,true);}finally{$('run').disabled=busy;}}
function chooseCustom(){
    setCustomProblemName();dataLoadToken++;invalidate();dataset=null;
    $('run').disabled=true;$('target').disabled=true;$('target').innerHTML='<option>Load a dataset first</option>';
    $('features').innerHTML='';$('schema').innerHTML='';$('previewTable').innerHTML='';
    $('datasetTag').textContent='◉ Custom Dataset';$('source').textContent='';$('url').value='';
    $('description').textContent='Custom CSV: Load a public CSV URL, upload a file, or try the Restaurant Tips example below.';
    status('Choose a CSV source or click Load & Analyze Example to get started.');
}
$('problem').onchange=()=>{$('problem').value==='custom'?chooseCustom():builtin();};
$('target').onchange=()=>{renderFeatures();updateDescription();requestAutoAnalysis();};
async function loadCSVURL(url,example=false){
    const loadToken=++dataLoadToken;
    invalidate();$('loadUrl').disabled=true;$('loadExample').disabled=true;
    status(example?'Loading the Restaurant Tips example…':'Loading CSV from URL…');
    try{
        const d=example?await loadBuiltin('tips'):await api('/api/url',{url});
        if(loadToken!==dataLoadToken)return;
        if(example){
            if(!d.columns.some(c=>c.name==='tip'&&c.type==='numeric'))throw Error('The example no longer contains a numeric tip column.');
            d.target='tip';d.example='Restaurant Tips';
        }
        $('problem').value='custom';$('url').value=url;acceptData(d);$('run').disabled=busy;
        if(example){mode='ALL';renderMethods();requestAutoAnalysis();}
    }catch(e){if(loadToken===dataLoadToken)status(e.message,true);}
    finally{$('loadUrl').disabled=false;$('loadExample').disabled=false;}
}
$('loadUrl').onclick=()=>loadCSVURL($('url').value);
$('loadExample').onclick=()=>loadCSVURL(EXAMPLE_URL,true);
$('file').onchange=async()=>{
    if(!$('file').files[0])return;
    const loadToken=++dataLoadToken;invalidate();
    const form=new FormData();form.append('file',$('file').files[0]);
    try{const d=await api('/api/upload',form);if(loadToken!==dataLoadToken)return;$('problem').value='custom';acceptData(d);$('run').disabled=busy;}
    catch(e){if(loadToken===dataLoadToken)status(e.message,true);}
};
function allFeaturesSelected(){
    const expected=dataset.columns.filter(c=>c.name!==$('target').value).map(c=>c.name);
    const selected=[...$('features').querySelectorAll('input:checked')].map(x=>x.value);
    return JSON.stringify(expected)===JSON.stringify(selected);
}
function updateDescription(){
    if(!dataset)return;
    const target=$('target').value;
    const name=datasetName(dataset);
    const label=dataset.builtin==='boston'&&target==='medv'?'median home value (MEDV, in thousands of dollars)':target;
    $('description').textContent=`${name}: Predict ${label} using the remaining fields as candidate predictors. Explore how feature selection affects model simplicity and predictive performance.`;
}
function featuresChanged(){
    if(presetKey(dataset)&&allFeaturesSelected()){requestAutoAnalysis();return;}
    const cached=presetKey(dataset)?presetMemory.get(presetKey(dataset)+'|'+$('target').value)?.[$('seed').value]:null;
    const selected=new Set([...$('features').querySelectorAll('input:checked')].map(x=>x.value));
    const count=cached?.models.find(m=>m.method==='Full OLS')?.inputs.filter(s=>selected.has(s.column)).reduce((n,s)=>n+s.names.length,0);
    const previousK=count!=null?Array.from({length:count},(_,i)=>i+1):[];
    invalidate();
    if(previousK.length)$('ks').innerHTML=[...new Set(previousK)].sort((a,b)=>a-b).map(k=>`<button class="k-btn" data-k="${k}" disabled>k = ${k}</button>`).join('');
    status('Candidate predictors changed. Click Run Analysis. Values of k remain in ascending order; restore all predictors to reuse built-in results.');
}
function matchingPreset(){
    if(!presetKey(dataset)||!allFeaturesSelected())return null;
    return presetMemory.get(presetKey(dataset)+'|'+$('target').value)?.[$('seed').value]||null;
}
async function fetchTargetPresets(){
    if(!presetKey(dataset)||!allFeaturesSelected())return;
    const problem=presetKey(dataset),target=$('target').value,key=problem+'|'+target;
    if(presetMemory.has(key))return;
    if(!presetRequests.has(key)){
        const promise=api(`/api/builtin/${problem}/presets?target=${encodeURIComponent(target)}`).then(data=>{
            presetMemory.set(key,data.presets);
        }).finally(()=>presetRequests.delete(key));
        presetRequests.set(key,promise);
    }
    await presetRequests.get(key);
}
function displayPreset(cached){
    result=cached;
    const candidates=mode==='ALL'?result.models:result.models.filter(m=>m.method===mode);
    active=candidates.find(m=>m.id===result.best)||[...candidates].sort((a,b)=>a.cv_rmse-b.cv_rmse||a.k-b.k)[0];
    renderResult();
    status(`Analysis ready · Seed ${result.seed} · Cached computed results; no retraining · Train ${result.train} / Test ${result.test}`);
}
async function requestAutoAnalysis(){
    invalidate();
    $('seedTag').textContent=`80/20 Split · Seed ${$('seed').value}`;
    if(!dataset)return;
    const token=generation;
    try{await fetchTargetPresets();}catch(e){if(token===generation)status(e.message,true);return;}
    if(token!==generation)return;
    const cached=matchingPreset();
    if(cached){displayPreset(cached);return;}
    pendingAuto=true;
    if(busy)status('Settings updated. The latest configuration will run after the current analysis finishes…');
    else runAnalysis();
}
$('seed').onchange=requestAutoAnalysis;
async function runAnalysis(){
    if(!dataset||busy)return;
    invalidate();
    const token=generation, seed=Number($('seed').value);
    busy=true;$('run').disabled=true;
    $('seedTag').textContent=`80/20 Split · Seed ${seed}`;
    const start=Date.now();
    status(`Preparing analysis · Seed ${seed}…`);
    try{
        const {job}=await api('/api/analyze',{dataset:dataset.id,target:$('target').value,features:[...$('features').querySelectorAll('input:checked')].map(x=>x.value),seed,methods:mode==='ALL'?methods:[mode]});
        while(true){
            const j=await api('/api/jobs/'+job);
            if(j.status==='done'||j.status==='error'){
                if(token!==generation)break;
                if(j.status==='error')throw Error(j.error);
                result=j.result;active=[...(mode==='ALL'?result.models:result.models.filter(m=>m.method===mode))].sort((a,b)=>a.cv_rmse-b.cv_rmse||a.k-b.k)[0]||result.models.find(m=>m.id===result.best);renderResult();
                status(`Analysis ready · Seed ${result.seed} · Train ${result.train} / Test ${result.test} · ${result.encoded} encoded predictors · ${result.dropped} invalid targets excluded · ${((Date.now()-start)/1000).toFixed(1)} s`);
                break;
            }
            if(token===generation)status(`Running nested CV and OLS · Seed ${seed}… ${Math.round((Date.now()-start)/1000)} s (Exhaustive Search may take a few minutes)`);
            await new Promise(r=>setTimeout(r,800));
        }
    }catch(e){if(token===generation)status(e.message,true);}
    finally{busy=false;$('run').disabled=false;if(pendingAuto)runAnalysis();}
}
$('run').onclick=runAnalysis;
function landmarks(method){
    const models=result.models.filter(m=>m.method===method).sort((a,b)=>a.k-b.k);
    const sweet=[...models].sort((a,b)=>a.cv_rmse-b.cv_rmse||a.k-b.k)[0];
    let cliff=null;
    for(let i=1;i<models.length;i++){
        const previous=models[i-1],model=models[i];
        if(model.k!==previous.k+1||previous.rmse<=0)continue;
        const rise=(model.rmse-previous.rmse)/previous.rmse;
        if(rise>=.05&&(!cliff||rise>cliff.rise))cliff={model,previous,rise};
    }
    return {sweet,cliff};
}
function renderResult(){if(!active)return;$('results').hidden=false;$('methodWarnings').hidden=!result.skipped?.length;$('methodWarnings').textContent=(result.skipped||[]).map(x=>x.reason).join(' ');const m=active,best=result.models.find(x=>x.id===result.best),{sweet,cliff}=landmarks(m.method);$('cliffTag').hidden=false;$('cliffTag').textContent=cliff?`⚠ Potential Overfitting Cliff: ${m.method} · k=${cliff.model.k} · Test RMSE +${fmt(cliff.rise*100,1)}%`:`${m.method}: No potential cliff meets the threshold`;$('landmarkNote').textContent=`Green Optimal Sweet Spot: the lowest CV RMSE for this method; the banner shows the best model across evaluated methods. Orange Potential Overfitting Cliff: the largest adjacent-k Test RMSE increase of at least 5% (a display heuristic, not a statistical test). ${cliff?`k=${cliff.previous.k} → ${cliff.model.k}: ${fmt(cliff.previous.rmse,2)} → ${fmt(cliff.model.rmse,2)}. `:''}An increase in test error does not establish overfitting and does not affect CV model selection.`;$('bestTag').textContent=`★ Optimal Sweet Spot: ${best.method} · k=${best.k} · RMSE ${fmt(best.cv_rmse,2)}`;$('activeModel').disabled=false;$('activeModel').innerHTML=[...result.models].sort((a,b)=>[...methods,'Full OLS'].indexOf(a.method)-[...methods,'Full OLS'].indexOf(b.method)||a.k-b.k).map(x=>`<option value="${esc(x.id)}" ${x.id===m.id?'selected':''}>${esc(x.method)} · k=${x.k}${x.id===result.best?' ★ CV best':''} · CV RMSE ${fmt(x.cv_rmse,2)}</option>`).join('');$('ks').innerHTML=result.models.filter(x=>x.method===m.method).sort((a,b)=>a.k-b.k).map(x=>`<button class="k-btn ${x.id===m.id?'active':''} ${x.id===sweet.id?'sweet-spot':''} ${x.id===cliff?.model.id?'overfitting':''}" data-id="${esc(x.id)}">k = ${x.k} ${x.id===sweet.id?'<span>★ Optimal Sweet Spot</span>':''} ${x.id===cliff?.model.id?'<span>⚠ Potential Overfitting Cliff</span>':''}</button>`).join('');$('ks').querySelectorAll('button').forEach(b=>b.onclick=()=>{active=result.models.find(x=>x.id===b.dataset.id);renderResult();});
const metrics=[['Test RMSE',fmt(m.rmse,2),m.id===sweet.id?'★ Optimal Sweet Spot':m.id===cliff?.model.id?'⚠ Potential Overfitting Cliff':'Comparison model','Lower is better'],['Test R²',fmt(m.r2,4),'Holdout test','Explained variation, not accuracy'],['Adjusted R²',fmt(m.adj_r2,4),'Training set','Computed from training-set OLS'],['Test MAE',fmt(m.mae,2),'Absolute error','Same units as the target'],['OLS F-statistic',fmt(m.f,2),`p = ${pv(m.fp)}`,'Overall model test on the training set']];$('metrics').innerHTML=metrics.map((x,i)=>`<div class="metric-card ${i<2?'sweet':''}"><div class="metric-title">${x[0]}</div><div class="metric-val">${x[1]}</div><span class="badge-tag ${i===0&&m.id===cliff?.model.id&&m.id!==sweet.id?'badge-amber':i<2?'badge-green':'badge-blue'}">${x[2]}</span><div class="metric-note">${x[3]}</div></div>`).join('');$('chips').innerHTML=m.features.map(f=>`<span class="feature-chip">${esc(f)}</span>`).join('');const base=result.models.find(x=>x.method==='Full OLS');$('comparison').textContent=`Active CV RMSE ${fmt(m.cv_rmse,2)}; Full OLS ${fmt(base.cv_rmse,2)}. ${m.cv_rmse<base.cv_rmse?'This model has lower CV error.':m.id===base.id?'This is the full-predictor baseline.':'Full OLS has lower or equal CV error.'}`;$('modelCaption').textContent=`Metrics, equation, coefficients, predictions, and residuals show: Seed ${result.seed} · ${m.method} / k=${m.k}. ${mode==='ALL'?'Compare All shows every evaluated method.':''}`;
$('equation').innerHTML=`<strong>${esc(result.target)}</strong> = ${fmt(m.coefficients[0].estimate,5)} `+m.coefficients.slice(1).map(c=>`<span class="${c.estimate>=0?'eq-pos':'eq-neg'}">${c.estimate>=0?'+':'−'} ${fmt(Math.abs(c.estimate),6)} × (${esc(c.feature)})</span>`).join(' ');$('coefficients').innerHTML=m.coefficients.map(c=>`<tr><td><span class="feature-chip">${esc(c.feature)}</span></td><td>${fmt(c.estimate,5)}</td><td>${fmt(c.se,4)}</td><td>${fmt(c.t,3)}</td><td><span class="badge-tag ${c.p!=null&&c.p<.05?'badge-green':'badge-amber'}">${pv(c.p)}</span></td><td>[${fmt(c.lo,4)}, ${fmt(c.hi,4)}]</td><td title="${esc(c.reason)}">${fmt(c.vif,3)}</td></tr>`).join('');$('statReason').textContent=m.reason?`N/A reason: ${m.reason}`:'Non-finite VIF values indicate constant predictors or perfect collinearity and are shown as N/A.';$('residualNote').textContent=`Residual = actual − predicted. High residual: |residual| > 2 × training RMSE = ${fmt(m.threshold,2)}. This is a heuristic flag, not a formal outlier test. Sample IDs are original CSV row numbers, starting at 1.`;$('residuals').innerHTML=m.residuals.map((r,i)=>`<tr><td>#${i+1}</td><td>${r.id}</td><td>${fmt(r.actual,2)}</td><td>${fmt(r.predicted,2)}</td><td class="${r.residual>=0?'eq-pos':'eq-neg'}">${fmt(r.residual,2)}</td><td>${fmt(r.absolute,2)}</td><td>${r.percentage==null?'N/A':fmt(r.percentage,2)+'%'}</td><td><span class="badge-tag ${r.high?'badge-amber':'badge-green'}">● ${r.high?'High residual':'Typical'}</span></td></tr>`).join('');renderCharts();renderPredictor();}
$('activeModel').onchange=()=>{active=result.models.find(x=>x.id===$('activeModel').value);if(mode!=='ALL'){mode=active.method==='Full OLS'?'ALL':active.method;renderMethods();}renderResult();};
function renderCharts(){charts.forEach(c=>c.destroy());charts=[];const colors=['#6366f1','#10b981','#f59e0b','#f43f5e','#06b6d4','#64748b'];const show=mode==='ALL'?[...new Set(result.models.map(x=>x.method))]:[active.method,...(active.method==='Full OLS'?[]:['Full OLS'])];for(const [id,key] of [['rmseChart','rmse'],['r2Chart','r2']]){const data=show.map(method=>{const ms=result.models.filter(x=>x.method===method).sort((a,b)=>a.k-b.k);return {label:method,data:ms.map(m=>({x:m.k,y:m[key],model:m})),borderColor:colors[[...methods,'Full OLS'].indexOf(method)],backgroundColor:colors[[...methods,'Full OLS'].indexOf(method)],borderWidth:2,pointRadius:ms.map(m=>m.id===landmarks(method).sweet.id||m.id===landmarks(method).cliff?.model.id?7:4),pointBackgroundColor:ms.map(m=>m.id===landmarks(method).cliff?.model.id?'#f59e0b':m.id===landmarks(method).sweet.id?'#10b981':colors[[...methods,'Full OLS'].indexOf(method)]),tension:.15,borderDash:method==='Full OLS'?[5,5]:[]};});charts.push(new Chart($(id),{type:'line',data:{datasets:data},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:c=>`${c.dataset.label}: ${fmt(c.parsed.y,4)}`,afterLabel:c=>['k = '+c.raw.model.k,...c.raw.model.features,'CV RMSE: '+fmt(c.raw.model.cv_rmse,3)]}}},scales:{x:{type:'linear',ticks:{stepSize:1},title:{display:true,text:'Number of encoded predictors (k)'}},y:{ticks:{maxTicksLimit:6}}}}}));}}
function renderPredictor(){const m=active;$('predLabel').textContent=`Predicted ${result.target}`;$('predictInputs').innerHTML=m.inputs.map((s,i)=>`<div class="input-group"><label for="pred${i}">${esc(s.column)}</label>${s.kind==='numeric'?`<input id="pred${i}" type="number" step="any" value="${Number(s.fill.toPrecision(12))}"><input id="range${i}" aria-label="${esc(s.column)} slider" type="range" min="${s.min}" max="${s.max===s.min?s.max+1:s.max}" step="any" value="${Number(s.fill.toPrecision(12))}">`:`<select id="pred${i}">${s.categories.map(c=>`<option ${c===s.fill?'selected':''}>${esc(c)}</option>`).join('')}</select><p class="note">Reference category: ${esc(s.categories[0])}</p>`}</div>`).join('');m.inputs.forEach((s,i)=>{$('pred'+i).oninput=()=>{if(s.kind==='numeric')$('range'+i).value=$('pred'+i).value;predict();};if(s.kind==='numeric')$('range'+i).oninput=()=>{$('pred'+i).value=$('range'+i).value;predict();};});predict();}
function predict(){let values={},notes=[];active.inputs.forEach((s,i)=>{const input=$('pred'+i).value;if(s.kind==='numeric'){const v=input===''?s.fill:Number(input);values[s.column]=Number.isFinite(v)?v:s.fill;if(input==='')notes.push(`${s.column} is blank; using training median ${fmt(s.fill)}`);if(v<s.min||v>s.max)notes.push(`${s.column} is outside the training range; this prediction is extrapolation`);}else{s.names.forEach((n,j)=>values[n]=input===s.categories[j+1]?1:0);}});const value=active.coefficients.reduce((sum,c,i)=>sum+c.estimate*(i?values[c.feature]??0:1),0);$('prediction').textContent=fmt(value,2);$('predNote').textContent=notes.join('; ')||'Input ranges and defaults come from training data. Unknown categories use zeros for all dummy variables.';}
renderMethods();builtin();
