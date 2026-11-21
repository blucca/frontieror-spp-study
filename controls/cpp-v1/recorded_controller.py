#!/usr/bin/env python3
"""One authorized native cold run; bounded worker and full exact/original checks."""
import json, os, pathlib, resource, signal, subprocess, sys, time
root = pathlib.Path('/data/workspace/temp/round710/frontier-spp')
method = root/'method'
out = method/'formal-v1'/'large3-seed1'
out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'shared'))
from spp_io import bounded_child, dump
cmd = [sys.executable,'-B',str(root/'shared'/'spp_io.py'),'run','--solver','native',
       '--instance',str(root/'source'/'hoffman1993-large_instance_3.json'),
       '--out',str(out),'--executable',str(method/'solver-formal-v1'),
       '--limit','55','--seed','1','--checker',str(root/'source'/'hoffman1993-feasibility_check.py'),
       '--checker-python','/usr/bin/python3']
env = dict(os.environ,OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',
           NUMEXPR_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1')
state = {'status':'STARTED','pid':os.getpid(),'command':cmd,'external_budget_seconds':60,
         'search_budget_seconds':55,'seed':1,'cpu_affinity':[0,1],
         'per_process_ram_bytes':4*1024**3,'cold_reference_files_present':False}
dump(out/'controller.json',state)
began=time.monotonic()
with (out/'worker.stdout.log').open('w') as log, (out/'worker.stderr.log').open('w') as err:
 p=subprocess.Popen(cmd,stdout=log,stderr=err,env=env,preexec_fn=bounded_child,start_new_session=True)
 try: p.wait(timeout=60)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);p.wait();state['failure']='instance wall budget exceeded'
elapsed=time.monotonic()-began
record=json.loads((out/'run.json').read_text()) if (out/'run.json').exists() else {}
record.update({'instance_name':'large3','external_end_to_end_seconds':elapsed,'worker_exit_code':p.returncode})
state.update({'external_end_to_end_seconds':elapsed,'worker_exit_code':p.returncode})
if p.returncode==0 and elapsed<=60 and record.get('status')=='PASS' and record.get('max_rss_kib',0)<=4*1024**2:
 state['status']='PASS'
else:
 state['status']='STOP';state.setdefault('failure',record.get('failure','resource or solver/checker gate failed'))
record['status']=state['status']
dump(out/'run.json',record);dump(out/'controller.json',state)
print(json.dumps({'status':state['status'],'objective':record.get('objective'),
                  'external_end_to_end_seconds':elapsed,'cpu_user_seconds':record.get('cpu_user_seconds'),
                  'cpu_system_seconds':record.get('cpu_system_seconds'),'max_rss_kib':record.get('max_rss_kib'),
                  'metrics':record.get('metrics')},allow_nan=False),flush=True)
sys.exit(0 if state['status']=='PASS' else 2)
