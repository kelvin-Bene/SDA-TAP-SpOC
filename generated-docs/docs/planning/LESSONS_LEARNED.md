# UCT Benchmark — Lessons Learned

**Date:** April 9, 2026
**Team:** DataMine Spring 2026

Per Louis: "What did we learn over the course of this project that would have made it easier if we had known? What do we know now that we wish we knew four months ago?"

---

## 1. Understand the Domain Before Writing Code

The UCT (Uncorrelated Track) problem is a specialized orbital mechanics challenge. Early in the project, we spent time building infrastructure (web UI, database, API) without fully understanding what a UCT processor does or what the evaluation metrics mean physically.

**What we wish we knew:** The benchmark is fundamentally about answering "can your algorithm correctly associate observations to satellites and estimate their orbits?" Every design decision should trace back to that question. If a feature doesn't help answer it, it's scope creep.

**For the next team:** Read Louis's original transcript (`provided-materials/Lewis_Transcript-1-22.md`) and the LLNL CTF paper before touching the code. Understanding the 5-tier system (T1 = raw, T2 = downsampled, T3 = simulated gaps, T4 = synthetic objects, T5 = unlabeled) will save weeks of confusion.

---

## 2. Orekit is Non-Negotiable for Full Evaluation

We underestimated the Orekit (Java orbit propagator) dependency. Without it, the evaluation pipeline can only compute binary metrics (F1, precision, recall). State metrics (Mahalanobis distance, position/velocity RMS) and residual metrics all require orbit propagation.

**What we wish we knew:** Set up Orekit on day one. Verify it works in your target deployment environment (Docker, local, ARM64) before building anything that depends on it. The `orekit-jpype` bridge is finicky — it needs a specific JDK version and the Orekit data files.

**For the next team:** Check `uct_benchmark/simulation/propagator.py` for the Orekit initialization. If you can run `python -c "import orekit_jpype; orekit_jpype.initVM()"` without errors, you're good. If not, fix this first.

---

## 3. UDL API Quirks

The Unified Data Library (UDL) API is the source of all real observation data. We learned several things the hard way:

- **Rate limiting:** UDL will throttle or block if you query too aggressively. Our hybrid search strategy (FAST/WINDOWED/HYBRID) was designed to balance speed with rate limits.
- **Data sparsity:** Not all satellites have observations in all time windows. A query for 10 objects might return data for only 3. The pipeline handles this gracefully now, but early versions would crash.
- **Token management:** UDL tokens expire. The settings page stores tokens encrypted, but users still get confused when their token expires mid-generation.
- **Date ranges matter:** Querying too wide a date range returns too much data; too narrow returns nothing. We settled on a 90-day max limit.

**For the next team:** If you're working with the production site, you'll need a valid UDL API token. If you're working locally/demo, the synthetic data mode bypasses UDL entirely.

---

## 4. The Answer Key Problem

This was Louis's biggest concern (identified April 9, 2026): if your dataset contains satellite numbers in the observations, anyone can trivially reconstruct the correct answer without actually running a UCT processor.

**What we learned:** Security of the benchmark is as important as the benchmark itself. The download must NEVER contain identifying information (satellite numbers, NORAD IDs, international designators). The truth data must live only in the database, never in the user-facing download.

**Current solution:** Whitelisted download fields — only observation time, angular measurements, sensor position, and sensor ID. All other fields (especially `satNo`, `origObjectId`, `idOnOrbit`) are excluded at the SQL layer.

**For the next team:** If you add new fields to the download, think carefully about whether they could be used to identify which satellite an observation belongs to. When in doubt, exclude the field.

---

## 5. Test Against Real Data Early

For months, we developed and tested against synthetic/demo data. When we finally tested against real UDL data, several assumptions broke:

- Real observations have null fields that synthetic data never produced
- Sensor names and IDs don't always match between UDL systems
- Some observations have NaN/Inf values for RA/Dec (corrupted data)
- The sheer volume of real data (thousands of observations per satellite) stressed the download streaming pipeline

**For the next team:** Generate a real dataset from UDL as your first test. Don't rely solely on demo mode for development.

---

## 6. Documentation is an Asset, Not Overhead

We initially treated documentation as something to write at the end. This made onboarding new team members painful and led to duplicate/conflicting implementations across branches.

**What changed:** We built comprehensive docs in `/generated-docs/docs/` (50+ files) covering architecture, guides, planning, and reference materials. This dramatically improved team alignment.

**For the next team:** Keep the docs updated as you make changes. The single most valuable file is `VISION_ALIGNMENT_AUDIT.md` — it maps every stakeholder requirement to a specific implementation location. Update it when you close a gap.

---

## 7. Live Demos Expose Real Issues

David's live demo during the April 9 meeting revealed several things that unit tests missed:

- The UDL token validation flow was confusing (production vs. demo mode)
- Dataset download JSON was one giant unformatted string — hard to inspect
- The evaluation pipeline takes a long time (Monte Carlo propagation)
- Users didn't understand the difference between train/validation/test splits

**For the next team:** Do a full end-to-end walkthrough (generate → download → inspect → submit → evaluate → view results) at least once per sprint. Automated tests don't catch UX problems.

---

## 8. Scope Management is Critical

The DGX Spark request arrived two weeks before handover. The temptation was to pivot the entire architecture to support local deployment. Louis wisely advised: "Don't make a whole bunch of changes to what we did to make it work with this thing. Give them some time to figure out what they actually wanna do."

**Lesson:** New stakeholder requests will come in late. Evaluate them against the existing roadmap. If the request is a "side mission" that doesn't advance the core MVP, note it for the transition document and keep building toward the original goal.

---

## 9. Branch Management

We had multiple development branches (combined, jovan-linuxTesting, various feature branches) that diverged significantly in dependencies, package naming, and even Python version requirements. This caused confusion about which branch was "the real one."

**For the next team:** The `combined` branch in `UCT-Benchmark-DMR/combined/` is the canonical codebase. All other branches should be considered reference material only. Avoid creating long-lived feature branches.

---

## 10. Key Technical Gotchas

| Gotcha | Details |
|--------|---------|
| DuckDB vs PostgreSQL | Local dev uses DuckDB; production uses PostgreSQL. SQL syntax is 99% compatible but not 100% — test queries against both. |
| Decimal serialization | Python `Decimal` types from PostgreSQL aren't JSON-serializable. The `_make_serializable()` helper handles this, but forget to use it and you get 500 errors. |
| ARM64 compilation | Some Python packages (especially scientific ones) don't have ARM64 wheels. Build from source or use Conda for ARM64 targets. |
| Supabase RLS | Row-Level Security policies in Supabase can silently filter out data if not configured correctly. Check RLS policies when debugging "missing data" issues. |
| Streaming responses | Large dataset downloads use `StreamingResponse` to avoid OOM. Don't try to load the full result set into memory. |
