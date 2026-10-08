"""Compare common, nonempty result-matching PROFILE pairs from saved summaries."""
from pathlib import Path
import pandas as pd

p=Path(__file__).resolve().parents[1]
frames=[]
for name,path in [('Gemini','outputs/performance_profile_summary.csv'),('Gemma','outputs/gemma_26b_performance_profile_summary.csv')]:
    d=pd.read_csv(p/path,keep_default_na=False)
    if d.duplicated(['instance_id','query_kind']).any():raise ValueError('Duplicate summary keys')
    d=d[d.query_kind.eq('generated')].copy()
    ok=d.all_repetitions_nonempty_result_match.astype(str).str.lower().isin(['true','1'])
    d=d[ok & pd.to_numeric(d.repetitions).eq(3)]
    for field in ['db_hits_median','client_elapsed_profile_ms_median']:d[field]=pd.to_numeric(d[field],errors='raise')
    frames.append(d)
common=frames[0].merge(frames[1],on=['instance_id','database'],suffixes=('_gemini','_gemma'),validate='one_to_one')
if common.empty:raise ValueError('No common eligible PROFILE cases')
out=p/'outputs/benchmark_comparison';out.mkdir(exist_ok=True)
common.to_csv(out/'paired_performance_measurements.csv',index=False)
rows=[]
for name,suffix in [('Gemini','gemini'),('Gemma','gemma')]:
    rows.append({'model':name,'common_cases':len(common),'median_db_hits':common['db_hits_median_'+suffix].median(),'median_recorded_client_profile_ms':common['client_elapsed_profile_ms_median_'+suffix].median()})
pd.DataFrame(rows).to_csv(out/'performance_comparison_summary.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
print('Common IDs only; three repetitions per query, warm-ups excluded.')
print('Recorded client timing includes network and PROFILE overhead; runs were at different times. It is not an isolated model-speed comparison.')
