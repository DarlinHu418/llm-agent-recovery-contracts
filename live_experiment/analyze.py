from pathlib import Path
from collections import Counter,defaultdict
from statistics import mean,median
import json,hashlib,csv
from experiment import ROOT,CASES,MECHANISMS

def rescore(state):
    """Independent offline implementation; does not call experiment.score."""
    approved=state['approved'];effects=state['effects']
    keys=['to','subject','body']
    payload=lambda x:tuple(x[k] for k in keys)
    content_counts={}
    for effect in effects:
        key=payload(effect);content_counts[key]=content_counts.get(key,0)+1
    goal=all(payload(op) in content_counts for op in approved)
    duplicates=sum(n-1 for n in content_counts.values())
    expected={op['effect_id']:op for op in approved}
    counts={}
    for effect in effects:
        key=effect['effect_id'];counts[key]=counts.get(key,0)+1
    missing=sum(1 for key in expected if not counts.get(key))
    excess=sum(max(0,n-(1 if key in expected else 0)) for key,n in counts.items())
    bad=0
    for effect in effects:
        op=expected.get(effect['effect_id'])
        if op is None or any(effect.get(k)!=op.get(k) for k in ['authorization_id',*keys]):bad+=1
    exact=(missing==0 and excess==0 and bad==0)
    status=(state.get('finish') or {}).get('status','missing_finish')
    sends=[e for e in state['events'] if e['tool']=='send_notifications']
    first_error=next((i for i,e in enumerate(sends) if e['is_error']),None)
    changed=False
    if first_error is not None:
        original=set(sends[first_error]['arguments'].get('effect_ids',[]))
        changed=len(original)>1 and any(set(e['arguments'].get('effect_ids',[]))<original for e in sends[first_error+1:])
    return {'native_goal':goal,'native_duplicates':duplicates,'native_accept':goal and duplicates==0,
      'agent_claim':status,'native_claim_aware_accept':goal and duplicates==0 and status=='completed',
      'authorized_excess':excess,'authorized_missing':missing,'binding_errors':bad,
      'authorized_exact':exact,'authorized_resolved_exact':exact and status=='completed',
      'false_complete':status=='completed' and not exact,'effects':len(effects),
      'tool_calls':len(state['events']),'send_calls':len(sends),'post_error_grouping_changed':changed}

def summarize(rows):
    result={}
    for m in MECHANISMS:
        allrows=[x for x in rows if x['mechanism']==m]
        valid=[x for x in allrows if x['valid_model_episode']]
        result[m]={'planned':len(allrows),'valid':len(valid),
          **{k:sum(bool(x[k]) for x in valid) for k in ['native_accept','native_claim_aware_accept',
             'authorized_exact','authorized_resolved_exact','false_complete','post_error_grouping_changed']},
          'authorized_missing':sum(x['authorized_missing'] for x in valid),
          'authorized_excess':sum(x['authorized_excess'] for x in valid),
          'binding_errors':sum(x['binding_errors'] for x in valid),
          'mean_tool_calls':mean(x['tool_calls'] for x in valid) if valid else None,
          'median_seconds':median(x['seconds'] for x in valid) if valid else None,
          'input_tokens':sum(x['usage'].get('input_tokens',0) for x in valid),
          'cached_input_tokens':sum(x['usage'].get('cached_input_tokens',0) for x in valid),
          'output_tokens':sum(x['usage'].get('output_tokens',0) for x in valid),
          'adopt_under_native':bool(valid) and len(valid)==len(allrows) and all(x['native_accept'] for x in valid),
          'adopt_under_native_claim_aware':bool(valid) and len(valid)==len(allrows) and all(x['native_claim_aware_accept'] for x in valid),
          'adopt_under_corrected':bool(valid) and len(valid)==len(allrows) and all(x['authorized_resolved_exact'] for x in valid)}
    return result

