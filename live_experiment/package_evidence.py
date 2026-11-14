from pathlib import Path
import hashlib,json,re,zipfile

ROOT=Path(__file__).parent

def main():
    files=['experiment.py','notification_service.py','agent_instructions.txt','followup.py',
      'test_experiment.py','analyze.py','protocol.json','followup_protocol.json','results.json',
      'results.csv','followup_results.json','analysis.json','evaluator_disagreements.csv',
      'README.md','实验结果报告.md','package_evidence.py']
    entries={name:ROOT/name for name in files}
    for phase,count in [('runs',24),('followup_runs',8)]:
        folders=sorted((ROOT/phase).glob('*/run.json'));assert len(folders)==count
        for meta in folders:
            for name in ['state.json','run.json','prompt.txt','command.json','public_events.jsonl','answer.txt','stderr.log']:
                path=meta.parent/name;assert path.exists(),path
                entries[path.relative_to(ROOT).as_posix()]=path
    third=ROOT.parent/'gap_audit'/'third_party'/'idempotencybench'
    for name in ['world.py','tasks.py','LICENSE','PROVENANCE.json']:
        entries['third_party/idempotencybench/'+name]=third/name
    # No credentials are sourced; this check avoids accidentally packaging a log containing one.
    sensitive=re.compile(rb'(?i)(?:Bearer\s+[A-Za-z0-9._-]{20,}|sk-[A-Za-z0-9_-]{20,}|"(?:access_token|refresh_token|OPENAI_API_KEY)"\s*:\s*"[^"\s]{8,}")')
    for name,path in entries.items():
        assert not sensitive.search(path.read_bytes()),'Potential credential in '+name
    digests={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(entries.items())}
    manifest=ROOT/'SHA256SUMS.json';manifest.write_text(json.dumps(digests,ensure_ascii=False,indent=2),encoding='utf-8')
    entries[manifest.name]=manifest
    out=ROOT/'真实Agent恢复实验_源码与32会话证据.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,path in sorted(entries.items()):z.write(path,name)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(entries)
    print(json.dumps({'zip':str(out),'files':len(entries),'bytes':out.stat().st_size,
      'sha256':hashlib.sha256(out.read_bytes()).hexdigest()},ensure_ascii=False))

if __name__=='__main__':main()
