# World3 Dashboard — SW Scenario + Substack Plan

## Plan

### Task 1: Add SW (Stabilized World) scenario

- [x] Add `run_sw()` to `src/scenarios.py` — adapted 2004 params for 1974 pyworld3 using policy-year switches (zpgt, pet, fcest, iet=2002) instead of global dcfsn override
- [x] Add SW to `run_all_scenarios()`
- [x] Update `SCENARIO_COLORS` in `app.py` (blue `#3498db`)
- [x] Update `SCENARIO_DESCRIPTIONS` with SW explanation
- [x] Smoke-test: all 4 scenarios run. SW peaks at 6.03B (2019), stabilizes, resources preserved (716B/1000B)
- [x] Commit: f4ef1f4 "Add SW (Stabilized World) scenario"
- [x] Push

### Task 2: Substack content plan

- [x] Draft `docs/SUBSTACK_PLAN.md` — 12 posts, per-post specs, networking calendar, grad school tie-in
- [x] Commit: 0131282 "Add 6-month Substack content plan for polycrisis thread"
- [x] Push

### Memory + housekeeping

- [x] Update `project-world3-dashboard.md` with SW done, Substack plan drafted, revised Next Steps
- [x] Add Review section below

## Review (2026-04-16)

### SW Scenario
- Implemented `run_sw()` with 11 parameters adapted for the 1974 pyworld3
- Key adaptation: the todo spec listed `dcfsn=2` from the 2004 book, but in the 1974 model `dcfsn` is a global constant (not policy-year-gated), which crushed population from 1900. Used `pet=2002` + `fcest=2002` + `zpgt=2002` instead, which correctly triggers population stabilization at the policy year.
- Smoke test results: SW peaks at 6.03B (2019), stabilizes at ~6B, resources conserved (716B/1000B), pollution stays low. Qualitatively matches Meadows Scenario 9 behavior.

### Substack Plan
- 12 posts across 6 months (May-Oct 2026), 2/month cadence
- Narrative arc: launch dashboard -> bibliometric paper -> deep dives -> synthesis
- Networking milestones for Herrington (May), Lawrence (June), Tooze (June), Jehn (May/Aug), Randers (Aug)
- Grad school tie-in: portfolio demonstrates original tools, bibliometric competence, public communication, quantitative skills
