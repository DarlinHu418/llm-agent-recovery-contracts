"""Windows host I/O compatibility for offline checks; frozen sources stay untouched."""
from pathlib import Path
import os,runpy,sys,time
count=0
if os.name=='nt':
 original=os.replace
 def replace(source,destination,*args,**kwargs):
  global count
  for attempt in range(11):
   try:return original(source,destination,*args,**kwargs)
   except PermissionError as e:
    if getattr(e,'winerror',None)!=5 or attempt==10:raise
    count+=1;time.sleep(.05)
 os.replace=replace
script=Path(sys.argv[1]).resolve();sys.argv=[str(script),*sys.argv[2:]]
sys.path.insert(0,str(script.parent))
try:runpy.run_path(str(script),run_name='__main__')
finally:
 if count:print('Windows offline host file replacement retries: '+str(count),file=sys.stderr)
