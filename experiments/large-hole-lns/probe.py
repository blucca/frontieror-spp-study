#!/usr/bin/env python3
"""Six-second complete incumbent-preserving Python LNS initialization probe."""
import time
START=time.monotonic()
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('spp',Path(__file__).resolve().parent/'main/solve.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def main():
    args=s.cli_args();data=s.read_instance(args.instance);n,m,k,_=s.dimensions(data);cols,costs=data['constraint_matrix_A']['columns'],data['cost_vector'];canonical={}
    assert k==0 and all(c>0 for c in costs)
    for j,rows in enumerate(cols):
        key=tuple(rows)
        if rows and (key not in canonical or costs[j]<costs[canonical[key]]):canonical[key]=j
    ordered=sorted(canonical.values(),key=lambda j:(costs[j]/len(cols[j]),-len(cols[j]),j))
    best,cold=s.bitset_probe(data,ordered,min(START+6,time.monotonic()+2),args.seed)
    if best is None: print(json.dumps({'probe_status':'NO_COLD_COVER','cold':cold}),flush=True);return 2
    cold_cost=s.cost(data,best)
    best,lns=s.lns_cover(data,best,ordered,START+6,args.seed)
    solution=s.write_solution(data,best,args.output)
    metrics={'method':'6s pure-Python incumbent-preserving large-hole LNS initialization','seed':args.seed,'probe_budget_seconds':6,'objective':solution['objective_value'],'cold_objective':cold_cost,'cold':cold,'lns':lns,'internal_seconds':time.monotonic()-START}
    print(json.dumps({'metrics':metrics}),flush=True);return 0
if __name__=='__main__':sys.exit(main())
