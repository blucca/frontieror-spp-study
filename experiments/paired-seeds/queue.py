#!/usr/bin/env python3
"""One fixed serial seed experiment; reuse the already measured full-native checker."""
import importlib.util, json, os
from pathlib import Path
import resource, signal, subprocess, sys, time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'temp/paired-seeds'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('controller', HERE/'controller.py')
c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
CASES={'tiny':'tiny_instance','large2':'large_instance_2','large3':'large_instance_3'}
RUNS=[('main',2,'tiny'),('main',2,'large2'),('main',2,'large3'),('highs',2,'large3'),('main',3,'large3'),('highs',3,'large3')]
assert len(RUNS)==6 and sum(name=='large3' for _,_,name in RUNS)==4
start=time.monotonic(); state={'status':'RUNNING','pid':os.getpid(),'runs':[], 'extra_cpu_budget_seconds':1200,'whole_instance_limit_seconds':60,'paired_seeds':[1,2,3],'seed1_source':'round710 frozen original; retained, not rerun'}
c.dump(OUT/'state.json',state)
for algorithm,seed,name in RUNS:
    if resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime>1200:
        state.update(status='STOP',failure='additional CPU budget reached'); break
    out=OUT/'results'/f'seed{seed}'/algorithm/name; out.mkdir(parents=True,exist_ok=True)
    script=HERE/('main/solve.py' if algorithm=='main' else 'eligible-baseline/highs_baseline.py')
    state['current']={'algorithm':algorithm,'seed':seed,'instance':name}; c.dump(OUT/'state.json',state)
    cmd=[sys.executable,'-B',str(HERE/'controller.py'),'run','--root',str(ROOT),'--out',str(out),'--algorithm',algorithm,'--instance',str(ROOT/'source'/f'hoffman1993-{CASES[name]}.json'),'--script',str(script),'--seed',str(seed)]
    began=time.monotonic()
    with (out/'worker.stdout.log').open('w') as log,(out/'worker.stderr.log').open('w') as err:
        p=subprocess.Popen(cmd,stdout=log,stderr=err,env=c.environment(ROOT),preexec_fn=c.bounded,start_new_session=True)
        try:p.wait(timeout=60)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    wall=time.monotonic()-began
    rec=json.loads((out/'run.json').read_text()) if (out/'run.json').exists() else {}
    rec.update(instance_name=name,external_end_to_end_seconds=wall,worker_exit_code=p.returncode)
    if p.returncode or wall>=60 or rec.get('status')!='PASS':
        state.update(status='STOP',failure=rec.get('failure','whole native/checker or resource gate failed'))
    state['runs'].append(rec);c.dump(out/'run.json',rec);c.dump(OUT/'state.json',state)
    print(json.dumps({'algorithm':algorithm,'seed':seed,'instance':name,'status':rec.get('status'),'objective':rec.get('objective'),'wall':wall}),flush=True)
    if state['status']!='RUNNING':break
if state['status']=='RUNNING':state['status']='DONE'
state.update(wall_seconds=time.monotonic()-start,cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime)
c.dump(OUT/'state.json',state)
