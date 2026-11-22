#!/usr/bin/env python3
"""Cold complete LP certificate + incumbent-preserving dual-guided exact cover.

Fixed positive Python-int K0 pathway. General Base/real-cost uses frozen v3.
Own source modules only; all decisions use the original instance and live best.
"""
import json
import math
import time
import original_v3 as base
from dual_lp import integer_dual
from dual_search import dual_lns
ORIGINAL_SOLVE = base.solve


def full_lp(data, deadline):
    begin = time.monotonic()
    import highspy
    import numpy as np
    n, m, k, _ = base.dimensions(data)
    assert k == 0 and all(type(c) is int and c > 0 for c in data['cost_vector'])
    lp = highspy.HighsLp(); lp.num_col_, lp.num_row_ = m, n
    lp.col_cost_ = np.asarray(data['cost_vector'], dtype=np.float64)
    lp.col_lower_, lp.col_upper_ = np.zeros(m), np.full(m, highspy.kHighsInf)
    lp.row_lower_, lp.row_upper_ = np.ones(n), np.ones(n)
    starts, indices = [0], []
    for rows in data['constraint_matrix_A']['columns']:
        indices.extend(rows); starts.append(len(indices))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_, lp.a_matrix_.index_ = np.asarray(starts,dtype=np.int32), np.asarray(indices,dtype=np.int32)
    lp.a_matrix_.value_ = np.ones(len(indices))
    h = highspy.Highs(); h.setOptionValue('output_flag',False); h.setOptionValue('threads',2)
    seconds = max(.001, min(2.0, deadline-time.monotonic()-1.0))
    h.setOptionValue('time_limit', seconds)
    assert h.passModel(lp) != highspy.HighsStatus.kError
    h.startSolve(); done, run_status = h.wait(seconds)
    if not done:
        # Same actual native-overrun contract as v3: no live solver reads.
        raise base.HighsDeadline({'stage':'full_LP','done':False,'native_result_available':False})
    sol = h.getSolution()
    if h.getModelStatus()!=highspy.HighsModelStatus.kOptimal or not sol.dual_valid:
        return None, None, None, {'lp_status':str(h.getModelStatus()),'seconds':time.monotonic()-begin}
    cert, rc = integer_dual(data,list(sol.row_dual))
    selected = [j for j,v in enumerate(sol.col_value) if v>.5]
    chosen = selected if base.exact_cover(data,selected) else None
    metrics = {'lp_status':str(h.getModelStatus()),'highspy':h.version(),'full_columns':m,'full_rows':n,'nnz':len(indices),
               'lp_objective':h.getObjectiveValue(),'certificate':cert,'seconds':time.monotonic()-begin,
               'rounded_candidate_feasible':chosen is not None,'minimum_reduced_cost':min(rc)}
    return chosen, cert, rc, metrics


def solve(data, deadline, seed=1):
    n,m,k,_ = base.dimensions(data)
    if k or n>256 or not all(type(c) is int and c>0 for c in data['cost_vector']):
        return ORIGINAL_SOLVE(data,deadline,seed)
    best, cert, reduced, lp_metrics = full_lp(data,deadline)
    if cert is None:
        return ORIGINAL_SOLVE(data,deadline,seed)
    if best is not None and base.cost(data,best)==cert['integer_objective_lower_bound']:
        return best, {'method':'full original LP + exact integer dual certificate', 'full_problem_status':'Optimal',
                      'lp':lp_metrics,'probes':{},'force_exit':False}
    costs,cols = data['cost_vector'],data['constraint_matrix_A']['columns']
    trace,probes = [],{}
    canonical,singleton = {},{}
    for j,rows in enumerate(cols):
        if not rows:
            continue
        key=tuple(rows)
        if key not in canonical or costs[j]<costs[canonical[key]]:
            canonical[key]=j
        if len(rows)==1 and (rows[0] not in singleton or costs[j]<costs[singleton[rows[0]]]):
            singleton[rows[0]]=j
    ordered = sorted(canonical.values(),key=lambda j:(costs[j]/len(cols[j]),-len(cols[j]),j))
    if len(singleton)==n:
        cold=[singleton[r] for r in range(n)]
        probes['cold']={'status':'SINGLETON_COVER','columns':len(ordered)}
    else:
        cold,probes['cold']=base.bitset_probe(data,ordered,min(deadline,time.monotonic()+2),seed)
    if cold is not None and (best is None or base.cost(data,cold)<base.cost(data,best)):
        best=cold
        trace.append([time.monotonic()-base.START,base.cost(data,best),'original_independent_cold'])
    if m>3*n and sum(map(len,cols))>2*m and ordered and time.monotonic()<deadline-1:
        pool,probes['pool']=base.density_pool(data,ordered)
        found,probes['density_probe']=base.bitset_probe(data,pool,min(deadline-1,time.monotonic()+6),104729*seed,
                                                       base.cost(data,best) if best is not None else math.inf)
        if found is not None:
            best=found
            trace.append([time.monotonic()-base.START,base.cost(data,best),'original_density_basin'])
        elif best is not None and time.monotonic()<deadline-1:
            best,probes['original_lns']=base.lns_cover(data,best,ordered,min(deadline-1,time.monotonic()+6),seed)
            trace.extend([t,c,'original_large_hole'] for t,c in probes['original_lns']['improvement_trace'])
        if best is not None and time.monotonic()<deadline-1:
            dual_order=sorted(canonical.values(),key=lambda j:(reduced[j]/len(cols[j]),-len(cols[j]),j))
            dual_begin=time.monotonic()-base.START
            best,probes['dual_lns']=dual_lns(data,best,dual_order,min(deadline-1,time.monotonic()+6),seed,
                                           cert['row_prices'],cert['scale'])
            trace.extend([dual_begin+t,c,'dual_bound_large_hole'] for t,c in probes['dual_lns']['improvement_trace'])
    force_exit=False
    try:
        candidate,metrics=base.highs_solve(data,deadline,best,seed,bounded=True)
    except base.HighsDeadline as error:
        if best is None:
            raise
        candidate,metrics,force_exit=None,error.args[0],True
    if candidate is not None and (best is None or base.cost(data,candidate)<base.cost(data,best)):
        best=candidate
        trace.append([time.monotonic()-base.START,base.cost(data,best),'warm_full_highs'])
    if best is None:
        raise ValueError('no full feasible cover within internal budget')
    return best,{'method':'full LP + original independent basin/LNS + exact dual-bound large-hole LNS + warm full highspy',
                 'lp':lp_metrics,'probes':probes,'improvement_trace':trace,'highs':metrics,'force_exit':force_exit}


if __name__=='__main__':
    base.solve=solve
    try:
        base.main()
    except Exception as error:
        import sys,os
        print(json.dumps({'failure':type(error).__name__+': '+str(error)}),file=sys.stderr,flush=True)
        if isinstance(error,base.HighsDeadline):
            os._exit(2)
        sys.exit(2)
