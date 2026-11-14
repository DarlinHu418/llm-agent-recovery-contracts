"""Prepare a separate fresh experiment copy; never launches a model."""
from pathlib import Path
import argparse,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--codex',required=True);a=p.parse_args()
 target=Path(a.output).resolve();cli=Path(a.codex).resolve()
 assert cli.is_file(),'Provide the installed executable path'
 assert not target.exists(),'Use a new, nonexistent output directory'
 assert not target.is_relative_to(ROOT/'live_experiment') and not target.is_relative_to(ROOT/'contract_recovery') and not target.is_relative_to(ROOT/'contract_boundaries')
 files={'live_experiment':['experiment.py','notification_service.py','agent_instructions.txt','followup.py','analyze.py','audit_measurement.py','test_experiment.py','README.md'],'contract_recovery':['run.py','service.py','instructions.txt','analyze.py','README.md'],'contract_boundaries':['run.py','service.py','instructions.txt','analyze.py','retry_infra.py','README.md']}
 for stage,names in files.items():
  (target/stage).mkdir(parents=True,exist_ok=True)
  for name in names:shutil.copy2(ROOT/stage/name,target/stage/name)
 source=target/'live_experiment'/'experiment.py';text=source.read_text(encoding='utf-8');lines=text.splitlines();match=[i for i,x in enumerate(lines) if x.startswith('BIN=Path(')];assert len(match)==1
 lines[match[0]]='BIN=Path('+repr(str(cli))+')';source.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('Fresh copies prepared at',target);print('No model calls were made. Run pilot and then main to generate new protocols.')
if __name__=='__main__':main()
