#!/usr/bin/env python3
"""One fixed 3-event x 3-solver gate, whole includes the independent check.

Only the saved old plan is supplied; controls/other results are evaluation only.
Workers are serial with 2 CPU / 4 GiB AS / 60s whole, no parameter sweeps.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import repair

ROOT=Path(__file__).resolve().parent
PYTHON=sys.executable
REPO=ROOT.parents[1]
INSTANCE=REPO/'source/hoffman1993-large_instance_3.json'
OLD_PLAN=REPO/'results/2026-11-21/v3/seed1/large3/solution.json'
CONTROL=ROOT/'controls.py'
STATE=None
RESULTS=None
CPUS=sorted(os.sched_getaffinity(0))[:2]
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}

def dump(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def limits():
    os.setsid()
    os.sched_setaffinity(0,CPUS)
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(130,130))


def one(solver,event):
    folder=RESULTS/event/solver
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/'result.json'
    args=[PYTHON,'-B',str(ROOT/'method.py') if solver=='method' else str(CONTROL)]
    if solver!='method': args+=['--solver',solver]
    args+=['--instance',str(INSTANCE),'--old-plan',str(OLD_PLAN),
           '--event',str(ROOT/(event+'.json')),'--output',str(output),'--time-limit','55','--seed','1']
    began=time.monotonic()
    with (folder/'stdout.log').open('w') as out,(folder/'stderr.log').open('w') as err:
        child=subprocess.Popen(args,cwd=ROOT,env=ENV,stdout=out,stderr=err,preexec_fn=limits)
        try:
            code=child.wait(timeout=60)
            killed=False
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL); code=child.wait(); killed=True
    solver_whole=time.monotonic()-began
    record={'event':event,'solver':solver,'exit_code':code,'hard_timeout':killed,
            'solver_process_whole_seconds':solver_whole,'cpus':CPUS,'address_space_limit_bytes':4*1024**3,
            'result_written':output.exists(),'whole_feasible':False}
    if not output.exists():
        record['failure']='worker_result_missing'
    if output.exists():
        result=json.loads(output.read_text())
        record.update(D=result.get('removed_old_count'),cost=result.get('actual_cost'),
                      primary=result['primary']['status'],primary_bound=result['primary'].get('best_bound',result['primary'].get('lower_bound')),
                      primary_seconds=result['primary'].get('seconds',result['primary'].get('search_seconds')),
                      secondary=result['secondary']['status'],secondary_bound=result['secondary'].get('best_bound'),
                      secondary_seconds=result['secondary'].get('seconds'),lexicographic_complete=result.get('lexicographic_complete',False),
                      failure=result.get('failure'))
        solution=result.get('solution')
        if solution is not None:
            data,old,ev=repair.read_contract(INSTANCE,OLD_PLAN,ROOT/(event+'.json'))
            witness=repair.check(data,old,ev,solution['selected_rotations'])
            assert solution==repair.make_solution(data,solution['selected_rotations'])
            assert record['D']==witness['removed_old_count'] and record['cost']==witness['recomputed_cost']
            dump(folder/'solution.json',solution)
            dump(folder/'exact-check.json',witness)
            command=[PYTHON,'-B',str(ROOT/'official_check.py'),'--instance_path',str(INSTANCE),
                     '--solution_path',str(folder/'solution.json'),'--result_path',str(folder/'official-check.json')]
            remaining=max(.001,60-(time.monotonic()-began))
            try:
                with (folder/'official-check.log').open('w') as log:
                    checked=subprocess.run(command,cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT,
                                           timeout=remaining,preexec_fn=limits)
                official=json.loads((folder/'official-check.json').read_text())
                record['official_checker_exit']=checked.returncode
                record['whole_feasible']=code==0 and not killed and checked.returncode==0 and official['feasible']
                if not record['whole_feasible']:
                    record['failure']='declared_solution_failed_complete_gate'
            except subprocess.TimeoutExpired:
                record['checker_timeout']=True
    record['whole_seconds']=time.monotonic()-began
    record['resource_pass']=not killed and record['whole_seconds']<=60.0
    dump(folder/'run.json',record)
    return record


def main():
    global STATE,RESULTS,CONTROL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,help='temporary output folder; run from the repository root')
    parser.add_argument('--initial-scip-adapter',action='store_true',help='reproduce the archived same-instance SCIP interruption')
    args=parser.parse_args()
    folder=Path(args.out).resolve(); folder.mkdir(parents=True,exist_ok=True)
    STATE=folder/'state.json'; RESULTS=folder/'runs'
    if args.initial_scip_adapter: CONTROL=ROOT/'executed-controls-initial.py'
    state={'phase':'RUNNING','pid':os.getpid(),'cases':[],'started_at_epoch':time.time()}
    dump(STATE,state)
    for event in ('E1','E2','E3'):
        for solver in ('cpsat','scip','method'):
            state['active']={'event':event,'solver':solver}
            dump(STATE,state)
            try:
                record=one(solver,event)
            except (ValueError, AssertionError, KeyError, json.JSONDecodeError) as error:
                record={'solver':solver,'event':event,'resource_pass':False,'whole_feasible':False,
                        'failure':type(error).__name__+': '+str(error)}
            state['cases'].append(record); dump(STATE,state)
            print(json.dumps(record,allow_nan=False),flush=True)
            if record.get('failure') or not record['resource_pass']:
                state.update(phase='STOPPED_EXECUTION_FAILURE',active=None)
                dump(STATE,state)
                return 2
    state.update(phase='COMPLETE_ALL_FIXED_CASES',active=None,finished_at_epoch=time.time())
    dump(STATE,state)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
