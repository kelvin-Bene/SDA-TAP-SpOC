# Issues Backlog

**Last Updated:** January 13, 2026
**Status:** Deferred for future resolution

This document tracks issues identified during the documentation consistency audit that are deferred for later resolution.

---

## HIGH Priority Issues

### Issue #1: Package Naming Inconsistency
**Status:** Deferred
**Identified:** January 13, 2026

| Location | Package Name | Version |
|----------|--------------|---------|
| `UCT-Benchmark-DMR/combined/pyproject.toml` | `uct_benchmark` (underscore) | 0.0.1 |
| `external-code/master/pyproject.toml` | `uctbenchmark` (no underscore) | 0.0.3 |
| `external-code/jovan-linuxTesting/pyproject.toml` | `uctbenchmark` (no underscore) | 0.0.4 |

**Impact:** Import statements will fail if packages are mixed.

**Fix Required:**
- [ ] Decide on standard name (`uct_benchmark` recommended per PEP 8)
- [ ] Update all pyproject.toml files
- [ ] Rename source directories accordingly
- [ ] Update all import statements

---

### Issue #2: Python Version Conflict
**Status:** Deferred
**Identified:** January 13, 2026

| Location | Stated Requirement |
|----------|-------------------|
| `UCT-Benchmark-DMR/combined/INSTALLATION.md` | Python 3.9-3.12 (3.12 recommended) |
| `UCT-Benchmark-DMR/combined/pyproject.toml` | `~=3.12.0` (3.12 ONLY) |

**Fix Required:**
- [ ] Update INSTALLATION.md to state Python 3.12 requirement correctly

---

### Issue #3: Linux setup.sh Syntax Errors
**Status:** Deferred
**Identified:** January 13, 2026
**Location:** `external-code/jovan-linuxTesting/setup.sh`

**Problem:** Missing spaces before `]` in bash conditionals

**Lines to fix:** 4, 5, 6, 9, 12, 15, 18

**Example fix:**
```bash
# BROKEN:
if [ -d "data"]; then

# FIXED:
if [ -d "data" ]; then
```

**Additional Fix Required:**
- [ ] Update README to remove "ACTION NEEDED: Bash script for Linux/Unix systems is still pending development"

---

### Issue #4: Linux Setup README Outdated
**Status:** Deferred
**Identified:** January 13, 2026
**Location:** `external-code/jovan-linuxTesting/README.md`

**Problem:** README says Linux setup is "pending development" but setup.sh exists.

**Fix Required:**
- [ ] Update README Linux Setup section to document available setup.sh

---

## MEDIUM Priority Issues

### Issue #5: Description Typo
**Status:** Deferred
**Identified:** January 13, 2026
**Locations:**
- `external-code/master/pyproject.toml`
- `external-code/jovan-linuxTesting/pyproject.toml`

**Problem:**
```
description = "f a packaged representation..."
```
Should be:
```
description = "A packaged representation..."
```

**Fix Required:**
- [ ] Fix typo in both files

---

### Issue #6: Author Attribution Inconsistency
**Status:** Deferred
**Identified:** January 13, 2026

| Location | Authors Field |
|----------|---------------|
| `UCT-Benchmark-DMR/combined/pyproject.toml` | "UCT Benchmark Team, SDA TAP Lab Cohort 7" |
| `external-code/jovan-linuxTesting/pyproject.toml` | "Jovan Bergh" |
| `external-code/master/pyproject.toml` | "Jovan Bergh" |

**Fix Required:**
- [ ] Decide on standard attribution approach
- [ ] Update all pyproject.toml files

---

### Issue #7: Dependency Differences
**Status:** Deferred
**Identified:** January 13, 2026

**`UCT-Benchmark-DMR/combined` has but others don't:**
- `solara>=1.51.1` (Web GUI)
- `pyarrow>=22.0.0` (Data format)

**`jovan-linuxTesting` has but `UCT-Benchmark-DMR/combined` doesn't:**
- `jdk4py>=21.0.8.0` (Java runtime)
- `fpdf>=1.7.2` (PDF generation)
- `scipy>=1.16.2` (Scientific computing)
- `polars>=1.35.2` (DataFrame library)
- `duckdb>=1.4.2` (Database)

**Fix Required:**
- [ ] Align dependencies across branches
- [ ] Document which GUI approach is standard (Solara vs CustomTkinter)

---

### Issue #8: Project Structure Differences
**Status:** Deferred
**Identified:** January 13, 2026

The module structure differs significantly between branches. See CONSISTENCY_AUDIT_REPORT.md for details.

**Fix Required:**
- [ ] Align on standard project structure
- [ ] Document the standard structure

---

## LOW Priority / Informational

### Issue #9: DOCX Files Not Version Control Friendly
**Status:** Informational
**Identified:** January 13, 2026

Many important documents are in .docx format which doesn't diff well in git.

**Recommendation:** Consider converting critical documentation to Markdown over time.

---

## Resolution Log

| Date | Issue # | Action Taken | By |
|------|---------|--------------|-----|
| - | - | - | - |

---

**Note:** When resolving issues, update this document and add entries to the Resolution Log.
