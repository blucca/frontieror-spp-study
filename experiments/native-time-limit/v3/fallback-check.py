import importlib.util,sys
from pathlib import Path
p=Path(__file__).parent/"main/solve.py"
s=importlib.util.spec_from_file_location("m",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def late(*a,**kw): raise m.HighsDeadline({"run_status":"MAIN_DEADLINE_FALLBACK","native_result_available":False})
m.highs_solve=late
m.main()
