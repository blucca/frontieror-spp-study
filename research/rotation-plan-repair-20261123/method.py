#!/usr/bin/env python3
"""Complete conflict-driven minimum-old-loss repair, then stock fixed-D cost.

The owner-group search supplies the primary proof and its own complete hint.
CP-SAT supplies the cost stage; the same stock routine is used by controls.
"""
import time
START = time.monotonic()
import argparse
import json
import resource
from pathlib import Path
import repair
import controls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('instance','old-plan','event','output'):
        parser.add_argument('--'+arg, required=True)
    parser.add_argument('--time-limit', type=float, default=55)
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    data, old, event = repair.read_contract(args.instance,args.old_plan,args.event)
    primary = repair.solve_primary(data,old,event,START+args.time_limit)
    result = {'solver':'owner-group minimum-old-loss + stock CP-SAT fixed-D cost',
              'primary':primary, 'secondary':controls.stage(), 'solution':None,
              'declared_event':event,'removed_old_count':None,'actual_cost':None,
              'verified':False,'seed':args.seed,'threads':2,'lexicographic_complete':False}
    if primary['selected_rotations'] is not None:
        best = primary['selected_rotations']
        result.update(solution=repair.make_solution(data,best),removed_old_count=primary['objective'],
                      actual_cost=primary['witness']['recomputed_cost'],verified=True)
        if primary['status']=='OPTIMAL' and time.monotonic()<START+args.time_limit:
            args.solver='cpsat'; args.primary_fixed=primary['objective']
            # Both stages share the process start, including input and preparation.
            controls.START=START
            try:
                controls.run(args,data,sorted(old['selected_rotations']),event,result,best)
            except Exception as error:
                result['failure']=type(error).__name__+': '+str(error)
            result['cost_stage_primary_context']=result['primary']
            result['primary']=primary
    result['primary_native_optimal']=False
    result['primary_custom_search_optimal']=primary['status']=='OPTIMAL'
    result['lexicographic_complete']=result['primary_custom_search_optimal'] and result['secondary']['status']=='OPTIMAL'
    if result['solution'] is not None:
        result['witness']=repair.check(data,old,event,result['solution']['selected_rotations'])
        assert result['solution']==repair.make_solution(data,result['solution']['selected_rotations'])
    result['own_wall_seconds_before_output']=time.monotonic()-START
    result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    Path(args.output).write_text(json.dumps(result, separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({'primary':result['primary']['status'],'secondary':result['secondary']['status'],
                      'verified':result['verified'],'D':result['removed_old_count'],'cost':result['actual_cost']}),flush=True)
    return 0 if result['verified'] and 'failure' not in result else 2


if __name__=='__main__':
    raise SystemExit(main())
