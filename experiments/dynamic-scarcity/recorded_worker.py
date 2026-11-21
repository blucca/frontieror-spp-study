#!/usr/bin/env python3
"""One authorized probe-only 6 s gate; full witness checks if a cover is found."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = Path('/data/workspace/temp/round710/frontier-spp')


def dump(path, data):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    tmp.replace(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,required=True)
    args=parser.parse_args()
    assert args.seed in (1,2,3)
    started=time.monotonic()
    out=HERE/f'seed{args.seed}'
    out.mkdir(parents=True,exist_ok=True)
    instance=BASE/'source/hoffman1993-large_instance_3.json'
    record={'status':'STARTED','instance':str(instance),'seed':args.seed,'probe_seed':104729*args.seed,
            'probe_limit_seconds':6,'outer_limit_seconds':10,'affinity':sorted(os.sched_getaffinity(0)),
            'ram_limit_bytes':resource.getrlimit(resource.RLIMIT_AS)[0],
            'candidate_sha256':hashlib.sha256((HERE/'dynamic-solve.py').read_bytes()).hexdigest(),
            'input_sha256':hashlib.sha256(instance.read_bytes()).hexdigest(),
            'reference_input':False,'solver_lp_mip_calls':0}
    dump(out/'run.json',record)
    try:
        spec=importlib.util.spec_from_file_location('dynamic_solve',HERE/'dynamic-solve.py')
        solver=importlib.util.module_from_spec(spec);spec.loader.exec_module(solver)
        data=solver.read_instance(instance)
        n,m,k,_=solver.dimensions(data)
        assert (n,m,k)==(100,15000,0)
        costs,cols=data['cost_vector'],data['constraint_matrix_A']['columns']
        canonical={}
        for j,rows in enumerate(cols):
            if not rows: continue
            key=tuple(rows)
            if key not in canonical or costs[j]<costs[canonical[key]]:
                canonical[key]=j
        ordered=sorted(canonical.values(),key=lambda j:(costs[j]/len(cols[j]),-len(cols[j]),j))
        pool,pool_info=solver.density_pool(data,ordered)
        assert len(ordered)==14970 and len(pool)==1706
        record.update(pool=pool_info,rows=n,original_columns=m,canonical_columns=len(ordered),cutoff='infinity')
        probe_call=time.monotonic()
        chosen,metrics=solver.bitset_probe(data,pool,probe_call+6,104729*args.seed,math.inf)
        record.update(search_status=metrics['status'],metrics=metrics,probe_including_bitset_build_seconds=time.monotonic()-probe_call)
        dump(out/'raw.json',{'selected_rotations':chosen,'metrics':metrics})
        if chosen is None:
            assert metrics['status'] in ('TIME_LIMIT','EXHAUSTED','EMPTY_ROW')
            record.update(status=metrics['status'],witness_status='NOT_APPLICABLE',envelope_status='PASS')
        else:
            solution=solver.write_solution(data,chosen,out/'solution.json')
            upper=pool_info['density_threshold']*n
            record.update(objective=solution['objective_value'],selected_count=len(chosen),input_cost_upper_bound=upper)
            assert solution['objective_value'] <= upper+1e-9
            spec=importlib.util.spec_from_file_location('spp_io',BASE/'shared/spp_io.py')
            helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
            checked=helper.exact(instance,solution)
            dump(out/'exact-check.json',checked)
            assert checked['feasible']
            with (out/'official-checker.log').open('w') as log:
                check=subprocess.run([sys.executable,'-B',str(BASE/'source/hoffman1993-feasibility_check.py'),
                                      '--instance_path',str(instance),'--solution_path',str(out/'solution.json'),
                                      '--result_path',str(out/'official-check.json')],stdout=log,stderr=subprocess.STDOUT,
                                     timeout=max(.01,9.5-(time.monotonic()-started)))
            official=json.loads((out/'official-check.json').read_text())
            assert check.returncode==0 and official.get('feasible',False)
            record.update(status='FEASIBLE',witness_status='PASS',envelope_status='PASS',
                          independent_exact_feasible=True,official_numpy_feasible=True,
                          full_variable_count=len(solution['variable_values']),output_bytes=(out/'solution.json').stat().st_size)
    except Exception as error:
        record.update(status='STOP',failure=type(error).__name__+': '+str(error),envelope_status='FAILED')
    record['worker_wall_seconds']=time.monotonic()-started
    own,children=resource.getrusage(resource.RUSAGE_SELF),resource.getrusage(resource.RUSAGE_CHILDREN)
    record.update(cpu_user_seconds=own.ru_utime+children.ru_utime,cpu_system_seconds=own.ru_stime+children.ru_stime,
                  max_rss_kib=max(own.ru_maxrss,children.ru_maxrss))
    dump(out/'run.json',record)
    print(json.dumps(record,allow_nan=False),flush=True)
    return 0 if record['envelope_status']=='PASS' else 2


if __name__=='__main__':sys.exit(main())
