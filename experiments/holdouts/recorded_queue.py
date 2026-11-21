#!/usr/bin/env python3
"""Nine fixed held-out cold runs, using the unchanged round710 worker and sources."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = Path('/data/workspace/temp/round710/frontier-spp')
SOURCE = HERE / 'source'
CASES = {'large1': 187822, 'large4': 323670, 'large5': 516521}
PLANNED = [(name, alg) for name in CASES for alg in ('main', 'highs', 'cpsat')]
CPU_CAP, WALL_CAP = 1800, 1200
HASHES = {
    'main/solve.py': '262cc89ce7daf833bf168bf5db4dafc3d46ae88e182ef5feaf2fe558890dd58b',
    'eligible-baseline/controller.py': 'd00f6934358b7c4ab5170e0de85751322809491206e650297ce2c4278181fd45',
    'eligible-baseline/highs_baseline.py': 'ad23d8d4b247d42ad5e7370f38cc2812258ba1f1b3c8121d41c092c4f76e1852',
    'eligible-baseline/cpsat_baseline.py': 'b0b79ef9a0fd9cb95dd3efd3196ffbebd03ef2066af8dd8b98b81896b35b93fb',
    'shared/spp_io.py': '5bdaed279efa41601cbc49e0d70432675a857e2f4deecf6472c79b7da0891515',
    'source/hoffman1993-feasibility_check.py': '321bff76bf51fcf30ff66d2847ac376a568dda5861d2a8a4e63605c6063039dd',
}
spec = importlib.util.spec_from_file_location('controller', ROOT / 'eligible-baseline/controller.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def cpu():
    own, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def bounded():
    c.bounded()
    if sorted(os.sched_getaffinity(0)) != [0, 1]:
        raise ValueError('required CPU affinity 0,1 unavailable')


def gate():
    receipt = json.loads((SOURCE / 'source-receipts.json').read_text())
    if receipt['revision'] != 'ef42a2eac13595453f986d9df0b62e86e75ab596' or receipt['reference_downloads'] != 0:
        raise ValueError('pinned official input-only source receipt gate failed')
    records = {r['case']: r for r in receipt['records']}
    audit = {'official_source_receipt': str(SOURCE / 'source-receipts.json'),
             'attribution': 'FrontierOR authors, audited dataset derivative, CC BY 4.0',
             'reference_reads_as_algorithm_input': 0, 'sources': [], 'frozen_sources': []}
    for name, nnz in CASES.items():
        path = SOURCE / f'hoffman1993-large_instance_{name[5:]}.json'
        raw = path.read_bytes()
        data = json.loads(raw)
        record = records[name]
        columns = data['constraint_matrix_A']['columns']
        if (record['status'] != 200 or len(raw) != record['bytes'] or
            data['dimensions']['num_rows'] != 100 or data['dimensions']['num_cols'] != 15000 or
            data.get('has_base_constraints', False) or len(columns) != 15000 or
            len(data['cost_vector']) != 15000 or sum(map(len, columns)) != nnz or record['nnz'] != nnz):
            raise ValueError(f'complete official source gate failed: {name}')
        audit['sources'].append({'case': name, 'path': str(path), 'bytes': len(raw),
                                 'sha256': hashlib.sha256(raw).hexdigest(),
                                 'rows': 100, 'variables': 15000, 'base_constraints': 0, 'nnz': nnz,
                                 'official_url': record['url'], 'pinned_revision': receipt['revision']})
    for relative, expected in HASHES.items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'frozen source changed: {relative}')
        audit['frozen_sources'].append({'path': str(path), 'sha256': actual})
    package_gate = json.loads((ROOT / 'eligible-baseline/version-gate.json').read_text())
    if package_gate['status'] != 'PASS' or package_gate['observed']['versions'] != c.VERSIONS:
        raise ValueError('existing exact dependency gate failed')
    code = "import importlib.metadata as m,json,sys; print(json.dumps({'python':sys.version,'versions':{n:m.version(n) for n in ['highspy','ortools','numpy']}}))"
    current = json.loads(subprocess.check_output([str(ROOT / 'eligible-baseline/main-env/bin/python'), '-B', '-c', code],
                                                text=True, timeout=20, env=c.environment(ROOT), preexec_fn=bounded))
    if current['versions'] != c.VERSIONS:
        raise ValueError('current exact dependency versions failed')
    audit['environment'] = current
    audit['status'] = 'PASS'
    c.dump(HERE / 'source-audit.json', audit)


def main():
    if (HERE / 'state.json').exists():
        raise ValueError('fixed one-shot queue state already exists; inspect saved state, no reruns')
    started = time.monotonic()
    state = {'status': 'RUNNING', 'pid': os.getpid(), 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'planned_count': 9, 'planned': [{'instance_name': name, 'algorithm': alg, 'seed': 1} for name, alg in PLANNED],
             'runs': [], 'cpu_cap_seconds': CPU_CAP, 'whole_queue_cap_seconds': WALL_CAP,
             'whole_run_limit_seconds': 60, 'internal_limit_seconds': 55,
             'affinity': [0, 1], 'per_native_as_bytes': c.RAM,
             'main_source': str(ROOT / 'main/solve.py'), 'main_version': 'frozen v1, default seed1 unchanged'}
    c.dump(HERE / 'state.json', state)
    stopped_main, stop = None, None
    try:
        gate()
    except Exception as error:
        stop = 'source/dependency gate: ' + type(error).__name__ + ': ' + str(error)
        state.update(status='STOP', failure=stop)
    for name, algorithm in PLANNED:
        out = HERE / 'results' / name / algorithm
        out.mkdir(parents=True, exist_ok=True)
        if stop is None and (cpu() >= CPU_CAP or time.monotonic() - started >= WALL_CAP):
            stop = 'additional CPU or whole-queue budget reached'
            state.update(status='STOP', failure=stop)
        if stop is not None or (algorithm == 'main' and stopped_main is not None):
            rec = {'instance_name': name, 'algorithm': algorithm, 'seed': 1, 'status': 'SKIPPED',
                   'failure': stop or 'Main full native failed earlier: ' + stopped_main}
        else:
            path = SOURCE / f'hoffman1993-large_instance_{name[5:]}.json'
            command = [sys.executable, '-B', str(ROOT / 'eligible-baseline/controller.py'), 'run',
                       '--root', str(ROOT), '--algorithm', algorithm, '--instance', str(path), '--out', str(out)]
            state['current'] = {'instance_name': name, 'algorithm': algorithm, 'seed': 1, 'out': str(out)}
            c.dump(HERE / 'state.json', state)
            began, timed_out = time.monotonic(), False
            with (out / 'worker.stdout.log').open('w') as log, (out / 'worker.stderr.log').open('w') as err:
                p = subprocess.Popen(command, stdout=log, stderr=err, env=c.environment(ROOT),
                                     preexec_fn=bounded, start_new_session=True)
                try:
                    p.wait(timeout=min(60, max(0.001, WALL_CAP - (time.monotonic() - started))))
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
            wall = time.monotonic() - began
            rec = json.loads((out / 'run.json').read_text()) if (out / 'run.json').exists() else {}
            rec.update(instance_name=name, algorithm=algorithm, seed=1, external_end_to_end_seconds=wall,
                       worker_exit_code=p.returncode, whole_native_executed=True)
            if timed_out or wall >= 60 or rec.get('max_rss_kib', 0) > c.RAM // 1024 or rec.get('algorithm_exit_code', 0) in (-9, -11, -24):
                rec.update(status='STOP', failure='whole-run resource gate failed')
                stop = f'{name}/{algorithm}: ' + rec['failure']
                state.update(status='STOP', failure=stop)
            elif rec.get('status') != 'PASS' or p.returncode:
                rec['status'] = 'FAILED'
                stderr = (out / 'algorithm.stderr.log').read_text() if (out / 'algorithm.stderr.log').exists() else ''
                rec['algorithm_failure_stderr'] = stderr
                if 'has no whole feasible solution' in stderr:
                    rec['failure_class'] = 'no feasible solution within the fixed cold budget'
                else:
                    rec['failure_class'] = rec.get('failure', 'full entry/checker failure')
                if algorithm == 'main':
                    stopped_main = f'{name}: {rec["failure_class"]}'
                    state['main_stopped_after_failure'] = stopped_main
                elif 'has no whole feasible solution' not in stderr:
                    stop = f'{name}/{algorithm}: {rec["failure_class"]}'
                    state.update(status='STOP', failure=stop)
        state['runs'].append(rec)
        state.update(wall_seconds=time.monotonic() - started, cpu_seconds=cpu())
        c.dump(out / 'run.json', rec)
        with (HERE / 'journal.jsonl').open('a') as journal:
            journal.write(json.dumps(rec, allow_nan=False) + '\n')
        c.dump(HERE / 'state.json', state)
        print(json.dumps({'event': 'RUN_COMPLETE', 'algorithm': algorithm, 'instance': name,
                          'status': rec['status'], 'objective': rec.get('objective'),
                          'algorithm_wall': rec.get('algorithm_external_wall_seconds'),
                          'whole_wall': rec.get('external_end_to_end_seconds'), 'failure': rec.get('failure_class', rec.get('failure'))}), flush=True)
    if state['status'] == 'RUNNING':
        state['status'] = 'DONE_WITH_NEGATIVE_RESULTS' if any(r['status'] != 'PASS' for r in state['runs']) else 'DONE'
    state.pop('current', None)
    state.update(wall_seconds=time.monotonic() - started, cpu_seconds=cpu(),
                 actual_native_count=sum(bool(r.get('whole_native_executed')) for r in state['runs']),
                 heavy_slot_released=True, ended_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    c.dump(HERE / 'state.json', state)
    print(json.dumps({'event': 'QUEUE_COMPLETE', 'status': state['status'],
                      'actual_native_count': state['actual_native_count'], 'cpu_seconds': state['cpu_seconds'],
                      'wall_seconds': state['wall_seconds'], 'heavy_slot_released': True}), flush=True)
    return 2 if state['status'] == 'STOP' else 0


if __name__ == '__main__':
    sys.exit(main())
