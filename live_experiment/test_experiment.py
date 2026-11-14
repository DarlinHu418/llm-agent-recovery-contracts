from pathlib import Path
import json,tempfile,subprocess,sys,copy
from experiment import ROOT,initial,score
from notification_service import Service

def main():
    checks=0
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        p=Path(td)/'state.json'
        for mechanism in ['content_receipt','authorization_receipt']:
            state=initial('partial_distinct_recipients',mechanism,0)
            p.write_text(json.dumps(state),encoding='utf-8')
            svc=Service(p);ids=[x['effect_id'] for x in state['approved']]
            out,error=svc.call('send_notifications',{'effect_ids':ids})
            assert error and len(svc.load()['effects'])==1;checks+=1
            # A fresh service instance must observe the committed effect.
            svc=Service(p);out,error=svc.call('send_notifications',{'effect_ids':ids})
            assert not error and len(svc.load()['effects'])==2;checks+=1
            svc.call('finish',{'status':'completed','missing_effect_ids':[],'summary':'verified'})
            result=score(svc.load());assert result['authorized_resolved_exact'];checks+=1
            bad=svc.load();bad['effects'][0]['body']='not the approved content'
            assert score(bad)['binding_errors']==1 and not score(bad)['authorized_exact'];checks+=1
            state=initial('new_approval_same_content',mechanism,0)
            p.write_text(json.dumps(state),encoding='utf-8');svc=Service(p)
            svc.call('send_notifications',{'effect_ids':[x['effect_id'] for x in state['approved']]})
            result=score(svc.load())
            assert result['native_accept']==(mechanism=='content_receipt');checks+=1
            assert result['authorized_exact']==(mechanism=='authorization_receipt');checks+=1
        p.write_text(json.dumps(initial('single_clean','authorization_receipt',0)),encoding='utf-8')
        wire=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05'}},
              {'jsonrpc':'2.0','method':'notifications/initialized'},
              {'jsonrpc':'2.0','id':2,'method':'tools/list'},
              {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'get_authorizations','arguments':{}}}]
        r=subprocess.run([sys.executable,str(ROOT/'notification_service.py'),str(p)],
              input='\n'.join(json.dumps(x) for x in wire)+'\n',capture_output=True,text=True,encoding='utf-8',timeout=10)
        replies=[json.loads(x) for x in r.stdout.splitlines()]
        assert r.returncode==0 and [x['id'] for x in replies]==[1,2,3];checks+=1
        assert len(replies[1]['result']['tools'])==4;checks+=1
    print(json.dumps({'meaningful_checks':checks,'status':'passed'}))
if __name__=='__main__':main()
