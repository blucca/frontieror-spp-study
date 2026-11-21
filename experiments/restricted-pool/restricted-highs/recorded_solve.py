#!/usr/bin/env python3
"""Experimental first-stage density-restricted MIP cover, not a full-time Main candidate."""
import time
START=time.monotonic()
import importlib.util,json,sys
from pathlib import Path
ROOT=Path('/data/workspace/temp/round711-frontier-v1-seeds')
spec=importlib.util.spec_from_file_location('spp',ROOT/'main/solve.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

def restricted(data,pool):
    n,m,k,_=s.dimensions(data)
    assert k==0 and len(pool)==len(set(pool)) and all(0<=j<m for j in pool)
    out=dict(data)
    out['dimensions']=dict(data['dimensions'],num_cols=len(pool),num_nonzeroes=sum(len(data['constraint_matrix_A']['columns'][j]) for j in pool))
    out['cost_vector']=[data['cost_vector'][j] for j in pool]
    out['constraint_matrix_A']=dict(data['constraint_matrix_A'],columns=[data['constraint_matrix_A']['columns'][j] for j in pool])
    return out

def main():
    args=s.cli_args();data=s.read_instance(args.instance);n,m,k,_=s.dimensions(data)
    assert k==0 and all(c>0 for c in data['cost_vector'])
    costs,cols=data['cost_vector'],data['constraint_matrix_A']['columns']
    canonical={}
    for j,rows in enumerate(cols):
        key=tuple(rows)
        if rows and (key not in canonical or costs[j]<costs[canonical[key]]):canonical[key]=j
    ordered=sorted(canonical.values(),key=lambda j:(costs[j]/len(cols[j]),-len(cols[j]),j))
    pool,pm=s.density_pool(data,ordered)
    model=restricted(data,pool)
    chosen,hm=s.highs_solve(model,START+min(6.0,args.time_limit-5),seed=args.seed)
    hm['model_scope']='density_restricted_all_original_rows'
    metrics={'method':'first-stage 6s density-pool restricted MIP','seed':args.seed,'pool':pm,'highs':hm,'original_columns':m,'probe_budget_seconds':6,'internal_seconds':time.monotonic()-START}
    if chosen is None:
        metrics.update(probe_status='NO_COVER',objective=None)
        print(json.dumps({'metrics':metrics},allow_nan=False),flush=True)
        return 2
    mapped=[pool[p] for p in chosen]
    assert s.exact_cover(data,mapped),'submodel to original index mapping must preserve full exact cover'
    solution=s.write_solution(data,mapped,args.output)
    metrics.update(probe_status='FEASIBLE',objective=solution['objective_value'],selected_count=len(mapped),internal_seconds=time.monotonic()-START)
    print(json.dumps({'metrics':metrics},allow_nan=False),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
