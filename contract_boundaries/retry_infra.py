from datetime import datetime,timezone
import json
from run import ROOT,execute

def main():
    rows=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))
    retries=[]
    for row in rows:
        if row['valid']:continue
        events=[json.loads(l) for l in (ROOT/'runs'/f"e{row['episode']:02d}"/'public_events.jsonl').read_text(encoding='utf-8').splitlines()]
        transport=any('stream disconnected' in json.dumps(e) for e in events)
        if transport:
            retries.append({'episode':row['episode'],'profile':row['profile'],'variant':row['variant'],
              'reason':'Transport stream failure; original episode preserved and excluded from valid primary denominator. One repeat on identical condition; no scoring or task changes.'})
    protocol={'declared_utc':datetime.now(timezone.utc).isoformat(),'status':'Post-main infrastructure-retry protocol, not part of original preregistration','retries':retries}
    f=ROOT/'retry_protocol.json'
    if not f.exists():f.write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in retries:print(json.dumps(execute(r['profile'],r['variant'],r['episode'],'replacement_runs'),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
