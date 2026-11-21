#!/usr/bin/env python3
"""One complete new LS-only/FJ control; all old algorithms and runs are reused."""
import importlib.util,json,os
from pathlib import Path
import resource,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'temp/fj-control'
OUT.mkdir(parents=True,exist_ok=True)
HOLDOUT=ROOT/'source'
spec=importlib.util.spec_from_file_location('c',ROOT/'versions/v3/recorded_controller.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
RUNS=[('tiny',1,ROOT/'source/hoffman1993-tiny_instance.json'),('large2',1,ROOT/'source/hoffman1993-large_instance_2.json'),('base-k2',1,ROOT/'main/base-contract-fixture.json'),('large1',1,HOLDOUT/'hoffman1993-large_instance_1.json'),('large3',1,ROOT/'source/hoffman1993-large_instance_3.json'),('large4',1,HOLDOUT/'hoffman1993-large_instance_4.json'),('large5',1,HOLDOUT/'hoffman1993-large_instance_5.json'),('large3',2,ROOT/'source/hoffman1993-large_instance_3.json'),('large3',3,ROOT/'source/hoffman1993-large_instance_3.json')]
assert len(RUNS)==9 and {name for name,seed,_ in RUNS if seed==1}=={'tiny','large1','large2','large3','large4','large5','base-k2'}
state={'status':'RUNNING','pid':os.getpid(),'runs':[],'cpu_budget_seconds':900,'instance_whole_limit_seconds':60,'original_baselines_reused':True,'cold_input_only':True,'method':'LS-only/FJ enabled'};c.dump(OUT/'state.json',state);start=time.monotonic()
for name,seed,instance in RUNS:
    if resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime>900:
        state.update(status='STOP',failure='additional native CPU budget reached');break
    out=OUT/'results'/f'seed{seed}'/name;out.mkdir(parents=True,exist_ok=True)
    state['current']={'case':name,'seed':seed};c.dump(OUT/'state.json',state)
    cmd=[sys.executable,'-B',str(ROOT/'versions/v3/recorded_controller.py'),'run','--root',str(ROOT),'--out',str(out),'--algorithm','cpsat','--instance',str(instance),'--script',str(ROOT/'eligible-baseline/cpsat_fj_control.py'),'--seed',str(seed)]
    began=time.monotonic()
    with (out/'worker.stdout.log').open('w') as log,(out/'worker.stderr.log').open('w') as err:
        p=subprocess.Popen(cmd,stdout=log,stderr=err,env=c.environment(ROOT),preexec_fn=c.bounded,start_new_session=True)
        try:p.wait(timeout=60)
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    wall=time.monotonic()-began;rec=json.loads((out/'run.json').read_text()) if (out/'run.json').exists() else {}
    rec.update(instance_name=name,external_end_to_end_seconds=wall,worker_exit_code=p.returncode)
    failure_text=(out/'algorithm.stderr.log').read_text() if (out/'algorithm.stderr.log').exists() else ''
    normal_no_cover=rec.get('algorithm_exit_code')==2 and 'cold CP-SAT has no whole feasible solution:' in failure_text
    if normal_no_cover:rec['outcome']='NO_FEASIBLE';rec['native_failure_detail']=failure_text.strip()
    if wall>=60 or rec.get('affinity')!=[0,1] or rec.get('ram_limit_bytes')!=4*1024**3 or (rec.get('status')!='PASS' and not normal_no_cover):
        state.update(status='STOP',failure=rec.get('failure','whole native/checker/resource gate failed'))
    state['runs'].append(rec);c.dump(out/'run.json',rec);c.dump(OUT/'state.json',state)
    print(json.dumps({'case':name,'seed':seed,'status':rec.get('status'),'outcome':rec.get('outcome'),'objective':rec.get('objective'),'wall':wall}),flush=True)
    if state['status']!='RUNNING':break
if state['status']=='RUNNING':state['status']='DONE_WITH_NEGATIVE_RESULTS' if any(r.get('outcome')=='NO_FEASIBLE' for r in state['runs']) else 'DONE'
state.update(wall_seconds=time.monotonic()-start,cpu_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime)
c.dump(OUT/'state.json',state)
