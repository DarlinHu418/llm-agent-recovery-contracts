from pathlib import Path
from collections import Counter
import json,hashlib
R=Path(__file__).parent;B=R.parent
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def main():
    r1=read(B/'live_experiment'/'results.json');extra=read(B/'live_experiment'/'followup_results.json');r2=read(B/'contract_recovery'/'results.json');r3=read(B/'contract_boundaries'/'results.json')
    chosen=[]
    for r in r3:
        p=B/'contract_boundaries'/'replacement_runs'/f"e{r['episode']:02d}"/'run.json'
        chosen.append(read(p) if not r['valid'] and p.exists() and read(p)['valid'] else r)
    assert len(r1)==24 and len(extra)==8 and len(r2)==18 and len(chosen)==12
    assert all(r['valid_model_episode'] for r in r1+extra)
    assert all(r['valid'] for r in r2+chosen)
    for stage in ['live_experiment','contract_recovery','contract_boundaries']:
        proto=read(B/stage/'protocol.json')
        for n,h in proto['source_sha256'].items():assert hashlib.sha256((B/stage/n).read_bytes()).hexdigest()==h,(stage,n)
    inputs=['live_experiment/analysis.json','live_experiment/results.json','live_experiment/followup_results.json','live_experiment/measurement_audit.json','contract_recovery/analysis.json','contract_recovery/results.json','contract_boundaries/analysis.json','contract_boundaries/results.json','contract_boundaries/replacement_runs/e04/run.json']
    out={'stage1':read(B/'live_experiment'/'analysis.json'),'stage1_audit':read(B/'live_experiment'/'measurement_audit.json')['summary'],
      'stage2':read(B/'contract_recovery'/'analysis.json'),'stage3':read(B/'contract_boundaries'/'analysis.json'),
      'accounting':{'stage1_valid':32,'stage2_valid':18,'stage3_valid':12,'valid_total':62,'formal_and_replacement_attempts':63,'excluded_transport_failures':1,'pilots_excluded':True},
      'hashes':{p:hashlib.sha256((B/p).read_bytes()).hexdigest() for p in inputs}}
    (R/'data_snapshot.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(out['accounting']))
if __name__=='__main__':main()
