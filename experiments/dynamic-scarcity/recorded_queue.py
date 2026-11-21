#!/usr/bin/env python3
"""The one authorized serial three-seed dynamic scarcity probe gate."""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
RAM=4*1024**3


def dump(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def bounded():
    os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
    resource.setrlimit(resource.RLIMIT_AS,(RAM,RAM))
    resource.setrlimit(resource.RLIMIT_CPU,(20,20))


def main():
    start=time.monotonic()
    state={'status':'RUNNING','pid':os.getpid(),'runs':[],'probe_seconds_per_seed':6,
           'whole_seconds_per_seed':10,'batch_cpu_limit_seconds':60,'seeds':[1,2,3],
           'baseline_retained_not_rerun':{'1':{'status':'FEASIBLE','objective':252,'seconds':4.932,'nodes':572584},
                                          '2':{'status':'TIME_LIMIT','seconds':6,'nodes':648577},
                                          '3':{'status':'TIME_LIMIT','seconds':6,'nodes':637313}}}
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2',
             MKL_NUM_THREADS='2',NUMEXPR_NUM_THREADS='2')
    dump(HERE/'state.json',state)
    for seed in state['seeds']:
        ru=resource.getrusage(resource.RUSAGE_CHILDREN)
        if ru.ru_utime+ru.ru_stime>=60:
            state.update(status='STOP',failure='60 s additional CPU gate');break
        out=HERE/f'seed{seed}';out.mkdir(exist_ok=True)
        state['current_seed']=seed;dump(HERE/'state.json',state)
        command=[sys.executable,'-B',str(HERE/'probe_worker.py'),'--seed',str(seed)]
        began=time.monotonic();timed_out=False
        with (out/'worker.stdout.log').open('w') as log,(out/'worker.stderr.log').open('w') as err:
            child=subprocess.Popen(command,stdout=log,stderr=err,env=env,preexec_fn=bounded,start_new_session=True)
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                timed_out=True;os.killpg(child.pid,signal.SIGKILL);child.wait()
        wall=time.monotonic()-began
        record=json.loads((out/'run.json').read_text()) if (out/'run.json').exists() else {'status':'STOP'}
        record.update(external_wall_seconds=wall,worker_exit_code=child.returncode,external_timeout=timed_out)
        if timed_out or wall>10 or child.returncode or record.get('max_rss_kib',0)>RAM//1024:
            record.update(status='STOP',envelope_status='FAILED',failure='per-process resource/worker gate')
            state.update(status='STOP',failure=record['failure'])
        state['runs'].append(record);dump(out/'run.json',record);dump(HERE/'state.json',state)
        print(json.dumps({'seed':seed,'status':record.get('status'),'objective':record.get('objective'),
                          'probe':record.get('metrics',{}),'whole_seconds':wall}),flush=True)
        if state['status']=='STOP':break
    if state['status']=='RUNNING':state['status']='DONE'
    ru=resource.getrusage(resource.RUSAGE_CHILDREN)
    covers=[r for r in state['runs'] if r.get('status')=='FEASIBLE' and r.get('witness_status')=='PASS']
    state.update(wall_seconds=time.monotonic()-start,cpu_seconds=ru.ru_utime+ru.ru_stime,
                 complete_cover_count=len(covers),primary_method_gate='PASS' if len(covers)>=2 else 'STOP')
    dump(HERE/'state.json',state)
    print(json.dumps({'batch_status':state['status'],'covers':len(covers),'gate':state['primary_method_gate'],
                      'cpu_seconds':state['cpu_seconds']}),flush=True)
    return 0 if state['status']=='DONE' else 2


if __name__=='__main__':sys.exit(main())
