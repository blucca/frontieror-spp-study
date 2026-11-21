# HiGHS time-limit triage — known issue, new report STOP

## Decision

**Merge this observation into existing known issue coverage; stop the new issue
and new reproducer draft.** The exact HiGHS repository search finds an open,
maintainer-reproduced report on the same 1.15.1 release and a later open report
with the missing native time-check locations and proposed fixes.

### Direct coverage

- [#3314](https://github.com/ERGO-Code/HiGHS/issues/3314), open:
  `highspy 1.15.1 / 04024d7`, `time_limit=60` takes 258–406s; presolve completes
  and the solve reports zero nodes/LP iterations. Maintainer odow confirms the
  release reproduction in
  [comment 5922951886](https://github.com/ERGO-Code/HiGHS/issues/3314#issuecomment-5922951886):
  “The trick is getting presolve's time limit to exit in just the right spot.”
  Their reproduction uses a 160s limit. This matches the observed dependence on
  shifting the native time allocation after adding LNS.
- [#3606](https://github.com/ERGO-Code/HiGHS/issues/3606), open, reports missing
  time checks in analytic-centre IPM, clique merging, dominated columns, clique
  partition, inequality strengthening and mod-k separation. It explicitly maps
  #3314 to `setupCliquePartition` / `cliquePartition` before the first node.
  It supplies six proposed fixes and measured current-versus-fixed runtimes.
  Maintainer fwesselm's
  [comment 6777956203](https://github.com/ERGO-Code/HiGHS/issues/3606#issuecomment-6777956203)
  acknowledges the report and plans dominated-column/inequality work after 1.16.
- [#3601](https://github.com/ERGO-Code/HiGHS/issues/3601), open, additionally
  covers central rounding and root separation missing their time checks, with
  examples 10s→52s and 12s→25s. Its body is available in the one search response;
  this triage starts no additional investigation of it.

Our large4 is a different model, with root's phase evidence locating the stall
inside full `h.run()` after timely LNS completion. Function-level attribution
for this particular model requires an over-limit native stack sample. The
reported release behavior and affected phase are already explicitly covered.

## Current release / fix status

- GitHub latest release is
  [v1.16.0](https://github.com/ERGO-Code/HiGHS/releases/tag/v1.16.0), published
  2026-11-11 14:57:20 UTC. Its time-limit changes cover IPX initial basis
  construction (PR3185) and symmetry detection (PR3535).
- #3314 and #3606 remain open. #3606's retrieved timeline contains an open
  related dominated-column issue and no linked merged fix for these six checks.
- One exact current `latest` source read confirms the Fix5 gap: the objective
  overload of `HighsCliqueTable::cliquePartition` retains its old signature and
  its function body contains zero `checkLimits` / `checkTimeLimit` calls.
  Source receipt and SHA are in `latest-clique-check.json`.

Thus this is **known open behavior**, with proposed fixes; the current release
does not provide the first-node clique-partition check identified by #3606.
The Main-matched highspy1.15.1 remains the target dependency. Root's scoped
`presolve="off"` fallback is a measured application workaround, with its
whole-native acceptance owned by root.

## Our separate observation

Root's original large4 diagnostic reports timely LNS ending at 7.867s, native
entry at 8.068s with limit3.78175s, and no native return before the 20s whole
kill. With `presolve="off"`, root measures native 8.136→13.825s for limit3.714s,
an overrun of about1.98s, and the whole20s check passes. These measurements are
our runtime-control evidence; they are not used to claim a new core defect or
a fixed release.

## Search receipts and scope

Exactly one GitHub issue search:
`repo:ERGO-Code/HiGHS is:issue "time limit" in:title,body`; 87 results, one
100-result page, `incomplete_results=false`. Follow-up GETs are only #3314
comments, #3606 comments/timeline, latest release and one exact current source
file. The original #3761 conversation is excluded; no comment endpoint for it
is accessed. All evidence stays here.

Native runs0, installs0, external sends0, new core PR0, new issue0, reproducer
draft0. Product, memory and note files retain their current contents.
