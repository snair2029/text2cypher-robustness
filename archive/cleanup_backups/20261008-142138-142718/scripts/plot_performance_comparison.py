"""Validate paired performance summary and render report figures."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).resolve().parents[1]/'outputs/benchmark_comparison'
s=pd.read_csv(p/'performance_comparison_summary.csv');d=pd.read_csv(p/'paired_performance_measurements.csv')
assert len(d)>0 and d.instance_id.nunique()==len(d)
for _,r in s.iterrows():
 suffix=r.model.lower()
 assert r.common_cases==len(d)
 assert d['repetitions_'+suffix].eq(3).all()
 assert d['all_repetitions_nonempty_result_match_'+suffix].astype(str).str.lower().isin(['true','1']).all()
 for a,b in [('median_db_hits','db_hits_median'),('median_recorded_client_profile_ms','client_elapsed_profile_ms_median')]:
  assert abs(r[a]-d[b+'_'+suffix].median())<1e-8
fig,axes=plt.subplots(1,2,figsize=(10,4.5))
for ax,field,title in zip(axes,['median_db_hits','median_recorded_client_profile_ms'],['Median database hits','Median recorded client PROFILE time (ms)']):
 bars=ax.bar(s.model,s[field],color=['#2369a1','#d4782a'])
 ax.bar_label(bars,fmt='%.2f',padding=3);ax.set_ylim(0,s[field].max()*1.2);ax.set_title(title,fontsize=10)
fig.suptitle(f'Saved query performance on {len(d)} common eligible questions')
fig.text(.02,.025,'Three measured repetitions per query; warm-ups excluded. Runs occurred at different times.\nClient timing includes network transfer and PROFILE overhead; this is not model generation speed.',fontsize=9)
fig.tight_layout(rect=(0,.1,1,.94))
for ext in ['png','pdf']:fig.savefig(p/f'performance_comparison.{ext}',dpi=220)
print('PASS: paired medians, eligibility and repetition counts; PNG/PDF saved.')
