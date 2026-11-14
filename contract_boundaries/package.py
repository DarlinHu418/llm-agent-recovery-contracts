from pathlib import Path
import json,hashlib,zipfile,re,tempfile,subprocess,sys
R=Path(__file__).parent
files={}
for name in ['run.py','service.py','instructions.txt','analyze.py','protocol.json','retry_infra.py','retry_protocol.json','results.json','results.csv','analysis.json','baseline_results.json','README.md','研究设计与实验结果.md','build_report.py','package.py']:
    files['contract_boundaries/'+name]=R/name
for name in ['experiment.py','notification_service.py']:files['live_experiment/'+name]=R.parent/'live_experiment'/name
for phase in ['runs','replacement_runs']:
    for run in (R/phase).glob('*/run.json'):
        for name in ['run.json','state.json','command.json','prompt.txt','public_events.jsonl','answer.txt','stderr.log']:
            path=run.parent/name
            if path.exists():files['contract_boundaries/'+path.relative_to(R).as_posix()]=path
assert len(list((R/'runs').glob('*/run.json')))==12
secret=re.compile(rb'(?i)(?:Bearer\s+[A-Za-z0-9._-]{20,}|sk-[A-Za-z0-9_-]{20,}|"(?:access_token|refresh_token)"\s*:\s*"[^"\s]{8,}")')
for name,path in files.items():assert path.exists() and not secret.search(path.read_bytes()),name
manifest={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(files.items())}
out=R/'契约边界辨别_完整数据与源码.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for name,path in files.items():z.write(path,name)
    z.writestr('SHA256SUMS.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with tempfile.TemporaryDirectory(dir=R) as tmp:
    root=Path(tmp).resolve()
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for name in z.namelist():assert (root/name).resolve().is_relative_to(root)
        z.extractall(root)
    for name,digest in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    for args in [['run.py','check'],['analyze.py']]:
        result=subprocess.run([sys.executable,*args],cwd=root/'contract_boundaries',capture_output=True,text=True,encoding='utf-8');assert result.returncode==0,result.stderr
print(json.dumps({'zip':str(out),'files':len(files)+1,'bytes':out.stat().st_size,'offline_verification':'passed'},ensure_ascii=False))
