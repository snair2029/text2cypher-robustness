"""Compare saved logical outcomes; makes no API or database requests."""
import argparse
from pathlib import Path
import hashlib
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--gemini', default='outputs/gemini_benchmark_logical_reconciled.csv')
parser.add_argument('--gemma', default='outputs/gemma_26b_logical_validation.csv')
parser.add_argument('--output', default='outputs/benchmark_comparison')
args = parser.parse_args()
a, b = [pd.read_csv(p, keep_default_na=False) for p in (args.gemini, args.gemma)]
for df in (a, b):
    if len(df) != 200 or df.instance_id.eq('').any() or df.instance_id.duplicated().any():
        raise SystemExit('Expected 200 unique, nonempty question IDs.')
if set(a.instance_id) != set(b.instance_id):
    raise SystemExit('Question ID sets differ.')
m = a.merge(b, on='instance_id', suffixes=('_gemini', '_gemma'), validate='one_to_one')
if not m.database_reference_alias_gemini.eq(m.database_reference_alias_gemma).all():
    raise SystemExit('Source graph aliases differ.')
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
m.to_csv(out/'paired_logical_outcomes.csv', index=False)
table = pd.concat([a.logical_status.value_counts().rename('Gemini'), b.logical_status.value_counts().rename('Gemma')], axis=1).fillna(0).astype(int)
table.index.name = 'logical_status'
table.to_csv(out/'logical_outcome_counts.csv')
pd.crosstab(m.logical_status_gemini, m.logical_status_gemma).to_csv(out/'paired_outcome_crosstab.csv')
x = m.logical_status_gemini.eq('observed_result_match')
y = m.logical_status_gemma.eq('observed_result_match')
pairs = pd.Series({'Both observed matches': int((x & y).sum()), 'Gemini only observed match': int((x & ~y).sum()), 'Gemma only observed match': int((~x & y).sum()), 'Neither observed match': int((~x & ~y).sum())}, name='count')
pairs.to_csv(out/'paired_match_counts.csv')
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
ax = table.rename(index=lambda s:s.replace('_',' ')).plot.barh(figsize=(11,7), color=['#2369a1','#d4782a'])
ax.set_xlabel('Questions (200 per model)'); ax.set_ylabel(''); ax.set_title('Saved database evaluation outcomes')
for container in ax.containers: ax.bar_label(container, padding=3)
ax.set_xlim(0,105)
plt.gcf().text(.02,.015,'Observed matches are not an overall correctness rate. Review and unavailable cases remain separate.',fontsize=9)
plt.tight_layout(rect=(0,.045,1,1))
for ext in ('png','pdf'): plt.savefig(out/f'logical_outcomes.{ext}',dpi=220)
plt.close()
ax = pairs.plot.barh(figsize=(10,4),color='#2369a1')
ax.set_xlabel('Paired questions'); ax.set_ylabel('');ax.set_title('Reference-result agreement on the same 200 questions')
ax.bar_label(ax.containers[0],padding=3);ax.set_xlim(0,180)
plt.gcf().text(.02,.015,'Neither observed match includes errors, review cases and unavailable graphs; it does not mean both are incorrect.',fontsize=8)
plt.tight_layout(rect=(0,.055,1,1))
for ext in ('png','pdf'): plt.savefig(out/f'paired_matches.{ext}',dpi=220)
plt.close()
manifest = {'inputs':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (args.gemini,args.gemma)},'paired_records':len(m),'graph_alias_matches':200,'both_source_graph_unavailable':int((m.logical_status_gemini.eq('source_graph_unavailable') & m.logical_status_gemma.eq('source_graph_unavailable')).sum()),'notes':['Automatic outcomes retained; manual reviews not merged.','Syntax failures may be recorded before source graph availability checks.','Public source graphs were not immutable snapshots.','These files do not verify generation prompts or settings; consult generation records.']}
(out/'provenance.json').write_text(json.dumps(manifest,indent=2))
print(table.to_string()); print('\n'+pairs.to_string()); print('Saved:',out)
