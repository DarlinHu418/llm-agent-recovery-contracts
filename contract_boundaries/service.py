from pathlib import Path
import json,sys,os,hashlib

PROFILES={'resume':(False,True,False),'cached_terminal':(False,False,True),'expired_terminal':(True,False,True),'expired_snapshot':(True,False,False)}

def description(profile,variant):
    expired,resume,terminal=PROFILES[profile]
    parts=[
      'Request keys bind the ordered item list. While retained, the same key with changed parameters is rejected. A fresh key is an independent request; effect IDs are references, not deduplication tokens.',
      ('Reusing a retained key executes only unfinished original items and returns all receipts.' if resume else 'Reusing a retained key returns the saved first response only; it performs no additional work. That response can contain a receipt for only part of the original list.'),
      ('Keys were removed at request age 60 minutes. Requests using a removed key are new requests.' if expired else 'Keys remain stored until request age 60 minutes.'),
      ('inspect_status reads a final authoritative execution ledger: the original worker is permanently fenced. An item reported NOT_FOUND there has not executed and cannot later execute under the old request.' if terminal else 'inspect_status reads only a point-in-time execution index. NOT_FOUND does not exclude delayed execution by the original worker; inspecting does not fence, cancel or drain it.'),
      'New requests succeed immediately. Notification payloads come from the immutable approved list. There is no cancellation or other lookup tool in this task.']
    if variant==1:parts=parts[3:]+parts[:3]
    if variant==2:
        parts=[x.replace('NOT_FOUND','NOT_FOUND').replace('fresh key','previously unused key').replace('unfinished','remaining').replace('permanently fenced','permanently prevented from further writes').replace('point-in-time','instantaneous') for x in reversed(parts)]
    return '\n'.join(parts)

def initial(profile,variant,rep):
    token=hashlib.sha256(f'boundary:{variant}'.encode()).hexdigest()[:7]
    ids=['op-'+token+'-x','op-'+token+'-y'];key='req-'+token
    ops=[{'effect_id':ids[0],'to':'a@example.invalid','subject':'Room','body':'Room 301'},
         {'effect_id':ids[1],'to':'b@example.invalid','subject':'Time','body':'Time 14:00'}]
    expired,resume,terminal=PROFILES[profile]
    return {'profile':profile,'variant':variant,'rep':rep,'approved':ops,'original':{'effect_ids':ids,'request_key':key},
      'request_age_minutes':90 if expired else 20,'effects':[dict(ops[0])],'terminal':terminal,'late_pending':not terminal,
      'request_cache':{},'events':[],'finish':None}

class Service:
    def __init__(self,path):self.path=Path(path)
    def call(self,name,args):
        s=json.loads(self.path.read_text(encoding='utf-8'));err=False
        expired,resume,terminal=PROFILES[s['profile']];orig=s['original'];ops={o['effect_id']:o for o in s['approved']}
        if s['finish']:out={'error':'FINISHED'};err=True
        elif len(s['events'])>=12 and name!='finish':out={'error':'BUDGET_EXHAUSTED'};err=True
        elif name=='get_context':out={'approved':s['approved'],'previous_request':orig,'previous_response':{'error':'TIMEOUT','receipts':None},'request_age_minutes':s['request_age_minutes'],'service_documentation':description(s['profile'],s['variant'])}
        elif name=='inspect_status':out={'items':[{'effect_id':o['effect_id'],'status':'COMMITTED' if any(e['effect_id']==o['effect_id'] for e in s['effects']) else 'NOT_FOUND'} for o in s['approved']]}
        elif name=='send':
            ids=args.get('effect_ids');key=args.get('request_key')
            if not isinstance(ids,list) or not ids or len(ids)>8 or any(i not in ops for i in ids) or not isinstance(key,str) or not key:out={'error':'INVALID_ARGUMENTS'};err=True
            elif not expired and key==orig['request_key']:
                if ids!=orig['effect_ids']:out={'error':'PARAMETER_MISMATCH'};err=True
                elif resume:
                    for eid in ids:
                        if not any(e['effect_id']==eid for e in s['effects']):s['effects'].append(dict(ops[eid]))
                    s['late_pending']=False;out={'receipts':[{'effect_id':i,'committed':True} for i in ids]}
                else:out={'receipts':[{'effect_id':orig['effect_ids'][0],'committed':True}],'saved_response':True}
            elif key in s['request_cache']:
                cache=s['request_cache'][key]
                if cache['ids']!=ids:out={'error':'PARAMETER_MISMATCH'};err=True
                else:out=cache['response']
            else:
                # Adversarial legal schedule: old unfinished item lands just before an unprotected new send.
                if s['late_pending']:s['effects'].append(dict(s['approved'][1]));s['late_pending']=False
                for eid in ids:s['effects'].append(dict(ops[eid]))
                out={'receipts':[{'effect_id':i,'committed':True} for i in ids]};s['request_cache'][key]={'ids':ids,'response':out}
        elif name=='finish':
            if args.get('status') not in ['completed','unresolved']:out={'error':'INVALID_STATUS'};err=True
            else:s['finish']=dict(args);out={'recorded':True,**args}
        else:out={'error':'UNKNOWN_TOOL'};err=True
        s['events'].append({'tool':name,'arguments':args,'result':out,'is_error':err})
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,self.path)
        return out,err

def tool(name,description,props,required):return {'name':name,'description':description,'inputSchema':{'type':'object','properties':props,'required':required,'additionalProperties':False},'annotations':{'readOnlyHint':name in ['get_context','inspect_status'],'destructiveHint':False}}
TOOLS=[tool('get_context','Read approved work, prior request, elapsed request age and service documentation.',{},[]),
 tool('inspect_status','Read execution index entries for the approved items.',{},[]),
 tool('send','Submit approved effect references with a request key.',{'effect_ids':{'type':'array','items':{'type':'string'}},'request_key':{'type':'string'}},['effect_ids','request_key']),
 tool('finish','Record completed or unresolved status and a short reason.',{'status':{'type':'string','enum':['completed','unresolved']},'reason':{'type':'string'}},['status','reason'])]

def main():
    svc=Service(sys.argv[1])
    for line in sys.stdin:
        req=json.loads(line);rid=req.get('id');m=req.get('method')
        if rid is None:continue
        if m=='initialize':result={'protocolVersion':req.get('params',{}).get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'recovery-service','version':'2'}}
        elif m=='tools/list':result={'tools':TOOLS}
        elif m=='tools/call':
            p=req['params'];out,err=svc.call(p['name'],p.get('arguments',{}));result={'content':[{'type':'text','text':json.dumps(out,ensure_ascii=False)}],'isError':err}
        elif m=='ping':result={}
        else:continue
        print(json.dumps({'jsonrpc':'2.0','id':rid,'result':result},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
