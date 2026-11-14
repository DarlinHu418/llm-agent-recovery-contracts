"""Offline only: no online runner entry points, credentials or external notifications."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=ROOT/'SHA256SUMS.json'
 if manifest.exists():
  for name,h in json.loads(manifest.read_text(encoding='utf-8')).items():assert sha(ROOT/name)==h,name
 for stage in ['live_experiment','contract_recovery','contract_boundaries']:
  proto=json.loads((ROOT/stage/'protocol.json').read_text(encoding='utf-8'))
  for name,h in proto['source_sha256'].items():assert sha(ROOT/stage/name)==h,(stage,name)
 commands=[('live_experiment',['test_experiment.py']),('live_experiment',['analyze.py']),('live_experiment',['audit_measurement.py']),('contract_recovery',['run.py','check']),('contract_recovery',['analyze.py']),('contract_boundaries',['run.py','check']),('contract_boundaries',['analyze.py'])]
 log=[]
 for stage,args in commands:
  command=[sys.executable,str(ROOT/'scripts'/'offline_bootstrap.py'),*args] if sys.platform=='win32' else [sys.executable,*args]
  p=subprocess.run(command,cwd=ROOT/stage,capture_output=True,text=True,encoding='utf-8',errors='replace')
  record={'directory':stage,'command':['python',*args],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
  log.append(record);print(stage+'/'+args[0]+': '+('passed' if p.returncode==0 else 'FAILED'),flush=True)
  if p.returncode:print(p.stderr);break
 all_ok=len(log)==len(commands) and all(x['returncode']==0 for x in log)
 result={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'offline_only':True,'all_passed':all_ok,'checks':log}
 out=ROOT/'verification'/'latest.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 assert all_ok,'Offline checks failed; see verification/latest.json'
 p=ROOT/'report'/'provenance.json';info=json.loads(p.read_text(encoding='utf-8'));assert sha(ROOT/info.get('final_report_path','report/final_report.pdf'))==info['final_report_sha256']
 print('All seven checks passed; author final report hash verified.')
if __name__=='__main__':main()
