// AI-workflow implementation; no reference solutions are read.
// Standard C++17. Native set partitioning: nonnegative costs, nonempty columns,
// no base side constraints, at most 128 rows.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
struct Mask {
    uint64_t lo = 0, hi = 0;
    void set(int r) { (r < 64 ? lo : hi) |= uint64_t(1) << (r & 63); }
    bool subset(const Mask& b) const { return !(lo & ~b.lo) && !(hi & ~b.hi); }
    bool intersects(const Mask& b) const { return (lo & b.lo) || (hi & b.hi); }
    Mask operator|(const Mask& b) const { return {lo | b.lo, hi | b.hi}; }
    Mask without(const Mask& b) const { return {lo & ~b.lo, hi & ~b.hi}; }
    int count() const { return __builtin_popcountll(lo) + __builtin_popcountll(hi); }
    bool operator==(const Mask& b) const { return lo == b.lo && hi == b.hi; }
};
struct Col { double cost; Mask mask; std::vector<int> rows; int original; };
struct Stats {
    uint64_t nodes = 0, cold_nodes = 0, bound_prunes = 0;
    uint64_t restarts = 0, neighborhoods = 0, improvements = 0, completed_holes = 0;
    uint64_t anchor_holes = 0, anchor_improvements = 0;
    double initial_cost = -1, cold_seconds = 0;
    bool exact_optimum = false;
};
struct Node { int l, r, u, d, c, edge; };

// Algorithm X / dancing links: every remaining header is an uncovered input row.
// Every active option is fully compatible with the rows fixed outside this search.
// Vertical lists are in true cost/coverage order, maintained by cover/uncover.
class ExactCover {
    const std::vector<Col>& cols;
    Stats& stats;
    std::vector<Node> a;
    std::array<int, 129> size{};
    std::vector<double> order;
    std::vector<int> path;
    Clock::time_point deadline;
    uint64_t node_limit, visits = 0;
    bool stop_first, aborted = false, found = false;
    double bound;
    std::vector<int> best;
    uint64_t tie_seed;

