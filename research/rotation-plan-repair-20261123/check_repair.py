#!/usr/bin/env python3
import time
from repair import solve_primary, make_solution, check
# k=1 must be exhausted before k=2 succeeds; selecting the new column exposes
# the second old group even though only the first was forbidden.
data={'dimensions':{'num_rows':2,'num_cols':3},'cost_vector':[5,5,1],
      'constraint_matrix_A':{'columns':[[0],[1],[0,1]]},'has_base_constraints':False}
old=make_solution(data,[0,1])
a=solve_primary(data,old,{'F':[0],'P':[]},time.monotonic()+1)
assert a['status']=='OPTIMAL' and a['objective']==2 and a['selected_rotations']==[2]
assert a['budgets']==[{'budget':1,'exhausted':True,'nodes':1}]
assert check(data,old,{'F':[0],'P':[]},[2])['removed_old']==[0,1]
b=solve_primary(data,old,{'F':[0],'P':[1]},time.monotonic()+1)
assert b['status']=='INFEASIBLE' and b['selected_rotations'] is None
print('complete region / per-budget cache / pins / D and cost PASS')
