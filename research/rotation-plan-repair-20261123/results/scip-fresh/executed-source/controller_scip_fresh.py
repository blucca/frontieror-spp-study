#!/usr/bin/env python3
import json
from pathlib import Path
import sys
import os
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import controller as c
c.ROOT=ROOT
c.STATE=ROOT/'state.json'
state={'phase':'RUNNING','pid':os.getpid(),'cases':[],'started_at_epoch':time.time()}
c.dump(c.STATE,state)
for event in ('E1','E2','E3'):
    state['active']={'event':event,'solver':'scip'}; c.dump(c.STATE,state)
    try:
        record=c.one('scip',event)
    except (ValueError,AssertionError,KeyError,json.JSONDecodeError) as error:
        record={'event':event,'solver':'scip','resource_pass':False,'failure':type(error).__name__+': '+str(error)}
    state['cases'].append(record); c.dump(c.STATE,state)
    print(json.dumps(record,allow_nan=False),flush=True)
    if record.get('failure') or not record['resource_pass']:
        state.update(phase='STOPPED_EXECUTION_FAILURE',active=None); c.dump(c.STATE,state); raise SystemExit(2)
state.update(phase='COMPLETE_SCIP_FRESH_FIXED_CASES',active=None,finished_at_epoch=time.time()); c.dump(c.STATE,state)