    void cover(int c) {
        a[a[c].r].l = a[c].l; a[a[c].l].r = a[c].r;
        for (int i = a[c].d; i != c; i = a[i].d)
            for (int j = a[i].r; j != i; j = a[j].r) {
                a[a[j].d].u = a[j].u; a[a[j].u].d = a[j].d;
                --size[a[j].c];
            }
    }
    void uncover(int c) {
        for (int i = a[c].u; i != c; i = a[i].u)
            for (int j = a[i].l; j != i; j = a[j].l) {
                ++size[a[j].c];
                a[a[j].d].u = j; a[a[j].u].d = j;
            }
        a[a[c].r].l = c; a[a[c].l].r = c;
    }
    uint64_t tie(int c) const {
        uint64_t x = uint64_t(c) + tie_seed;
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
        x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
        return x ^ (x >> 31);
    }
    bool dfs(double cost) {
        ++visits; ++stats.nodes;
        if (visits > node_limit || ((visits & 127) == 1 && Clock::now() >= deadline)) {
            aborted = true; return true;
        }
        if (a[0].r == 0) {
            if (cost < bound - 1e-9) {
                bound = cost; best = path; found = true;
                return stop_first;
            }
            return false;
        }
        int c = a[0].r;
        double lb = 0;
        for (int h = a[0].r; h; h = a[h].r) {
            if (!size[h]) return false;
            if (size[h] < size[c] || (size[h] == size[c] && tie(h) < tie(c))) c = h;
            // For each uncovered row r, min_e cost(e)/|e| is a row price.
            // Any exact cover pays >= sum of these prices, since all its edges
            // occur in the current active lists and cover only remaining rows.
            int e = a[a[h].d].edge;
            lb += cols[e].cost / cols[e].rows.size();
        }
        if (!stop_first && cost + lb >= bound - 1e-9) {
            ++stats.bound_prunes; return false;
        }
        std::vector<int> options;
        options.reserve(size[c]);
        for (int i = a[c].d; i != c; i = a[i].d)
            if (cost + cols[a[i].edge].cost < bound - 1e-9) options.push_back(i);
        std::sort(options.begin(), options.end(), [&](int x, int y) {
            int ex = a[x].edge, ey = a[y].edge;
            return order[ex] < order[ey] || (order[ex] == order[ey] && ex < ey);
        });
        cover(c);
        for (int i : options) {
            int e = a[i].edge;
            if (cost + cols[e].cost >= bound - 1e-9) continue;
            path.push_back(e);
            for (int j = a[i].r; j != i; j = a[j].r) cover(a[j].c);
            bool stop = dfs(cost + cols[e].cost);
            for (int j = a[i].l; j != i; j = a[j].l) uncover(a[j].c);
            path.pop_back();
            if (stop) { uncover(c); return true; }
        }
        uncover(c); return false;
    }
public:
    ExactCover(const std::vector<Col>& columns, const std::vector<int>& ids,
               Mask hole, int n, Stats& s, std::mt19937_64& rng,
               Clock::time_point until, uint64_t limit, double cap, bool first)
        : cols(columns), stats(s), order(columns.size(), 0), deadline(until),
          node_limit(limit), stop_first(first), bound(cap), tie_seed(rng()) {
        size_t nnz = n + 1;
        for (int e : ids) nnz += cols[e].rows.size();
        a.reserve(nnz); a.resize(n + 1);
        a[0] = {0, 0, 0, 0, 0, -1};
        for (int r = 0; r < n; ++r) {
            int h = r + 1; a[h] = {h, h, h, h, h, -1};
            Mask one; one.set(r);
            if (one.subset(hole)) {
                a[h].l = a[0].l; a[h].r = 0;
                a[a[0].l].r = h; a[0].l = h;
            }
        }
        std::uniform_real_distribution<double> unit(0, 1);
        for (int e : ids) {
            // One perturbation per search, so node order is deterministic for a seed.
            order[e] = (cols[e].cost + 0.5) / cols[e].rows.size() * (0.8 + 0.4 * unit(rng));
            int firstnode = -1, last = -1;
            for (int r : cols[e].rows) {
                int h = r + 1, j = int(a.size());
                a.push_back({j, j, a[h].u, h, h, e});
                a[a[h].u].d = j; a[h].u = j; ++size[h];
                if (firstnode < 0) firstnode = j;
                else { a[j].l = last; a[last].r = j; }
                last = j;
            }
            a[firstnode].l = last; a[last].r = firstnode;
        }
    }
    void run() { dfs(0); }
    bool has_solution() const { return found; }
    bool complete() const { return !aborted; }
    uint64_t nodes() const { return visits; }
    double value() const { return bound; }
    const std::vector<int>& solution() const { return best; }
};

