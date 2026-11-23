"""Reuse the unchanged original cold solver's stdlib input/witness functions."""
import importlib.util
from pathlib import Path
path=Path(__file__).resolve().parents[2]/'main/solve.py'
spec=importlib.util.spec_from_file_location('_frozen_spp_io',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
read_instance=module.read_instance
dimensions=module.dimensions
cost=module.cost
exact_cover=module.exact_cover
