from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse,csv,hashlib,json,random,subprocess,sys,time
from notification_service import Service

ROOT=Path(__file__).parent
BIN=Path(r'C:\Users\16421\AppData\Roaming\npm\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe')
MODEL='gpt-5.6-sol'
CASES=['single_clean','single_lost_ack','same_approval_two','new_approval_same_content','partial_distinct_recipients','distinct_messages']
MECHANISMS=['content_receipt','authorization_receipt']

def initial(case,mechanism,rep):
    def op(ref,auth,to='alex@example.invalid',subject='Meeting cancelled',body='The meeting is cancelled.'):
        return {'effect_id':ref,'authorization_id':auth,'to':to,'subject':subject,'body':body}
    prefix=hashlib.sha256(f'{case}:{rep}'.encode()).hexdigest()[:8]
    a=op('op-'+prefix+'-1','approval-'+prefix+'-1')
    approved=[a]
    if case in ['same_approval_two','new_approval_same_content','partial_distinct_recipients','distinct_messages']:
        b=op('op-'+prefix+'-2',a['authorization_id'] if case=='same_approval_two' else 'approval-'+prefix+'-2')
        if case=='partial_distinct_recipients':b['to']='jordan@example.invalid'
        if case=='distinct_messages':b['subject']='Room changed';b['body']='The room is now 301.'
        approved.append(b)
    return {'case':case,'mechanism':mechanism,'rep':rep,'approved':approved,
            'fault_armed':case in ['single_lost_ack','partial_distinct_recipients'],
            'effects':[],'receipts':{},'events':[],'tool_calls':0,'finish':None}

def score(state):
    fields=['to','subject','body']
    def payload(x):return tuple(x[k] for k in fields)
    expected=Counter(x['effect_id'] for x in state['approved'])
    observed=Counter(x['effect_id'] for x in state['effects'])
    old=Counter(payload(x) for x in state['effects'])
    native_duplicates=sum(max(0,n-1) for n in old.values())
    native_goal=all(payload(x) in old for x in state['approved'])
    excess=sum((observed-expected).values());missing=sum((expected-observed).values())
    by_id={x['effect_id']:x for x in state['approved']}
    binding_errors=sum(x['effect_id'] not in by_id or
        any(x.get(k)!=by_id[x['effect_id']].get(k) for k in ['authorization_id',*fields])
        for x in state['effects'])
    exact=excess==missing==binding_errors==0
    finish=state.get('finish') or {}
    send_events=[x for x in state['events'] if x['tool']=='send_notifications']
    errors=[x for x in send_events if x['is_error']]
    post_error=send_events[send_events.index(errors[0])+1:] if errors else []
    original=set(errors[0]['arguments'].get('effect_ids',[])) if errors else set()
    grouping_changed=bool(len(original)>1 and any(
        set(x['arguments'].get('effect_ids',[])) < original for x in post_error))
    return {'native_goal':native_goal,'native_duplicates':native_duplicates,
            'native_accept':native_goal and native_duplicates==0,
            'agent_claim':finish.get('status','missing_finish'),
            'native_claim_aware_accept':native_goal and native_duplicates==0 and finish.get('status')=='completed',
            'authorized_excess':excess,'authorized_missing':missing,
            'binding_errors':binding_errors,
            'authorized_exact':exact,'authorized_resolved_exact':exact and finish.get('status')=='completed',
            'false_complete':finish.get('status')=='completed' and not exact,
            'effects':len(state['effects']),'tool_calls':state['tool_calls'],
            'send_calls':len(send_events),'post_error_grouping_changed':grouping_changed}

def command(folder,statefile):
    q=json.dumps
    return [str(BIN),'exec','--ignore-user-config','--ephemeral','--sandbox','read-only',
      '--skip-git-repo-check','--json','--disable','shell_tool','--disable','apps',
      '--disable','plugins','--disable','multi_agent','--disable','browser_use',
      '--disable','computer_use','--disable','memories','-c','project_doc_max_bytes=0',
      '-c','model_reasoning_effort="low"','-c','features.respect_system_proxy=true',
      '-c','model_provider="experiment_https"',
      '-c','model_providers.experiment_https={name="OpenAI HTTPS experiment",wire_api="responses",requires_openai_auth=true,supports_websockets=false,stream_max_retries=0,request_max_retries=0}',
      '-c','model_instructions_file='+q(str(ROOT/'agent_instructions.txt')),
      '-c','approval_policy="never"','-c','mcp_servers.notifications.command='+q(sys.executable),
      '-c','mcp_servers.notifications.args='+q([str(ROOT/'notification_service.py'),str(statefile)]),
      '-c','mcp_servers.notifications.required=true',
      '-c','mcp_servers.notifications.default_tools_approval_mode="approve"',
      '--model',MODEL,'--output-last-message',str(folder/'answer.txt'),'-']

PROMPT='Complete every approved notification occurrence in this task. Retrieve the authorizations from the notification service. Use the provided tools to perform and verify the work, recover from errors as you judge appropriate, then record finish. Identical notification content can correspond to distinct required occurrences; do not change the recipient or content.'

