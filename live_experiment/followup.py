"""Exploratory follow-up: add lost acknowledgements to the two multiplicity cases.

Kept separate from the original 24-episode protocol. The only state change from
those two task cases is fault_armed=True before the first notification attempt.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,random
import experiment as ex

base_initial=ex.initial
def initial_with_fault(case,mechanism,rep):
    state=base_initial(case,mechanism,rep)
    state['fault_armed']=True
    return state

def main():
    ex.initial=initial_with_fault
    p=ex.ROOT/'followup_protocol.json'
    if not p.exists():
        protocol={'frozen_utc':datetime.now(timezone.utc).isoformat(),
          'reason':'The initial study includes clean multiplicity controls. Test whether the decision discrepancy also occurs after an actual post-commit lost acknowledgement.',
          'status':'exploratory extension, separate from the 24-episode main study',
          'cases':['same_approval_two','new_approval_same_content'],'mechanisms':ex.MECHANISMS,
          'repetitions':2,'planned_episodes':8,'changed_field':'fault_armed=True',
          'source_sha256':{n:hashlib.sha256((ex.ROOT/n).read_bytes()).hexdigest()
                            for n in ['followup.py','experiment.py','notification_service.py','agent_instructions.txt']}}
        p.write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    jobs=[(c,m,r) for c in ['same_approval_two','new_approval_same_content']
          for m in ex.MECHANISMS for r in [1,2]]
    random.Random(20261111).shuffle(jobs)
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(ex.run_one,c,m,r,'followup_runs') for c,m,r in jobs]
        for f in as_completed(fs):
            x=f.result();rows.append(x);print(json.dumps(x,ensure_ascii=False),flush=True)
    rows.sort(key=lambda x:(x['case'],x['mechanism'],x['rep']))
    (ex.ROOT/'followup_results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
