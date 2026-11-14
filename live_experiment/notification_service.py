"""Persistent simulated notification service, driven by a real model over MCP.

Mechanisms differ only in the persistent receipt identity. Errors are injected
after a real local ledger write, before its response. This sends no real email.
The stdio server processes requests serially; no distributed safety claim.
"""
from pathlib import Path
import json,sys,os,time

class Service:
    def __init__(self,path):self.path=Path(path)
    def load(self):return json.loads(self.path.read_text(encoding='utf-8'))
    def save(self,state):
        tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(tmp,self.path)
    def call(self,name,args):
        s=self.load(); s['tool_calls']+=1
        result={};error=False
        approved={x['effect_id']:x for x in s['approved']}
        if s.get('finish'):
            result={'error':'TASK_ALREADY_FINISHED'};error=True
        elif s['tool_calls']>12 and name!='finish':
            result={'error':'TOOL_BUDGET_EXHAUSTED','instruction':'Finish with current status.'};error=True
        elif name=='get_authorizations':
            result={'required_operations':s['approved'],
                    'requirement':'Every listed effect_id is a distinct required occurrence. Identical contents can be required more than once.'}
        elif name=='inspect_receipts':
            result={'receipts':s['effects']}
        elif name=='send_notifications':
            ids=args.get('effect_ids')
            if not isinstance(ids,list) or not ids or len(ids)>10 or any(x not in approved for x in ids):
                result={'error':'INVALID_EFFECT_REFERENCE'};error=True
            else:
                receipts=[]
                for eid in ids:
                    op=approved[eid]
                    fields=['to','subject','body']
                    identity=(eid if s['mechanism']=='authorization_receipt'
                              else json.dumps([op[x] for x in fields],ensure_ascii=False))
                    if identity in s['receipts']:
                        rec=dict(s['receipts'][identity]); rec['replayed']=True
                    else:
                        rec={'receipt_id':'receipt-'+str(len(s['effects'])+1),
                             'effect_id':eid,'authorization_id':op['authorization_id'],
                             **{k:op[k] for k in fields},'committed':True}
                        s['effects'].append(rec)
                        s['receipts'][identity]=rec
                    receipts.append(rec)
                    if s['fault_armed']:
                        s['fault_armed']=False
                        result={'error':'TIMEOUT','message':'The request timed out. No receipt was returned.'}
                        error=True;break
                if not error:result={'receipts':receipts}
        elif name=='finish':
            status=args.get('status')
            missing=args.get('missing_effect_ids',[])
            if status not in ['completed','partial'] or not isinstance(missing,list) or any(x not in approved for x in missing):
                result={'error':'INVALID_FINISH'};error=True
            else:
                s['finish']={'status':status,'missing_effect_ids':missing,'summary':str(args.get('summary',''))[:1200]}
                result={'recorded':True,**s['finish']}
        else:result={'error':'UNKNOWN_TOOL'};error=True
        s['events'].append({'seq':len(s['events'])+1,'time_ns':time.time_ns(),
                            'tool':name,'arguments':args,'result':result,'is_error':error})
        self.save(s)
        return result,error

def tools():
    def obj(properties,required):return {'type':'object','properties':properties,'required':required,'additionalProperties':False}
    return [
      {'name':'get_authorizations','description':'Read the approved required notification operations, their occurrence references and exact content.',
       'inputSchema':obj({},[]),'annotations':{'readOnlyHint':True}},
      {'name':'send_notifications','description':'Send one or more approved notification occurrence references. Returns committed receipt records; a record may have been replayed. Exact content comes from the approval. A timeout does not establish non-execution.',
       'inputSchema':obj({'effect_ids':{'type':'array','items':{'type':'string'},'minItems':1,'maxItems':10}},['effect_ids']),
       'annotations':{'readOnlyHint':False,'destructiveHint':False}},
      {'name':'inspect_receipts','description':'Read all committed notification receipts for this task. Each record includes its original effect_id and authorization_id.',
       'inputSchema':obj({},[]),'annotations':{'readOnlyHint':True}},
      {'name':'finish','description':'Record completion or partial completion and missing occurrence references. This does not send notifications.',
       'inputSchema':obj({'status':{'type':'string','enum':['completed','partial']},
                          'missing_effect_ids':{'type':'array','items':{'type':'string'}},
                          'summary':{'type':'string'}},['status','missing_effect_ids','summary']),
       'annotations':{'readOnlyHint':False,'destructiveHint':False}},
    ]

def main():
    service=Service(sys.argv[1])
    for line in sys.stdin:
        try:
            req=json.loads(line);method=req.get('method');rid=req.get('id')
            if rid is None:continue
            if method=='initialize':
                result={'protocolVersion':req.get('params',{}).get('protocolVersion','2024-11-05'),
                        'capabilities':{'tools':{}},'serverInfo':{'name':'notification-task','version':'1.0.0'}}
            elif method=='tools/list':result={'tools':tools()}
            elif method=='tools/call':
                p=req['params'];out,err=service.call(p['name'],p.get('arguments',{}))
                result={'content':[{'type':'text','text':json.dumps(out,ensure_ascii=False)}],'isError':err}
            elif method=='ping':result={}
            else:
                print(json.dumps({'jsonrpc':'2.0','id':rid,'error':{'code':-32601,'message':'Method not found'}}),flush=True);continue
            print(json.dumps({'jsonrpc':'2.0','id':rid,'result':result},ensure_ascii=False),flush=True)
        except Exception as e:
            print(str(e),file=sys.stderr,flush=True)
            if 'rid' in locals() and rid is not None:
                print(json.dumps({'jsonrpc':'2.0','id':rid,'error':{'code':-32603,'message':type(e).__name__}}),flush=True)

if __name__=='__main__':main()