def read_phase(phase,expected):
    files=sorted((ROOT/phase).glob('*/run.json'))
    assert len(files)==expected,(phase,len(files),expected)
    rows=[]
    for f in files:
        x=json.loads(f.read_text(encoding='utf-8'))
        state=json.loads((f.parent/'state.json').read_text(encoding='utf-8'))
        assert all(x[k]==v for k,v in rescore(state).items()),f'Score drift: {f}'
        assert x['returncode']==0 and x['valid_model_episode'],f'Invalid model episode: {f}'
        eventfile=f.parent/'events.jsonl'
        if not eventfile.exists():eventfile=f.parent/'public_events.jsonl'
        raw=[json.loads(l) for l in eventfile.read_text(encoding='utf-8').splitlines() if l.strip()]
        calls=[z['item'] for z in raw if z.get('type')=='item.completed' and z.get('item',{}).get('type')=='mcp_tool_call']
        assert all(c.get('server')=='notifications' for c in calls),f'Unexpected MCP server: {f}'
        assert [(c['tool'],c['arguments']) for c in calls]==[(e['tool'],e['arguments']) for e in state['events']],f'CLI/server action mismatch: {f}'
        assert not any(z.get('item',{}).get('type') in ['command_execution','file_change'] for z in raw),f'Unexpected local action: {f}'
        # Public tool actions, final messages and usage suffice as evidence.
        public=[z for z in raw if z.get('item',{}).get('type')!='reasoning']
        (f.parent/'public_events.jsonl').write_text('\n'.join(json.dumps(z,ensure_ascii=False) for z in public)+'\n',encoding='utf-8')
        rows.append(x)
    return rows

def main():
    for proto_name in ['protocol.json','followup_protocol.json']:
        p=json.loads((ROOT/proto_name).read_text(encoding='utf-8'))
        for name,digest in p['source_sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,f'Frozen source changed: {name}'
    mainrows=read_phase('runs',24);extra=read_phase('followup_runs',8)
    cases=[]
    for case in CASES:
        cases.append({'case':case,**{m:{k:sum(bool(x[k]) for x in mainrows if x['case']==case and x['mechanism']==m)
          for k in ['native_accept','native_claim_aware_accept','authorized_resolved_exact','false_complete']} for m in MECHANISMS}})
    disagreements=[{k:x[k] for k in ['phase','case','mechanism','rep','native_accept','native_claim_aware_accept',
                      'authorized_resolved_exact','agent_claim','authorized_missing','native_duplicates']}
      for x in mainrows+extra if x['native_accept']!=x['authorized_resolved_exact']]
    pairs=[]
    for phase,rows in [('main',mainrows),('followup',extra)]:
        for case in sorted({x['case'] for x in rows}):
            for rep in [1,2]:
                a=next(x for x in rows if x['case']==case and x['rep']==rep and x['mechanism']=='content_receipt')
                b=next(x for x in rows if x['case']==case and x['rep']==rep and x['mechanism']=='authorization_receipt')
                pairs.append({'phase':phase,'case':case,'rep':rep,
                  'native_preference':'content' if a['native_accept']>b['native_accept'] else ('authorization' if a['native_accept']<b['native_accept'] else 'tie'),
                  'corrected_preference':'content' if a['authorized_resolved_exact']>b['authorized_resolved_exact'] else ('authorization' if a['authorized_resolved_exact']<b['authorized_resolved_exact'] else 'tie')})
    out={'main':summarize(mainrows),'followup':summarize(extra),'main_cases':cases,
         'disagreements':disagreements,'matched_pairs':pairs,
         'inference_scope':'Descriptive fixed-suite counterexample with one model alias and two repetitions; no population significance claim.',
         'verification':'Frozen source hashes, independent rescoring, model completion, MCP-only actions and raw effect bindings passed.'}
    (ROOT/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=list(disagreements[0])
    with (ROOT/'evaluator_disagreements.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(disagreements)
    print(json.dumps({k:out[k] for k in ['main','followup','verification']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
