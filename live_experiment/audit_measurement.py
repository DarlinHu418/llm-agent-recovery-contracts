"""Offline audit only. No model calls, service writes or frozen-source edits."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib,json
from experiment import score,initial

ROOT=Path(__file__).parent
CORE=['native_accept','native_claim_aware_accept','authorized_exact','authorized_resolved_exact']

def bag_accept(state,fields):
    key=lambda row:tuple(row.get(k) for k in fields)
    return (Counter(map(key,state['approved']))==Counter(map(key,state['effects']))
            and (state.get('finish') or {}).get('status')=='completed')

def representation_checks(state):
    # These are evaluator-input encodings, not executed or fault-replayed trajectories.
    ids=[op['effect_id'] for op in state['approved']]
    encodings=[[ids],[[eid] for eid in ids]]
    baseline=score(state)
    for groups in encodings:
        view=deepcopy(state)
        view['events']=[{'tool':'send_notifications','arguments':{'effect_ids':group},'is_error':False} for group in groups]
        view['tool_calls']=len(groups)
        assert all(score(view)[key]==baseline[key] for key in CORE)

def self_checks():
    s=initial('same_approval_two','authorization_receipt',0)
    s['effects']=deepcopy(s['approved']);s['finish']={'status':'completed'}
    assert score(s)['authorized_resolved_exact']
    assert bag_accept(s,['to','subject','body'])
    representation_checks(s)
    bad=deepcopy(s);bad['effects']=[deepcopy(s['approved'][0])]*2
    assert bag_accept(bad,['to','subject','body'])
    assert not score(bad)['authorized_resolved_exact']
    bad=deepcopy(s);bad['effects'][0]['authorization_id']='unapproved'
    assert bag_accept(bad,['to','subject','body'])
    assert not bag_accept(bad,['authorization_id','to','subject','body'])
    assert not score(bad)['authorized_resolved_exact']

def main():
    self_checks();rows=[];hashes={}
    for phase,n in [('runs',24),('followup_runs',8)]:
        files=sorted((ROOT/phase).glob('*/state.json'));assert len(files)==n
        for path in files:
            s=json.loads(path.read_text(encoding='utf-8'));v=score(s)
            record=json.loads((path.parent/'run.json').read_text(encoding='utf-8'))
            assert record['valid_model_episode'] and record['returncode']==0
            assert all(v[key]==record[key] for key in CORE)
            representation_checks(s)
            payloads=Counter(tuple(op[k] for k in ['to','subject','body']) for op in s['approved'])
            rows.append({'run':str(path.parent.relative_to(ROOT)),
              'required_identical_multiplicity':any(n>1 for n in payloads.values()),
              'disagreement':v['native_accept']!=v['authorized_resolved_exact'],
              'post_error_grouping_changed':v['post_error_grouping_changed'],
              'payload_multiset_accept':bag_accept(s,['to','subject','body']),
              'authorization_multiset_accept':bag_accept(s,['authorization_id','to','subject','body']),
              'instance_accept':v['authorized_resolved_exact']})
            hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    summary={'episodes':len(rows),'disagreements':sum(r['disagreement'] for r in rows),
      'identical_required':{'episodes':sum(r['required_identical_multiplicity'] for r in rows),
        'disagreements':sum(r['disagreement'] and r['required_identical_multiplicity'] for r in rows)},
      'no_identical_required':{'episodes':sum(not r['required_identical_multiplicity'] for r in rows),
        'disagreements':sum(r['disagreement'] and not r['required_identical_multiplicity'] for r in rows)},
      'observed_group_changes':sum(r['post_error_grouping_changed'] for r in rows),
      'group_changes_without_identical_required':sum(r['post_error_grouping_changed'] and not r['required_identical_multiplicity'] for r in rows),
      'representation_only_core_score_changes':0,
      'payload_multiset_agreement_with_instance':sum(r['payload_multiset_accept']==r['instance_accept'] for r in rows),
      'authorization_multiset_agreement_with_instance':sum(r['authorization_multiset_accept']==r['instance_accept'] for r in rows),
      'scope':'Offline reanalysis and synthetic evaluator-input checks, not new model episodes or causal fault replays. Multiset agreement is local to these hard-bound approved effects.'}
    out={'summary':summary,'rows':rows,'input_sha256':hashes,
      'scorer_sha256':hashlib.sha256((ROOT/'experiment.py').read_bytes()).hexdigest()}
    (ROOT/'measurement_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