static bool valid(const std::vector<int>& sol, const std::vector<Col>& cols,
                  Mask full, double& cost) {
    Mask seen; cost = 0;
    for (int e : sol) {
        if (e < 0 || e >= int(cols.size()) || seen.intersects(cols[e].mask)) return false;
        seen = seen | cols[e].mask; cost += cols[e].cost;
    }
    return seen == full;
}
static double elapsed(Clock::time_point start) {
    return std::chrono::duration<double>(Clock::now() - start).count();
}
int main(int argc, char** argv) {
    const auto started = Clock::now(); // Parsing is part of the requested limit.
    double seconds = argc > 2 ? std::strtod(argv[2], nullptr) : 55;
    if (!std::isfinite(seconds) || seconds < 0) seconds = 0;
    seconds = std::min(seconds, 86400.0);
    uint64_t seed = argc > 3 ? std::strtoull(argv[3], nullptr, 10) : 1;
    auto hard_end = started + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
    auto work_end = hard_end - std::chrono::milliseconds(4);
    int n = 0, m = 0, k = 0;
    std::string reason;
    Stats stats;
    std::vector<Col> cols;
    std::vector<int> incumbent;
    double incumbent_cost = 0;
    bool have_incumbent = false;
    std::ifstream input(argc > 1 ? argv[1] : "");
    if (!(input >> n >> m >> k) || n < 1 || m < 1 || k < 0) reason = "invalid_header";
    else if (n > 128) reason = "unsupported_rows_gt_128";
    else if (k) reason = "unsupported_base_constraints";
    if (reason.empty()) {
        cols.reserve(m);
        for (int e = 0; e < m; ++e) {
            double c; int count;
            if (!(input >> c >> count) || !std::isfinite(c) || c < 0 || count < 1 || count > n) {
                reason = "requires_nonnegative_cost_nonempty_columns"; break;
            }
            Col col{c, {}, {}, e}; col.rows.reserve(count);
            for (int j = 0; j < count; ++j) {
                int r = -1; input >> r;
                Mask one; if (r >= 0 && r < n) one.set(r);
                if (!input || r < 0 || r >= n || col.mask.intersects(one)) {
                    reason = "invalid_or_repeated_row"; break;
                }
                col.mask.set(r); col.rows.push_back(r);
            }
            if (!reason.empty()) break;
            cols.push_back(std::move(col));
        }
    }
    if (reason.empty()) {
        // Same-covered-row rotations are interchangeable under K=0. Preserve
        // only their cheapest original index, then sort by true cost/coverage.
        std::sort(cols.begin(), cols.end(), [](const Col& x, const Col& y) {
            if (x.mask.hi != y.mask.hi) return x.mask.hi < y.mask.hi;
            if (x.mask.lo != y.mask.lo) return x.mask.lo < y.mask.lo;
            return x.cost < y.cost || (x.cost == y.cost && x.original < y.original);
        });
        cols.erase(std::unique(cols.begin(), cols.end(), [](const Col& x, const Col& y) {
            return x.mask == y.mask;
        }), cols.end());
        std::sort(cols.begin(), cols.end(), [](const Col& x, const Col& y) {
            double a = x.cost / x.rows.size(), b = y.cost / y.rows.size();
            return a < b || (a == b && (x.cost < y.cost || (x.cost == y.cost && x.original < y.original)));
        });
        std::vector<int> ids(cols.size()); std::iota(ids.begin(), ids.end(), 0);
        Mask full; for (int r = 0; r < n; ++r) full.set(r);
        std::mt19937_64 rng(seed);
        while (!have_incumbent && Clock::now() < work_end) {
            ++stats.restarts;
            auto until = std::min(work_end, Clock::now() + std::chrono::milliseconds(450));
            ExactCover search(cols, ids, full, n, stats, rng, until, 120000,
                              std::numeric_limits<double>::infinity(), true);
            search.run(); stats.cold_nodes += search.nodes();
            if (search.has_solution()) {
                incumbent = search.solution();
                have_incumbent = valid(incumbent, cols, full, incumbent_cost);
                if (!have_incumbent) { reason = "internal_cover_validation_failed"; break; }
                stats.initial_cost = incumbent_cost; stats.cold_seconds = elapsed(started);
            } else if (search.complete()) { reason = "exact_cover_infeasible"; break; }
        }
        const int targets[] = {30, 40, 50, 60};
        while (have_incumbent && incumbent_cost > 1e-9 && Clock::now() < work_end) {
            int target = std::min(n, targets[stats.neighborhoods % 4]);
            ++stats.neighborhoods;
            std::vector<int> perm = incumbent;
            std::shuffle(perm.begin(), perm.end(), rng);
            // Target costly incumbent edges without making every hole identical.
            if (perm.size() > 1) {
                size_t pivot = 0;
                for (size_t j = 1; j < std::min<size_t>(3, perm.size()); ++j)
                    if (cols[perm[j]].cost > cols[perm[pivot]].cost) pivot = j;
                std::swap(perm[0], perm[pivot]);
            }
            Mask hole; std::vector<int> fixed; double removed_cost = 0;
            int anchor = -1;
            // Every second hole ejects the incumbent edges touched by a cheap
            // unselected edge. Forcing this anchor opens a coherent replacement
            // that a uniformly random hole seldom contains.
            if (n > 60 && (stats.neighborhoods & 1) == 0) {
                size_t pool = 0;
                while (pool < cols.size() && cols[pool].cost / cols[pool].rows.size() < incumbent_cost / n) ++pool;
                if (pool) {
                    int proposed = int(rng() % pool);
                    if (std::find(incumbent.begin(), incumbent.end(), proposed) == incumbent.end()) {
                        for (int e : incumbent)
                            if (cols[e].mask.intersects(cols[proposed].mask)) hole = hole | cols[e].mask;
                        if (hole.count() <= 60) anchor = proposed;
                        else hole = {};
                    }
                }
            }
            if (anchor >= 0) { ++stats.anchor_holes; target = std::max(target, 50); }
            for (int e : perm) {
                bool conflicts = anchor >= 0 && cols[e].mask.intersects(cols[anchor].mask);
                if (conflicts || n <= 60 || (hole.count() < target && hole.count() + int(cols[e].rows.size()) <= 60)) {
                    hole = hole | cols[e].mask; removed_cost += cols[e].cost;
                } else fixed.push_back(e);
            }
            if (!hole.count() || removed_cost <= 1e-9) continue;
            Mask repair_rows = anchor >= 0 ? hole.without(cols[anchor].mask) : hole;
            double repair_cap = removed_cost - (anchor >= 0 ? cols[anchor].cost : 0);
            if (repair_cap <= 1e-9) continue;
            if (anchor >= 0) fixed.push_back(anchor);
            std::vector<int> eligible;
            for (int e : ids)
                if (cols[e].cost < repair_cap - 1e-9 && cols[e].mask.subset(repair_rows)) eligible.push_back(e);
            auto until = std::min(work_end, Clock::now() + std::chrono::milliseconds(60));
            ExactCover repair(cols, eligible, repair_rows, n, stats, rng, until, 30000, repair_cap, false);
            repair.run();
            if (repair.complete()) ++stats.completed_holes;
            if (repair.has_solution()) {
                std::vector<int> candidate = fixed;
                candidate.insert(candidate.end(), repair.solution().begin(), repair.solution().end());
                double candidate_cost = 0;
                if (!valid(candidate, cols, full, candidate_cost)) { reason = "internal_cover_validation_failed"; break; }
                if (candidate_cost < incumbent_cost - 1e-9) {
                    incumbent.swap(candidate); incumbent_cost = candidate_cost; ++stats.improvements;
                    if (anchor >= 0) ++stats.anchor_improvements;
                }
            }
            if (anchor < 0 && hole == full && repair.complete()) { stats.exact_optimum = true; break; }
        }
        if (have_incumbent && incumbent_cost <= 1e-9) stats.exact_optimum = true;
    }
    std::vector<int> original;
    for (int e : incumbent) original.push_back(cols[e].original);
    std::sort(original.begin(), original.end());
    std::cout << std::setprecision(17)
              << "{\"status\":\"" << (have_incumbent ? "feasible" : "no_feasible") << "\",\"objective_value\":";
    if (have_incumbent) std::cout << incumbent_cost; else std::cout << "null";
    std::cout << ",\"selected_rotations\":[";
    for (size_t i = 0; i < original.size(); ++i) { if (i) std::cout << ','; std::cout << original[i]; }
    std::cout << "],\"metrics\":{\"method\":\"native_dlx_hole_lns\",\"rows\":" << n
              << ",\"input_columns\":" << m << ",\"distinct_columns\":" << cols.size()
              << ",\"seed\":" << seed << ",\"nodes\":" << stats.nodes
              << ",\"cold_nodes\":" << stats.cold_nodes << ",\"cold_restarts\":" << stats.restarts
              << ",\"cold_seconds\":" << stats.cold_seconds << ",\"initial_objective\":";
    if (stats.initial_cost < 0) std::cout << "null"; else std::cout << stats.initial_cost;
    std::cout << ",\"neighborhoods\":" << stats.neighborhoods << ",\"improvements\":" << stats.improvements
              << ",\"anchor_holes\":" << stats.anchor_holes << ",\"anchor_improvements\":" << stats.anchor_improvements
              << ",\"completed_holes\":" << stats.completed_holes << ",\"row_bound_prunes\":" << stats.bound_prunes
              << ",\"exact_optimum\":" << (stats.exact_optimum ? "true" : "false")
              << ",\"elapsed_seconds\":" << elapsed(started)
              << ",\"time_limit_seconds\":" << seconds << ",\"scope\":\"N<=128,K=0,nonnegative_cost,nonempty_columns\"";
    if (!reason.empty()) std::cout << ",\"termination\":\"" << reason << "\"";
    else std::cout << ",\"termination\":\"" << (stats.exact_optimum ? "proved_optimum" : "deadline") << "\"";
    std::cout << "}}\n";
    return 0;
}
