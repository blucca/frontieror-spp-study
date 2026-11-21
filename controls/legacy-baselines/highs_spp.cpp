// Sparse cold baseline. FrontierOR input attribution: authors, audited CC BY 4.0 derivative.
// Solver: existing pinned HiGHS MIT library, no incumbent/reference access.
#include "interfaces/highs_c_api.h"
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <vector>

static void ok(HighsInt result, const char* operation) {
  if (result == kHighsStatusError) throw std::runtime_error(operation);
}

int main(int argc, char** argv) {
  const auto start = std::chrono::steady_clock::now();
  auto elapsed = [&]() { return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count(); };
  try {
    if (argc < 4 || argc > 5) throw std::runtime_error("usage: solver INPUT.dat LIMIT_SECONDS SEED [LOG_FILE]");
    const double limit = std::stod(argv[2]);
    const HighsInt seed = std::stoi(argv[3]);
    std::ifstream in(argv[1]);
    HighsInt n, m, k;
    if (!(in >> n >> m >> k) || n <= 0 || m <= 0 || k < 0) throw std::runtime_error("invalid dimensions");
    std::vector<double> cost(m), lower(m, 0), upper(m, 1), rowlower(n + k, 1), rowupper(n + k, 1);
    std::vector<HighsInt> integer(m, kHighsVarTypeInteger);
    std::vector<std::vector<HighsInt>> indices(m);
    std::vector<std::vector<double>> values(m);
    for (HighsInt j = 0; j < m; ++j) {
      HighsInt count;
      if (!(in >> cost[j] >> count) || count < 0) throw std::runtime_error("invalid column");
      for (HighsInt t = 0; t < count; ++t) {
        HighsInt row;
        if (!(in >> row) || row < 0 || row >= n) throw std::runtime_error("invalid coverage row");
        indices[j].push_back(row); values[j].push_back(1);
      }
    }
    for (HighsInt b = 0; b < k; ++b) {
      std::string lo, hi;
      if (!(in >> lo >> hi)) throw std::runtime_error("missing Base bounds");
      rowlower[n + b] = std::stod(lo); rowupper[n + b] = std::stod(hi);
      for (HighsInt j = 0; j < m; ++j) {
        double v;
        if (!(in >> v)) throw std::runtime_error("missing Base coefficient");
        if (v != 0) { indices[j].push_back(n + b); values[j].push_back(v); }
      }
    }
    std::string extra;
    if (in >> extra) throw std::runtime_error("trailing transport data");
    std::vector<HighsInt> astart(m + 1, 0), aindex;
    std::vector<double> avalue;
    for (HighsInt j = 0; j < m; ++j) {
      aindex.insert(aindex.end(), indices[j].begin(), indices[j].end());
      avalue.insert(avalue.end(), values[j].begin(), values[j].end());
      astart[j + 1] = (HighsInt)aindex.size();
    }
    void* highs = Highs_create();
    ok(Highs_setIntOptionValue(highs, "threads", 2), "threads option");
    ok(Highs_setIntOptionValue(highs, "random_seed", seed), "seed option");
    ok(Highs_setBoolOptionValue(highs, "log_to_console", 0), "console option");
    if (argc == 5) ok(Highs_setStringOptionValue(highs, "log_file", argv[4]), "log file option");
    ok(Highs_passMip(highs, m, n + k, (HighsInt)aindex.size(), kHighsMatrixFormatColwise,
                     kHighsObjSenseMinimize, 0, cost.data(), lower.data(), upper.data(),
                     rowlower.data(), rowupper.data(), astart.data(), aindex.data(),
                     avalue.data(), integer.data()), "pass sparse MIP");
    const double build = elapsed();
    ok(Highs_setDoubleOptionValue(highs, "time_limit", std::max(0.001, limit - build)), "time limit option");
    const HighsInt runstatus = Highs_run(highs);
    HighsInt solutionstatus = 0;
    ok(Highs_getIntInfoValue(highs, "primal_solution_status", &solutionstatus), "primal status");
    std::vector<double> x(m, 0);
    double bound = 0, gap = 0;
    int64_t nodes = 0;
    Highs_getDoubleInfoValue(highs, "mip_dual_bound", &bound);
    Highs_getDoubleInfoValue(highs, "mip_gap", &gap);
    Highs_getInt64InfoValue(highs, "mip_node_count", &nodes);
    std::vector<HighsInt> selected;
    double objective = 0;
    if (solutionstatus == 2) {
      ok(Highs_getSolution(highs, x.data(), nullptr, nullptr, nullptr), "extract solution");
      for (HighsInt j = 0; j < m; ++j) if (x[j] > 0.5) { selected.push_back(j); objective += cost[j]; }
    }
    const HighsInt status = Highs_getModelStatus(highs);
    rusage ru{}; getrusage(RUSAGE_SELF, &ru);
    std::cout << std::setprecision(17) << "{\"status\":\"" << (solutionstatus == 2 ? (status == 7 ? "OPTIMAL" : "FEASIBLE") : "NO_SOLUTION")
              << "\",\"objective_value\":";
    if (solutionstatus == 2) std::cout << objective; else std::cout << "null";
    std::cout << ",\"selected_rotations\":[";
    for (size_t t = 0; t < selected.size(); ++t) { if (t) std::cout << ','; std::cout << selected[t]; }
    std::cout << "],\"metrics\":{\"solver\":\"HiGHS\",\"solver_version\":\"" << Highs_version()
              << "\",\"git_hash\":\"" << Highs_githash() << "\",\"threads\":2,\"seed\":" << seed
              << ",\"model_status\":" << status << ",\"run_status\":" << runstatus << ",\"best_bound\":";
    if (std::isfinite(bound)) std::cout << bound; else std::cout << "null";
    std::cout << ",\"mip_gap\":";
    if (std::isfinite(gap)) std::cout << gap; else std::cout << "null";
    std::cout << ",\"nodes\":" << nodes << ",\"build_seconds\":" << build
              << ",\"search_seconds\":" << Highs_getRunTime(highs) << ",\"internal_seconds\":" << elapsed()
              << ",\"max_rss_kib\":" << ru.ru_maxrss << "}}\n";
    Highs_destroy(highs);
    return runstatus == kHighsStatusError ? 2 : 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 2;
  }
}
