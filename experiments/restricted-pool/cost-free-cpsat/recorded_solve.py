#!/usr/bin/env python3
"""One 6s cost-free CP-SAT density-pool feasibility probe; all original rows."""
import time
START=time.monotonic()
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('p','/data/workspace/temp/round711-frontier-submip-probe/solve.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
s=p.s

def main():
    args=s.cli_args();data=s.read_instance(args.instance)
    n,m,k,_=s.dimensions(data)
    assert k==0 and all(c>0 for c in data['cost_vector'])
    costs,cols=data['cost_vector'],data['constraint_matrix_A']['columns'];canonical={}
    for j,rows in enumerate(cols):
        key=tuple(rows)
        if rows and (key not in canonical or costs[j]<costs[canonical[key]]):canonical[key]=j
    ordered=sorted(canonical.values(),key=lambda j:(costs[j]/len(cols[j]),-len(cols[j]),j))
    pool,pm=s.density_pool(data,ordered)
    import ortools
    from ortools.sat.python import cp_model
    model=cp_model.CpModel(); x=[model.new_bool_var(f'x{q}') for q in range(len(pool))]; rows=[[] for _ in range(n)]
    for q,j in enumerate(pool):
        for r in cols[j]:rows[r].append(x[q])
    for row in rows:model.add_exactly_one(row)
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=2;solver.parameters.random_seed=args.seed;solver.parameters.max_memory_in_mb=4096
    solver.parameters.max_time_in_seconds=max(.001,START+min(6,args.time_limit-5)-time.monotonic()-.15)
    build=time.monotonic()-START; status=solver.solve(model)
    metrics={'method':'first-stage cost-free CP-SAT density-pool feasibility','probe_budget_seconds':6,'pool':pm,'seed':args.seed,'threads':2,'solver_version':ortools.__version__,'model_scope':'density_restricted_all_original_rows','model_columns':len(pool),'model_rows':n,'model_status':solver.status_name(status),'model_build_seconds':build,'search_seconds':solver.wall_time,'branches':solver.num_branches,'conflicts':solver.num_conflicts,'response_stats':solver.response_stats()}
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        metrics.update(probe_status='NO_COVER',objective=None,internal_seconds=time.monotonic()-START);print(json.dumps({'metrics':metrics}),flush=True);return 2
    chosen=[pool[q] for q in range(len(pool)) if solver.value(x[q])]
    solution=s.write_solution(data,chosen,args.output)
    metrics.update(probe_status='FEASIBLE',objective=solution['objective_value'],selected_count=len(chosen),internal_seconds=time.monotonic()-START);print(json.dumps({'metrics':metrics}),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