def run_one(case,mechanism,rep,phase):
    folder=ROOT/phase/f'{case}__{mechanism}__r{rep}';folder.mkdir(parents=True,exist_ok=True)
    meta=folder/'run.json'
    if meta.exists():return json.loads(meta.read_text(encoding='utf-8'))
    statefile=folder/'state.json';s=initial(case,mechanism,rep)
    statefile.write_text(json.dumps(s,indent=2),encoding='utf-8')
    (folder/'prompt.txt').write_text(PROMPT,encoding='utf-8')
    args=command(folder,statefile)
    (folder/'command.json').write_text(json.dumps(args,indent=2),encoding='utf-8')
    started=datetime.now(timezone.utc).isoformat();t=time.monotonic();timeout=False
    with (folder/'events.jsonl').open('w',encoding='utf-8') as out,(folder/'stderr.log').open('w',encoding='utf-8') as err:
        p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=out,stderr=err,cwd=folder,text=True,encoding='utf-8')
        try:p.communicate(PROMPT,timeout=180)
        except subprocess.TimeoutExpired:
            timeout=True;p.kill();p.communicate(timeout=10)
    s=json.loads(statefile.read_text(encoding='utf-8'));events=[]
    for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines():
        try:events.append(json.loads(line))
        except json.JSONDecodeError:pass
    usage=[x.get('usage',{}) for x in events if x.get('type')=='turn.completed']
    record={'case':case,'mechanism':mechanism,'rep':rep,'phase':phase,'model_requested':MODEL,
            'started_utc':started,'seconds':time.monotonic()-t,'returncode':p.returncode,'timeout':timeout,
            'turn_completed':bool(usage),'usage':usage[-1] if usage else {},
            **score(s)}
    approval_block=any('requires approval' in json.dumps(x) for x in events)
    record['harness_approval_block']=approval_block
    record['valid_model_episode']=record['turn_completed'] and bool(s['events']) and not approval_block
    meta.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return record

def preflight():
    p=ROOT/'preflight';p.mkdir(exist_ok=True)
    for m in MECHANISMS:
        f=p/(m+'.json');x=initial('single_lost_ack',m,0);f.write_text(json.dumps(x),encoding='utf-8')
        service=Service(f);eid=x['approved'][0]['effect_id']
        a,e=service.call('send_notifications',{'effect_ids':[eid]});assert e
        assert len(service.load()['effects'])==1
        a,e=service.call('send_notifications',{'effect_ids':[eid]});assert not e
        assert len(service.load()['effects'])==1
        f=p/(m+'_two.json');x=initial('new_approval_same_content',m,0);f.write_text(json.dumps(x),encoding='utf-8')
        service=Service(f);service.call('send_notifications',{'effect_ids':[o['effect_id'] for o in x['approved']]})
        assert len(service.load()['effects'])==(1 if m=='content_receipt' else 2)
        bad,_=service.call('send_notifications',{'effect_ids':['not-authorized']});assert bad['error']=='INVALID_EFFECT_REFERENCE'
    print('Preflight passed: post-commit fault, same-operation replay, authorization controls, invalid reference rejection',flush=True)

def freeze():
    p=ROOT/'protocol.json'
    if p.exists():return
    files=['experiment.py','notification_service.py','agent_instructions.txt']
    protocol={'frozen_utc':datetime.now(timezone.utc).isoformat(),'model_requested':MODEL,
      'cli_version':'0.154.0','reasoning_effort':'low','temperature':'provider default, not exposed by CLI',
      'seed':'not available','mechanisms':MECHANISMS,'cases':CASES,'repetitions':2,'planned_episodes':24,
      'max_concurrent':2,'episode_timeout_seconds':180,'max_tool_calls_instruction':10,
      'primary_decision':'For this fixed suite, an adapter is acceptable only if every valid episode satisfies the chosen evaluator. Report invalid runs separately; do not count them as successes.',
      'evaluators':['native content-goal coverage + zero semantic duplicates','same plus model-reported completed','all required authorized occurrences exactly once and model-reported completed'],
      'native_scope':'Faithful single-parent adaptation of IdempotencyBench semantic duplicate/goal concepts. Uses full body as well as recipient/subject (stronger content matching); not a reproduction of its published model results.',
      'limitations':['single model alias','synthetic notification service','six structural cases','two repetitions','no concurrency or production reliability claim'],
      'prompt':PROMPT,'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}}
    p.write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['preflight','pilot','main']);args=ap.parse_args()
    preflight()
    if args.mode=='preflight':return
    if args.mode=='pilot':
        for m in MECHANISMS:
            x=run_one('single_lost_ack',m,98,'pilot_v2')
            print(json.dumps(x,ensure_ascii=False),flush=True)
            assert x['valid_model_episode'] and x['send_calls']>0,'Pilot harness failed'
        return
    freeze()
    jobs=[(c,m,r) for c in CASES for m in MECHANISMS for r in [1,2]]
    random.Random(20261110).shuffle(jobs)
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as ex:
        futs=[ex.submit(run_one,c,m,r,'runs') for c,m,r in jobs]
        for f in as_completed(futs):
            x=f.result();rows.append(x);print(json.dumps(x,ensure_ascii=False),flush=True)
    rows.sort(key=lambda x:(x['case'],x['mechanism'],x['rep']))
    (ROOT/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    cols=[k for k in rows[0] if k!='usage']
    with (ROOT/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:x[k] for k in cols} for x in rows)

if __name__=='__main__':main()
