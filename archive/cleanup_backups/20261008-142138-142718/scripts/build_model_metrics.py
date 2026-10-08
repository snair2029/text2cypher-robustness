"""Audit saved generation and syntax records; no external requests."""
from pathlib import Path
import hashlib
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT = Path(__file__).resolve().parents[1]

def build():
    paths = ['data/generated_queries.csv','outputs/benchmark_gemma_26b.csv',
             'outputs/neo4j_syntax_validation.csv','outputs/gemma_26b_syntax_validation.csv']
    g,h,s,t = [pd.read_csv(PROJECT/p,keep_default_na=False) for p in paths]
    for df in (g,h,s,t):
        if len(df)!=200 or df.instance_id.eq('').any() or df.instance_id.duplicated().any() or set(df.instance_id)!=set(g.instance_id):
            raise ValueError('Expected identical sets of 200 unique IDs.')
    m=g.merge(h,on='instance_id',suffixes=('_gemini','_gemma'),validate='one_to_one')
    for field in ('question','schema','cypher'):
        if not m[field+'_gemini'].eq(m[field+'_gemma']).all(): raise ValueError('Inputs differ: '+field)
    if not h.generation_status.eq('completed').all() or not h.model_requested.eq('gemma-4-26b-a4b-it').all():
        raise ValueError('Unexpected Gemma model or incomplete generation.')
    records=[]
    for name,df,syntax in [('Gemini',g,s),('Gemma',h,t)]:
        query,reference=df.generated_cypher.str.strip(),df.cypher.str.strip()
        if query.eq('').any(): raise ValueError('Empty query')
        scores=pd.to_numeric(df.bleu_score,errors='raise')
        if scores.isna().any() or not scores.between(0,100).all(): raise ValueError('Invalid saved BLEU')
        records.append(dict(model=name,records=len(df),mean_sentence_bleu=scores.mean(),
            lowercase_trimmed_exact_match_count=int(query.str.lower().eq(reference.str.lower()).sum()),
            case_sensitive_trimmed_exact_match_count=int(query.eq(reference).sum()),
            syntax_accepted_count=int(syntax.generated_status.eq('accepted').sum()),
            syntax_error_count=int(syntax.generated_status.eq('syntax_error').sum())))
    result=pd.DataFrame(records)
    out=PROJECT/'outputs/benchmark_comparison';out.mkdir(parents=True,exist_ok=True)
    result.to_csv(out/'model_metrics.csv',index=False)
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,field,title,limit in zip(axes,['mean_sentence_bleu','case_sensitive_trimmed_exact_match_count','syntax_accepted_count'],['Mean sentence BLEU (0–100)','Trimmed Exact Match (of 200)','Syntax accepted (of 200)'],[100,200,200]):
        bars=ax.bar(result.model,result[field],color=['#2369a1','#d4782a'])
        ax.bar_label(bars,fmt='%.2f' if 'bleu' in field else '%.0f',padding=3)
        ax.set_title(title,fontsize=10);ax.set_ylim(0,limit*1.12)
    fig.text(.02,.015,'BLEU averages saved sentence scores across all 200 rows, including zeros. Exact Match is recomputed from saved text.',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1))
    for ext in ('png','pdf'):fig.savefig(out/f'model_metrics.{ext}',dpi=220)
    plt.close(fig)
    (out/'metric_provenance.json').write_text(json.dumps({'inputs':{p:hashlib.sha256((PROJECT/p).read_bytes()).hexdigest() for p in paths},'same_question_schema_reference':True,'bleu_method':'Mean of saved sentence BLEU scores, including zeros; BLEU not regenerated','gemini_model_evidence':'Journal/script; no per-query model metadata','gemma_model':'gemma-4-26b-a4b-it'},indent=2))
    print(result.to_string(index=False))
    return result

if __name__=='__main__':build()
