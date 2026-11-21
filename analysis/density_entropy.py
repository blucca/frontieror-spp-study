"""Independent uniform hyperedges conditional on size: a heuristic, not actual cover count."""
import argparse
import collections
import json
import math
from pathlib import Path


def log_add(a, b):
    if a == -math.inf:
        return b
    if b == -math.inf:
        return a
    m = max(a, b)
    return m + math.log1p(math.exp(min(a, b) - m))


def log_expected_covers(n, groups):
    # E[covers] = n! [z^n] product_k (1 + z^k/(n)_k)^m_k.
    dp = [-math.inf] * (n + 1)
    dp[0] = 0.0
    for k, m in groups.items():
        assert 1 <= k <= n and m >= 0
        falling = math.lgamma(n + 1) - math.lgamma(n - k + 1)
        weights = [math.lgamma(m + 1) - math.lgamma(t + 1) - math.lgamma(m - t + 1) - t * falling for t in range(min(m, n // k) + 1)]
        new = [-math.inf] * (n + 1)
        for j, v in enumerate(dp):
            if v != -math.inf:
                for t, w in enumerate(weights):
                    if j + k * t <= n:
                        new[j + k * t] = log_add(new[j + k * t], v + w)
        dp = new
    return math.lgamma(n + 1) + dp[n]


# Two independently uniform singleton columns cover two vertices with probability 1/2.
assert abs(math.exp(log_expected_covers(2, {1: 2})) - 0.5) < 1e-12
# A sole size-n column always covers all n vertices.
assert abs(math.exp(log_expected_covers(2, {2: 1})) - 1) < 1e-12

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    x = json.loads(args.instance.read_text())
    n = x['dimensions']['num_rows']
    report = []
    for theta in (1.5, 1.6, 2, 2.25, 2.5, 3, 3.5, 4, 5, 6, 8, 10):
        groups = collections.Counter(len(s) for c, s in zip(x['cost_vector'], x['constraint_matrix_A']['columns']) if s and c / len(s) <= theta)
        loge = log_expected_covers(n, groups)
        report.append({'density_threshold': theta, 'columns': sum(groups.values()), 'sizes': dict(groups), 'uniform_random_expected_covers_log10': loge / math.log(10)})
    result = {'assumption': __doc__, 'checks': 'PASS', 'report': report}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    print('PASS')
